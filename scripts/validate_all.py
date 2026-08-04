#!/usr/bin/env python3
"""Validate release manifests and run both dataset-specific validators."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASES = (
    ROOT / "NEX-Laminate-v1.0",
    ROOT / "T-COMP-PT-v1.0",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_manifest(release: Path, manifest_name: str) -> None:
    manifest = release / manifest_name
    if not manifest.is_file():
        raise RuntimeError(f"Missing manifest: {manifest}")

    checked = 0
    for line_number, raw_line in enumerate(
        manifest.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not raw_line.strip():
            continue
        try:
            expected, relative = raw_line.split("  ", 1)
        except ValueError as exc:
            raise RuntimeError(
                f"Malformed manifest line {line_number}: {manifest}"
            ) from exc
        target = release / relative
        if not target.is_file():
            raise RuntimeError(f"Manifest target is missing: {target}")
        observed = sha256(target)
        if observed != expected:
            raise RuntimeError(f"SHA-256 mismatch: {target}")
        checked += 1
    print(f"PASS manifest: {release.name} ({checked} files)")


def run_validator(release: Path, script_name: str) -> None:
    command = [
        sys.executable,
        str(release / "src" / script_name),
        "--dataset",
        str(release),
    ]
    subprocess.run(command, check=True)
    print(f"PASS validator: {release.name}")


def main() -> None:
    verify_manifest(ROOT, "MANIFEST_SHA256.txt")
    for release in RELEASES:
        verify_manifest(release, "release_manifest_sha256.txt")

    run_validator(RELEASES[0], "validate_inverse_dataset.py")
    run_validator(RELEASES[1], "validate_thermography_dataset.py")
    print("All repository checks passed.")


if __name__ == "__main__":
    main()
