# FRP Dataset Suite

Versioned datasets for manufacturing-constrained composite laminate design and
thermographic inspection. This repository accompanies a Scientific Data Data
Descriptor and keeps the two releases separate because their observational
units, evidence levels, and validation rules are not row-compatible.

## Releases

| Release | Contents | Evidence level | Primary use |
| --- | --- | --- | --- |
| [NEX-Laminate v1.0](NEX-Laminate-v1.0/) | 10,000 manufacturing-constrained IM7/8552 layups with deterministic classical lamination theory labels | Analytical labels plus cited material-property summaries | Forward modelling, constrained inverse design, and group-safe benchmarking |
| [T-COMP-PT v1.0](T-COMP-PT-v1.0/) | 1,034 deposited thermogram-mask pairs and a registry of 12 external CFRP/GFRP sequences | Reused experimental pixels, derived metadata, and registry-only external files | Pipeline validation, temporal analysis, and specimen-grouped thermography studies |

The releases can support sequential design-and-inspection research, but they
must not be joined row by row. A defensible future connection requires a
manufactured specimen carrying the NEX layup hash together with material,
manufacturing, geometry, and thermography acquisition identifiers.

## Repository layout

```text
FRP-Dataset-Suite/
├── NEX-Laminate-v1.0/       # numerical laminate release
├── T-COMP-PT-v1.0/          # thermography release
├── scripts/validate_all.py  # cross-platform integrity and QA runner
├── requirements.txt         # runtime dependencies
├── environment.yml          # optional Conda environment
├── UPLOAD_TO_GITHUB.md       # command-line upload instructions
├── REFERENCES.bib           # primary data and material sources
├── CITATION.cff             # GitHub citation metadata
├── LICENSE                  # suite-level licensing notice
└── .github/workflows/       # automated validation
```

Each release retains its own README, citation metadata, provenance, data
dictionary, build and QA reports, licence notices, source code, notebook, and
SHA-256 manifest.

For publication, follow [UPLOAD_TO_GITHUB.md](UPLOAD_TO_GITHUB.md).

## Quick validation

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
```

Linux or macOS activation:

```bash
source .venv/bin/activate
```

Windows PowerShell activation:

```powershell
.venv\Scripts\Activate.ps1
```

Install the dependencies and run all checks:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/validate_all.py
```

The validation runner checks every file against the release SHA-256 manifests
and then executes both release validators. A successful run ends with
`All repository checks passed.` The same validation runs automatically through
GitHub Actions on pushes and pull requests.

## Important evidence boundaries

- NEX labels are deterministic CLT outputs at fidelity `F0_CLT`; they are not
  measurements from the generated layups.
- The NEX physical-test files contain a frozen plan marked
  `planned_not_observed`, not completed experiments.
- The included T-COMP benchmark comes from one specimen and contains 1,034
  unique images but only eight unique mask patterns. It is fixed as
  `benchmark_only`; random frame-level train/test splitting is not a valid
  specimen-level generalization test.
- The 6.56 GB external thermography corpus is cited and registered but is not
  redistributed here.
- The primary T-COMP images and masks retain their source attribution and CC BY
  4.0 terms.

## Primary sources

- NCAMP, *Hexcel 8552 IM7 Unidirectional Prepreg 190 gsm & 35% RC
  Qualification Material Property Data Report*, CAM-RP-2009-015 Rev. B (2019).
- Garcia Vargas and Fernandes, *Thermal Inspection Dataset for Defect
  Segmentation in CFRP Laminates*, Mendeley Data v1,
  <https://doi.org/10.17632/jrsb4b9yy5.1>.
- Erazo-Aux et al., *Thermal imagery from composite material academic
  samples*, Mendeley Data v2, <https://doi.org/10.17632/v4knrwgj9y.2>.
- York, *Balanced and Symmetric Laminates with Bending--Twisting Coupling*,
  Mendeley Data v3, <https://doi.org/10.17632/rys232ynhf.3>.
- Shabani, Li, and Laliberte, *Double--Double Laminate Finder*, Mendeley Data
  v1, <https://doi.org/10.17632/2xzwppwxrw.1>.

Machine-readable records are provided in [REFERENCES.bib](REFERENCES.bib).

## Citation

Use the repository's **Cite this repository** menu for the suite-level citation.
When using a specific release, also cite its local `CITATION.cff` and all
applicable primary sources. Replace or extend citation metadata only after the
author list, ORCIDs, repository URL, and archival DOI have been finalized.

## Licence

Release-authored data and metadata are distributed under CC BY 4.0 and
release-authored code under the MIT License. Third-party data retain their
original terms and required attribution. See [LICENSE](LICENSE) and each
release's `LICENSES.md` and `THIRD_PARTY_NOTICES.md` before redistribution.
