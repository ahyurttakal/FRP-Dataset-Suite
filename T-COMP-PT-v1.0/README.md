# T-COMP-PT v1.0

**A provenance-controlled experimental thermography benchmark and curved-sequence registry for composite defect detection**

T-COMP-PT v1.0 supports the thermography phase of the project *Layup
Optimization in Fiber Reinforced Polymers Using Generative Adversarial
Networks*. It includes a complete public, expert-annotated CFRP benchmark and a
download-on-demand registry for a much larger CFRP/GFRP corpus containing
planar, curved, and trapezoidal specimens.

## Evidence layers

| Layer | Included bytes | Experimental scope | Intended use |
| --- | ---: | --- | --- |
| Garcia Vargas/Fernandes benchmark | Included | 1 CFRP/PEEK specimen, 1,034 images + 1,034 masks | Segmentation pretraining, pipeline QA, temporal analysis |
| Erazo-Aux et al. corpus | Registry only; 6.56 GB authoritative files | 6 specimens, 12 sequences, planar/curved/trapezoidal CFRP and GFRP | Specimen-grouped external testing and project-specific annotation |
| Project landing-gear thermography | Acquisition/annotation protocol required | Not yet observed | Final application-specific validation |

No artificial thermograms are represented as experimental data.

## Included benchmark

Primary dataset:

- Iago Garcia Vargas and Henrique Fernandes, *Thermal Inspection Dataset for
  Defect Segmentation in CFRP Laminates*, version 1, CC BY 4.0:
  <https://doi.org/10.17632/jrsb4b9yy5.1>
- Associated article:
  <https://doi.org/10.1080/10589759.2025.2457593>

Reported specimen:

- carbon/PEEK laminate;
- fibre volume fraction 61%;
- layup \([0_2/90_2]_6\);
- 100 mm x 100 mm;
- Kapton inserts at nominal depths 0.13, 0.26, and 0.39 mm;
- nominal sizes 2 x 2, 3 x 3, and 4 x 4 mm;
- pulsed thermography, MWIR camera, reported 55 Hz.

The deposit contains 1,034 paired grayscale PNGs. The source metadata reports
640 x 512 acquisition, but every deposited image and mask is 234 x 234 pixels.
This release preserves the deposited pixels, reports both dimensions, and does
not rescale or invent missing field of view.

Observed release QA:

- 1,034 paired frames;
- 786 frames with positive mask pixels;
- 248 empty-mask frames;
- 8 unique mask patterns across the 1,034 frames;
- 14 missing source frame numbers between deposited frames 3 and 1050;
- mask values restricted to 0 and 255;
- SHA-256 for every image and mask.

## External planar/curved/trapezoidal registry

Primary dataset:

- Jorge Erazo-Aux et al., *Thermal imagery from composite material academic
  samples*, version 2, CC BY 4.0:
  <https://doi.org/10.17632/v4knrwgj9y.2>
- Associated Data in Brief article:
  <https://doi.org/10.1016/j.dib.2020.106313>

The corpus contains CFRP and GFRP specimens with matched geometries:

- 006: planar;
- 007: curved;
- 008: trapezoidal.

Each 300 x 300 x 2 mm plate contains 25 Teflon inserts representing
delaminations. The article reports defect depths of 0.2-1.0 mm and sizes of
3-15 mm. Front and back inspections yield 12 sequences of approximately 2,000
frames at 512 x 512 pixels. The authoritative files total 6,555,895,186 bytes.

The complete registry is
`metadata/external_curved_sequence_registry.csv`. It contains authoritative
download URLs, repository file IDs, sizes, material, geometry, side, frame
rate, licence, and a specimen-grouped split. The repository API does not supply
source SHA-256 values; `src/fetch_curved_sequences.py` records observed hashes
after download and never claims an unavailable checksum match.

Example:

```bash
python src/fetch_curved_sequences.py \
  --registry metadata/external_curved_sequence_registry.csv \
  --output-dir external_sequences \
  --specimen CFRP-007
```

