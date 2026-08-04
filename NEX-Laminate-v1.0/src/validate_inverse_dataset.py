#!/usr/bin/env python3
"""Validate NEX-Laminate v1.0 and write a machine-readable QA report."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


ANGLES = (0, 45, -45, 90)
EXPECTED_ROWS = 10_000


def token(seq: tuple[int, ...]) -> str:
    return ";".join(str(x) for x in seq)


def seq_hash(seq: tuple[int, ...]) -> str:
    return hashlib.sha256(token(seq).encode()).hexdigest()


def eq_hash(seq: tuple[int, ...]) -> str:
    mirror = tuple(-x if abs(x) == 45 else x for x in seq)
    return hashlib.sha256(min(token(seq), token(mirror)).encode()).hexdigest()


def max_contiguity(seq: tuple[int, ...]) -> int:
    return max(len(list(group)) for _, group in itertools.groupby(seq))


def angular_difference(a: int, b: int) -> int:
    delta = abs(a - b) % 180
    return min(delta, 180 - delta)


def expected_split(n_plies: int, group_hash: str) -> str:
    if n_plies == 24:
        return "test_ood_thickness"
    bucket = int(group_hash[:8], 16) % 100
    if bucket < 70:
        return "train"
    if bucket < 85:
        return "validation"
    return "test"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    args = parser.parse_args()
    root = args.dataset.resolve()
    data_path = root / "data" / "numerical_clt_v1.csv.gz"

    errors: list[str] = []
    warnings: list[str] = []
    record_ids: set[str] = set()
    layup_hashes: set[str] = set()
    group_splits: dict[str, set[str]] = defaultdict(set)
    split_counts: Counter[str] = Counter()
    ply_counts: Counter[int] = Counter()
    numerical_ranges = {
        "Ex_GPa": [float("inf"), -float("inf")],
        "Ey_GPa": [float("inf"), -float("inf")],
        "Gxy_GPa": [float("inf"), -float("inf")],
        "areal_mass_kg_m2": [float("inf"), -float("inf")],
    }
    row_count = 0

    with gzip.open(data_path, "rt", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row_count, row in enumerate(reader, 1):
            rid = row["record_id"]
            if rid in record_ids:
                errors.append(f"duplicate record_id: {rid}")
            record_ids.add(rid)
            seq = tuple(int(x) for x in row["layup_deg"].split(";"))
            n = int(row["n_plies"])
            counts = Counter(seq)
            actual_hash = seq_hash(seq)
            actual_group = eq_hash(seq)
            if len(seq) != n:
                errors.append(f"{rid}: n_plies mismatch")
            if seq != seq[::-1]:
                errors.append(f"{rid}: not symmetric")
            if counts[45] != counts[-45]:
                errors.append(f"{rid}: not balanced")
            if abs(seq[0]) != 45:
                errors.append(f"{rid}: outer ply is not +/-45")
            if max_contiguity(seq) > 3:
                errors.append(f"{rid}: contiguity exceeds 3")
            if min(counts[a] / n for a in ANGLES) < 0.10:
                errors.append(f"{rid}: orientation fraction below 10%")
            if actual_hash != row["canonical_layup_hash"]:
                errors.append(f"{rid}: canonical hash mismatch")
            if actual_group != row["equivalence_group_hash"]:
                errors.append(f"{rid}: equivalence hash mismatch")
            if actual_hash in layup_hashes:
                errors.append(f"{rid}: duplicate layup")
            layup_hashes.add(actual_hash)
            if expected_split(n, actual_group) != row["split"]:
                errors.append(f"{rid}: split mismatch")
            group_splits[actual_group].add(row["split"])
            if int(row["max_contiguity"]) != max_contiguity(seq):
                errors.append(f"{rid}: max_contiguity field mismatch")
            expected_d = max(
                angular_difference(x, y) for x, y in zip(seq, seq[1:])
            )
            if int(float(row["max_disorientation_deg"])) != expected_d:
                errors.append(f"{rid}: max_disorientation field mismatch")
            if row["rule_valid"].lower() != "true":
                errors.append(f"{rid}: rule_valid is false")
            for field, (minimum, maximum) in numerical_ranges.items():
                value = float(row[field])
                if not math.isfinite(value) or value <= 0:
                    errors.append(f"{rid}: invalid {field}")
                numerical_ranges[field][0] = min(minimum, value)
                numerical_ranges[field][1] = max(maximum, value)
            split_counts[row["split"]] += 1
            ply_counts[n] += 1
            if len(errors) > 100:
                break

    leaking_groups = [key for key, splits in group_splits.items() if len(splits) > 1]
    if leaking_groups:
        errors.append(f"{len(leaking_groups)} equivalence groups cross partitions")
    if row_count != EXPECTED_ROWS:
        errors.append(f"expected {EXPECTED_ROWS} rows, found {row_count}")
    if ply_counts.get(24, 0) != split_counts.get("test_ood_thickness", 0):
        errors.append("24-ply OOD partition is incomplete")

    exp_path = root / "data" / "experimental_ncamp_lamina_summary.csv"
    with exp_path.open(newline="", encoding="utf-8") as handle:
        experimental_rows = list(csv.DictReader(handle))
    if not experimental_rows:
        errors.append("experimental summary is empty")
    if any(row["data_role"] != "experimental_summary_statistic" for row in experimental_rows):
        errors.append("experimental rows lack explicit data role")

    protocol_path = root / "protocols" / "minimum_experimental_plan.csv"
    with protocol_path.open(newline="", encoding="utf-8") as handle:
        planned_rows = list(csv.DictReader(handle))
    if any(row["status"] != "planned_not_observed" for row in planned_rows):
        errors.append("planned experiment was misrepresented as observed")

    report = {
        "dataset": "NEX-Laminate",
        "version": "1.0.0",
        "status": "PASS" if not errors else "FAIL",
        "rows_checked": row_count,
        "unique_layups": len(layup_hashes),
        "unique_equivalence_groups": len(group_splits),
        "experimental_summary_rows": len(experimental_rows),
        "planned_experimental_designs": len(planned_rows),
        "counts_by_split": dict(sorted(split_counts.items())),
        "counts_by_ply": dict(sorted(ply_counts.items())),
        "numeric_ranges": {
            key: {"min": values[0], "max": values[1]}
            for key, values in numerical_ranges.items()
        },
        "errors": errors,
        "warnings": warnings,
    }
    report_path = root / "reports" / "qa_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
