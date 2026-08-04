#!/usr/bin/env python3
"""Fetch selected Erazo-Aux curved/planar/trapezoidal sequences.

Files are downloaded from the authoritative Mendeley Data URLs recorded in
metadata/external_curved_sequence_registry.csv. The repository does not expose
source checksums for these files, so this script records observed SHA-256 values
after download rather than pretending a checksum comparison was possible.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import urllib.request
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--split",
        choices=["all", "train", "validation", "test"],
        default="all",
    )
    parser.add_argument("--specimen", action="append", default=[])
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with args.registry.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    selected = [
        row
        for row in rows
        if (args.split == "all" or row["recommended_split"] == args.split)
        and (not args.specimen or row["specimen_id"] in args.specimen)
    ]
    receipts = []
    for row in selected:
        filename = (
            f"{row['specimen_id']}_facq-{row['frame_rate_hz']}Hz_"
            f"s-{row['inspection_side'].title()}_Img-2000.zip"
        )
        target = args.output_dir / filename
        request = urllib.request.Request(
            row["download_url"],
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/octet-stream"},
        )
        with urllib.request.urlopen(request) as response, target.open("wb") as handle:
            shutil.copyfileobj(response, handle)
        observed_size = target.stat().st_size
        expected_size = int(row["source_file_size_bytes"])
        if observed_size != expected_size:
            raise RuntimeError(
                f"Size mismatch for {filename}: {observed_size} != {expected_size}"
            )
        receipts.append(
            {
                "sequence_id": row["sequence_id"],
                "local_path": str(target),
                "observed_size_bytes": observed_size,
                "observed_sha256": sha256(target),
                "source_checksum_available": False,
            }
        )
    receipt_path = args.output_dir / "download_receipts.csv"
    with receipt_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(receipts[0]) if receipts else [])
        if receipts:
            writer.writeheader()
            writer.writerows(receipts)
    print(f"Downloaded {len(receipts)} sequences; receipts: {receipt_path}")


if __name__ == "__main__":
    main()