## Main files

- `data/public_benchmark/images/` - 1,034 deposited thermograms.
- `data/public_benchmark/masks/` - 1,034 deposited binary masks.
- `metadata/frame_manifest.csv` - frame-level pairing, hashes, timing, mask
  statistics, bounding boxes, and evidence role.
- `metadata/frame_data_dictionary.csv` - field definitions and units.
- `metadata/nominal_defect_catalog.csv` - nominal size/depth combinations; no
  unsupported pixel-to-defect mapping.
- `metadata/external_curved_sequence_registry.csv` - 12 authoritative external
  sequence records.
- `metadata/source_archives.csv` - source file IDs, sizes, URLs, and observed
  archive hashes used to build this release.
- `metadata/provenance.json` - evidence boundaries and limitations.
- `src/build_thermography_dataset.py` - deterministic builder.
- `src/validate_thermography_dataset.py` - paired-file validator.
- `src/fetch_curved_sequences.py` - selective external fetcher.
- `notebooks/build_and_validate_thermography_dataset.ipynb` - executable build
  and QA workflow.
- `reports/qa_report.json` - machine-readable QA result.

## Split policy

The included 1,034-frame benchmark comes from one specimen. Its `split` is
therefore `benchmark_only`. Frame-wise random train/test division would
measure near-duplicate temporal interpolation, not specimen-level
generalization. Five contiguous `temporal_block` labels are supplied only for
exploratory temporal sensitivity analyses.

The external corpus is split by specimen:

- train: CFRP-006, CFRP-007, GFRP-006, GFRP-007;
- validation: CFRP-008;
- test: GFRP-008.

Both inspection sides of a specimen remain in the same partition.

For the final project dataset, split by manufactured specimen and production
batch. Never split individual frames from one acquisition across partitions.

## Recommended project acquisition

The project-specific curved landing-gear dataset should follow a frozen
protocol aligned with ASTM E2582-21(2025), while recognizing the standard's
view-angle and surface-emissivity limitations. At minimum, record:

- specimen, material batch, cure cycle, layup hash, geometry revision;
- defect type, creation method, nominal size, depth, coordinates, and
  independent verification method;
- camera model/serial, lens, spectral band, integration time, frame rate,
  calibration date, emissivity setting, and camera-to-surface pose;
- pulse energy, duration, flash arrangement, trigger timing, ambient
  temperature, and surface preparation;
- raw radiometric sequence before normalization;
- calibration targets and nonuniformity correction;
- expert masks in original coordinates, annotator IDs, adjudication, and
  uncertainty flags.

Minimum design:

- sound controls and deliberately defective specimens;
- planar coupons for calibration plus curved landing-gear-like specimens;
- at least three independently manufactured replicates per design condition;
- front/back or multiple view angles where physically justified;
- specimen-level train/validation/test partitions fixed before modelling.

## Labels and metrics

Use segmentation metrics (Dice, IoU, pixel precision/recall) for masks and
detection metrics (AP at declared IoU thresholds) for instances. Accuracy alone
is inadequate because most pixels are background. Report results per specimen,
defect size, defect depth, geometry, material, and time after pulse.

The source masks are frame-level visible regions. The deposit does not provide
a defensible pixel-to-specific-nominal-defect mapping; this release does not
invent one.

## Reproduction

If the three source files are available:

```bash
python src/build_thermography_dataset.py \
  --source-dir source_cache \
  --output .
python src/validate_thermography_dataset.py --dataset .
```

The notebook can fetch the three 32.6 MB source files from the authoritative
repository, rebuild the paired release, and rerun QA.

## Licence and citation

The included images, masks, and derived metadata retain the source CC BY 4.0
licence. Release-authored code is MIT licensed. Cite both the relevant primary
source dataset and this derived release DOI after deposit. See `LICENSES.md`
and `THIRD_PARTY_NOTICES.md`.

Before depositing a DOI, confirm author order and ORCIDs in `CITATION.cff` and
`zenodo.json`.
