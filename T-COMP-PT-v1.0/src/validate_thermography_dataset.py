#!/usr/bin/env python3
"""Validate the paired T-COMP-PT v1.0 benchmark and external registry."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    args = parser.parse_args()
    root = args.dataset.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    manifest_path = root / "metadata" / "frame_manifest.csv"
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1034:
        errors.append(f"Expected 1,034 frame records; found {len(rows)}")
    frame_ids = set()
    positive = 0
    empty = 0
    dimensions = set()
    for row in rows:
        frame_id = row["frame_id"]
        if frame_id in frame_ids:
            errors.append(f"Duplicate frame id: {frame_id}")
        frame_ids.add(frame_id)
        image_path = root / row["image_path"]
        mask_path = root / row["mask_path"]
        if not image_path.exists() or not mask_path.exists():
            errors.append(f"Missing pair for {frame_id}")
            continue
        if sha256(image_path) != row["image_sha256"]:
            errors.append(f"Image hash mismatch: {frame_id}")
        if sha256(mask_path) != row["mask_sha256"]:
            errors.append(f"Mask hash mismatch: {frame_id}")
        image = np.asarray(Image.open(image_path))
        mask = np.asarray(Image.open(mask_path))
        if image.shape != mask.shape:
            errors.append(f"Shape mismatch: {frame_id}")
        dimensions.add(tuple(image.shape))
        values = set(np.unique(mask).tolist())
        if not values.issubset({0, 255}):
            errors.append(f"Non-binary mask: {frame_id}")
        pixels = int((mask > 0).sum())
        if pixels != int(row["mask_positive_pixels"]):
            errors.append(f"Positive-pixel mismatch: {frame_id}")
        expected_present = pixels > 0
        if str(expected_present).lower() != row["mask_present"].lower():
            errors.append(f"mask_present mismatch: {frame_id}")
        positive += int(expected_present)
        empty += int(not expected_present)
        if row["split"] != "benchmark_only":
            errors.append(f"Single-specimen frame assigned to ML split: {frame_id}")
        if row["data_role"] != "experimental_public_benchmark":
            errors.append(f"Incorrect data role: {frame_id}")
        frame_number = int(row["source_frame_number"])
        expected_time = (frame_number - 3) / 55.0
        if not math.isclose(
            float(row["time_s_from_first_available"]),
            expected_time,
            rel_tol=0,
            abs_tol=1e-8,
        ):
            errors.append(f"Timestamp mismatch: {frame_id}")
        if len(errors) > 100:
            break

    if dimensions != {(234, 234)}:
        errors.append(f"Unexpected deposited dimensions: {sorted(dimensions)}")

    registry_path = root / "metadata" / "external_curved_sequence_registry.csv"
    with registry_path.open(newline="", encoding="utf-8") as handle:
        registry = list(csv.DictReader(handle))
    if len(registry) != 12:
        errors.append(f"Expected 12 external sequences; found {len(registry)}")
    specimen_splits: dict[str, set[str]] = defaultdict(set)
    total_bytes = 0
    for row in registry:
        specimen_splits[row["specimen_id"]].add(row["recommended_split"])
        total_bytes += int(row["source_file_size_bytes"])
        if row["licence"] != "CC BY 4.0":
            errors.append(f"Missing source licence: {row['sequence_id']}")
        if not row["download_url"].startswith("https://data.mendeley.com/"):
            errors.append(f"Non-authoritative URL: {row['sequence_id']}")
    leaking = [key for key, value in specimen_splits.items() if len(value) != 1]
    if leaking:
        errors.append(f"Specimens cross recommended splits: {leaking}")
    if total_bytes != 6_555_895_186:
        errors.append(f"External registry byte total mismatch: {total_bytes}")

    report = {
        "dataset": "T-COMP-PT",
        "version": "1.0.0",
        "status": "PASS" if not errors else "FAIL",
        "frame_rows_checked": len(rows),
        "positive_mask_frames": positive,
        "empty_mask_frames": empty,
        "deposited_dimensions": [list(item) for item in sorted(dimensions)],
        "external_sequences_checked": len(registry),
        "external_specimens": len(specimen_splits),
        "external_registered_bytes": total_bytes,
        "errors": errors,
        "warnings": warnings,
    }
    (root / "reports" / "qa_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
