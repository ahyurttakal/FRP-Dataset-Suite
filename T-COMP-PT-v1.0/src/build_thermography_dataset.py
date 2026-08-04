#!/usr/bin/env python3
"""Build T-COMP-PT v1.0 from the deposited Garcia Vargas/Fernandes files.

The builder preserves the original frame numbers, creates paired image/mask
records with hashes, and registers (without duplicating) the 6.56 GB
Erazo-Aux et al. curved/planar/trapezoidal sequence corpus.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image


VERSION = "1.0.0"
ANNOTATED_DOI = "https://doi.org/10.17632/jrsb4b9yy5.1"
ANNOTATED_PAPER = "https://doi.org/10.1080/10589759.2025.2457593"
CURVED_DOI = "https://doi.org/10.17632/v4knrwgj9y.2"
CURVED_PAPER = "https://doi.org/10.1016/j.dib.2020.106313"
CC_BY = "https://creativecommons.org/licenses/by/4.0/"
FPS = 55.0


SOURCE_FILES = [
    {
        "repository_file_id": "7758b5e6-3c8a-4cf5-afd8-94d9ccc8c194",
        "filename": "annotatedData.zip",
        "expected_size_bytes": 345509,
        "download_url": (
            "https://data.mendeley.com/public-files/datasets/jrsb4b9yy5/files/"
            "7758b5e6-3c8a-4cf5-afd8-94d9ccc8c194/file_downloaded"
        ),
    },
    {
        "repository_file_id": "d01f1ed6-eeb3-4d86-8b10-cf70838efdf1",
        "filename": "originalData.zip",
        "expected_size_bytes": 32259334,
        "download_url": (
            "https://data.mendeley.com/public-files/datasets/jrsb4b9yy5/files/"
            "d01f1ed6-eeb3-4d86-8b10-cf70838efdf1/file_downloaded"
        ),
    },
    {
        "repository_file_id": "1d758af1-9a13-4a98-89f2-e25e8539c334",
        "filename": "Thermography_Dataset_Readme.txt",
        "expected_size_bytes": 2588,
        "download_url": (
            "https://data.mendeley.com/public-files/datasets/jrsb4b9yy5/files/"
            "1d758af1-9a13-4a98-89f2-e25e8539c334/file_downloaded"
        ),
    },
]


CURVED_FILES = [
    ("CFRP-006", "CFRP", "planar", "Back", 120, 546057230, "3c430a30-97f6-41b0-b383-5f4a2cec1364"),
    ("CFRP-006", "CFRP", "planar", "Front", 145, 538735726, "a88624e0-63fc-4616-9fac-93866a9542eb"),
    ("CFRP-007", "CFRP", "curved", "Back", 120, 547332235, "66e6218a-5b5c-4332-84fc-0e9c3ef2eb3d"),
    ("CFRP-007", "CFRP", "curved", "Front", 145, 538799283, "28753602-2e01-43c5-a803-4f1bfa4edcff"),
    ("CFRP-008", "CFRP", "trapezoidal", "Back", 120, 535407311, "0b7c8b2a-06cc-4272-b20f-ae0c059fea1f"),
    ("CFRP-008", "CFRP", "trapezoidal", "Front", 145, 551761598, "6ce9b367-566c-41bb-b93c-6c78938f632a"),
    ("GFRP-006", "GFRP", "planar", "Back", 120, 564843091, "b47c668f-1472-4223-98bf-036b3737b027"),
    ("GFRP-006", "GFRP", "planar", "Front", 145, 570871749, "46c0bd4f-d407-43e5-b0e8-71a3ee04430a"),
    ("GFRP-007", "GFRP", "curved", "Back", 120, 538731688, "0285f679-9e37-40d4-92bc-9c1ed46fa593"),
    ("GFRP-007", "GFRP", "curved", "Front", 145, 545677702, "97363b5f-9f7e-436a-bac2-8e46155ec36c"),
    ("GFRP-008", "GFRP", "trapezoidal", "Back", 120, 538493168, "227127e0-bff4-4173-b203-10ba46f4b5d8"),
    ("GFRP-008", "GFRP", "trapezoidal", "Front", 145, 539184405, "d53a3cd3-4b13-4c71-bee0-3b4026068cca"),
]


FRAME_FIELDS = [
    "frame_id",
    "source_dataset_id",
    "source_specimen_id",
    "source_frame_number",
    "time_s_from_first_available",
    "frame_rate_hz_reported",
    "image_path",
    "mask_path",
    "image_sha256",
    "mask_sha256",
    "width_px_deposited",
    "height_px_deposited",
    "source_acquisition_width_px_reported",
    "source_acquisition_height_px_reported",
    "mask_present",
    "mask_positive_pixels",
    "mask_area_fraction",
    "bbox_xmin_px",
    "bbox_ymin_px",
    "bbox_xmax_px",
    "bbox_ymax_px",
    "temporal_block",
    "split",
    "data_role",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def png_members(archive: Path, prefix: str) -> dict[int, str]:
    out = {}
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            match = re.fullmatch(rf"{re.escape(prefix)}/(\d+)\.png", name)
            if match:
                out[int(match.group(1))] = name
    return out


def extract_member(zf: zipfile.ZipFile, member: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with zf.open(member) as source, target.open("wb") as destination:
        shutil.copyfileobj(source, destination)


def write_source_archive_manifest(source_dir: Path, output_dir: Path) -> None:
    fields = [
        "repository_file_id",
        "filename",
        "expected_size_bytes",
        "observed_size_bytes",
        "observed_sha256",
        "download_url",
        "source_dataset_doi",
        "licence",
    ]
    with (output_dir / "metadata" / "source_archives.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for source in SOURCE_FILES:
            path = source_dir / source["filename"]
            writer.writerow(
                {
                    **source,
                    "observed_size_bytes": path.stat().st_size,
                    "observed_sha256": sha256(path),
                    "source_dataset_doi": ANNOTATED_DOI,
                    "licence": "CC BY 4.0",
                }
            )


def write_curved_registry(output_dir: Path) -> None:
    fields = [
        "sequence_id",
        "specimen_id",
        "material_family",
        "geometry",
        "inspection_side",
        "frame_rate_hz",
        "reported_frames",
        "reported_resolution_px",
        "plate_dimensions_mm",
        "defect_surrogate",
        "reported_defect_count",
        "reported_defect_depth_range_mm",
        "reported_defect_size_range_mm",
        "source_file_size_bytes",
        "repository_file_id",
        "download_url",
        "source_dataset_doi",
        "associated_article_doi",
        "licence",
        "recommended_split",
        "checksum_status",
    ]
    rows = []
    for specimen, material, geometry, side, fps, size, file_id in CURVED_FILES:
        if specimen in {"CFRP-006", "CFRP-007", "GFRP-006", "GFRP-007"}:
            split = "train"
        elif specimen == "CFRP-008":
            split = "validation"
        else:
            split = "test"
        filename = f"{specimen}_facq-{fps}Hz_s-{side}_Img-2000.zip"
        rows.append(
            {
                "sequence_id": f"{specimen}_{side.lower()}",
                "specimen_id": specimen,
                "material_family": material,
                "geometry": geometry,
                "inspection_side": side.lower(),
                "frame_rate_hz": fps,
                "reported_frames": 2000,
                "reported_resolution_px": "512x512",
                "plate_dimensions_mm": "300x300x2",
                "defect_surrogate": "Teflon inserts representing delamination",
                "reported_defect_count": 25,
                "reported_defect_depth_range_mm": "0.2-1.0",
                "reported_defect_size_range_mm": "3-15",
                "source_file_size_bytes": size,
                "repository_file_id": file_id,
                "download_url": (
                    "https://data.mendeley.com/public-files/datasets/"
                    f"v4knrwgj9y/files/{file_id}/file_downloaded"
                ),
                "source_dataset_doi": CURVED_DOI,
                "associated_article_doi": CURVED_PAPER,
                "licence": "CC BY 4.0",
                "recommended_split": split,
                "checksum_status": "not_supplied_by_repository_api; compute_after_download",
            }
        )
    with (output_dir / "metadata" / "external_curved_sequence_registry.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_defect_catalog(output_dir: Path) -> None:
    fields = [
        "nominal_defect_id",
        "insert_material",
        "nominal_size_mm",
        "nominal_depth_mm",
        "pixel_mapping_status",
        "source_dataset_doi",
    ]
    rows = []
    index = 1
    for depth in (0.13, 0.26, 0.39):
        for size in (2, 3, 4):
            rows.append(
                {
                    "nominal_defect_id": f"KAPTON-{index:02d}",
                    "insert_material": "Kapton tape",
                    "nominal_size_mm": f"{size}x{size}",
                    "nominal_depth_mm": depth,
                    "pixel_mapping_status": (
                        "not provided in deposit; masks are frame-level visible regions"
                    ),
                    "source_dataset_doi": ANNOTATED_DOI,
                }
            )
            index += 1
    with (output_dir / "metadata" / "nominal_defect_catalog.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_data_dictionary(output_dir: Path) -> None:
    descriptions = {
        "frame_id": ("string", "", "Stable frame identifier."),
        "source_dataset_id": ("string", "", "DOI-keyed source dataset label."),
        "source_specimen_id": ("string", "", "Deposited specimen identifier."),
        "source_frame_number": ("integer", "frame", "Original deposited filename stem."),
        "time_s_from_first_available": (
            "number",
            "s",
            "(source frame number - first deposited frame number) / reported 55 Hz.",
        ),
        "frame_rate_hz_reported": ("number", "Hz", "Frame rate reported by depositor."),
        "image_path": ("string", "", "Release-relative thermal image path."),
        "mask_path": ("string", "", "Release-relative binary mask path."),
        "image_sha256": ("string", "", "SHA-256 of deposited PNG bytes."),
        "mask_sha256": ("string", "", "SHA-256 of deposited mask PNG bytes."),
        "width_px_deposited": ("integer", "pixel", "Actual PNG width."),
        "height_px_deposited": ("integer", "pixel", "Actual PNG height."),
        "source_acquisition_width_px_reported": (
            "integer",
            "pixel",
            "Acquisition width stated by source metadata.",
        ),
        "source_acquisition_height_px_reported": (
            "integer",
            "pixel",
            "Acquisition height stated by source metadata.",
        ),
        "mask_present": ("boolean", "", "True when at least one mask pixel is positive."),
        "mask_positive_pixels": ("integer", "pixel", "Count of mask pixels equal to 255."),
        "mask_area_fraction": ("number", "fraction", "Positive mask pixels / image pixels."),
        "bbox_xmin_px": ("integer", "pixel", "Positive-mask bounding box left edge."),
        "bbox_ymin_px": ("integer", "pixel", "Positive-mask bounding box top edge."),
        "bbox_xmax_px": ("integer", "pixel", "Positive-mask bounding box right edge, inclusive."),
        "bbox_ymax_px": ("integer", "pixel", "Positive-mask bounding box bottom edge, inclusive."),
        "temporal_block": (
            "integer",
            "",
            "One of five contiguous exploratory temporal blocks; not a specimen split.",
        ),
        "split": (
            "category",
            "",
            "benchmark_only because all 1,034 frames come from one specimen.",
        ),
        "data_role": (
            "category",
            "",
            "experimental_public_benchmark; never synthetic.",
        ),
    }
    with (output_dir / "metadata" / "frame_data_dictionary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(["field", "type", "unit", "description"])
        for field in FRAME_FIELDS:
            writer.writerow([field, *descriptions[field]])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source_dir = args.source_dir.resolve()
    output_dir = args.output.resolve()
    for subdir in (
        "data/public_benchmark/images",
        "data/public_benchmark/masks",
        "metadata",
        "reports",
        "third_party",
    ):
        (output_dir / subdir).mkdir(parents=True, exist_ok=True)

    for source in SOURCE_FILES:
        path = source_dir / source["filename"]
        if not path.exists():
            raise FileNotFoundError(path)
        if path.stat().st_size != source["expected_size_bytes"]:
            raise ValueError(f"Unexpected source file size: {path}")

    image_zip = source_dir / "originalData.zip"
    mask_zip = source_dir / "annotatedData.zip"
    images = png_members(image_zip, "originalData")
    masks = png_members(mask_zip, "annotatedData")
    if set(images) != set(masks):
        raise ValueError("Deposited image and mask identifiers do not match.")

    frame_numbers = sorted(images)
    first_frame = frame_numbers[0]
    manifest_path = output_dir / "metadata" / "frame_manifest.csv"
    positive_frames = 0
    mask_pixel_counts: Counter[int] = Counter()
    with zipfile.ZipFile(image_zip) as image_zf, zipfile.ZipFile(mask_zip) as mask_zf, manifest_path.open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=FRAME_FIELDS)
        writer.writeheader()
        for rank, frame_number in enumerate(frame_numbers):
            image_target = (
                output_dir
                / "data"
                / "public_benchmark"
                / "images"
                / f"frame_{frame_number:04d}.png"
            )
            mask_target = (
                output_dir
                / "data"
                / "public_benchmark"
                / "masks"
                / f"frame_{frame_number:04d}.png"
            )
            extract_member(image_zf, images[frame_number], image_target)
            extract_member(mask_zf, masks[frame_number], mask_target)
            image = np.asarray(Image.open(image_target))
            mask = np.asarray(Image.open(mask_target))
            if image.shape != mask.shape:
                raise ValueError(f"Shape mismatch for frame {frame_number}")
            unique_mask = set(np.unique(mask).tolist())
            if not unique_mask.issubset({0, 255}):
                raise ValueError(f"Non-binary mask for frame {frame_number}")
            ys, xs = np.where(mask > 0)
            pixels = int(len(xs))
            present = pixels > 0
            positive_frames += int(present)
            mask_pixel_counts[pixels] += 1
            block = min(4, int(rank * 5 / len(frame_numbers)))
            writer.writerow(
                {
                    "frame_id": f"GVF-2025-{frame_number:04d}",
                    "source_dataset_id": "jrsb4b9yy5_v1",
                    "source_specimen_id": "CPEEK_PANEL_001",
                    "source_frame_number": frame_number,
                    "time_s_from_first_available": f"{(frame_number-first_frame)/FPS:.9f}",
                    "frame_rate_hz_reported": FPS,
                    "image_path": image_target.relative_to(output_dir).as_posix(),
                    "mask_path": mask_target.relative_to(output_dir).as_posix(),
                    "image_sha256": sha256(image_target),
                    "mask_sha256": sha256(mask_target),
                    "width_px_deposited": image.shape[1],
                    "height_px_deposited": image.shape[0],
                    "source_acquisition_width_px_reported": 640,
                    "source_acquisition_height_px_reported": 512,
                    "mask_present": present,
                    "mask_positive_pixels": pixels,
                    "mask_area_fraction": f"{pixels / image.size:.12g}",
                    "bbox_xmin_px": "" if not present else int(xs.min()),
                    "bbox_ymin_px": "" if not present else int(ys.min()),
                    "bbox_xmax_px": "" if not present else int(xs.max()),
                    "bbox_ymax_px": "" if not present else int(ys.max()),
                    "temporal_block": block,
                    "split": "benchmark_only",
                    "data_role": "experimental_public_benchmark",
                }
            )

    shutil.copy2(
        source_dir / "Thermography_Dataset_Readme.txt",
        output_dir / "third_party" / "Thermography_Dataset_Readme.txt",
    )
    write_source_archive_manifest(source_dir, output_dir)
    write_curved_registry(output_dir)
    write_defect_catalog(output_dir)
    write_data_dictionary(output_dir)

    provenance = {
        "dataset": "T-COMP-PT",
        "version": VERSION,
        "generated_utc": "2026-07-29T00:00:00Z",
        "included_benchmark": {
            "doi": ANNOTATED_DOI,
            "associated_article": ANNOTATED_PAPER,
            "licence": "CC BY 4.0",
            "frames": len(frame_numbers),
            "specimens": 1,
            "deposited_png_shape": [234, 234],
            "reported_acquisition_resolution": [640, 512],
            "resolution_discrepancy": (
                "The source metadata reports 640x512 acquisition, while every deposited "
                "PNG is a 234x234 crop. The release preserves deposited pixels."
            ),
        },
        "registered_external_corpus": {
            "doi": CURVED_DOI,
            "associated_article": CURVED_PAPER,
            "licence": "CC BY 4.0",
            "sequences": 12,
            "specimens": 6,
            "bytes": sum(row[5] for row in CURVED_FILES),
            "included_in_archive": False,
            "reason": "6.56 GB; fetched on demand from the authoritative repository.",
        },
        "split_policy": {
            "included_benchmark": (
                "benchmark_only: one specimen cannot support specimen-independent claims."
            ),
            "external_registry": (
                "Specimen grouped: 006/007 train, CFRP-008 validation, GFRP-008 test."
            ),
        },
        "licence_url": CC_BY,
        "known_limitations": [
            "The included masks are visible-region, frame-level masks; a pixel-to-specific-defect mapping is not deposited.",
            "The included benchmark contains one specimen and cannot by itself estimate specimen-level generalization.",
            "The curved corpus has no expert segmentation masks in the repository; annotations must be created under a frozen protocol.",
            "Frame timestamps are inferred from source frame numbers and the reported 55 Hz acquisition rate.",
        ],
    }
    (output_dir / "metadata" / "provenance.json").write_text(
        json.dumps(provenance, indent=2), encoding="utf-8"
    )
    report = {
        "dataset": "T-COMP-PT",
        "version": VERSION,
        "included_frames": len(frame_numbers),
        "positive_mask_frames": positive_frames,
        "empty_mask_frames": len(frame_numbers) - positive_frames,
        "deposited_shape": [234, 234],
        "source_frame_min": min(frame_numbers),
        "source_frame_max": max(frame_numbers),
        "source_frame_gaps": (
            max(frame_numbers) - min(frame_numbers) + 1 - len(frame_numbers)
        ),
        "mask_positive_pixel_histogram": {
            str(key): value for key, value in sorted(mask_pixel_counts.items())
        },
        "external_sequences_registered": len(CURVED_FILES),
        "external_bytes_registered": sum(row[5] for row in CURVED_FILES),
    }
    (output_dir / "reports" / "build_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
