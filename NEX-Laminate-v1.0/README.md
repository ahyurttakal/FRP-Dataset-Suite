# NEX-Laminate v1.0

**A provenance-controlled numerical-experimental evidence package for inverse laminate design**

NEX-Laminate v1.0 supports the first, data-oriented phase of the project
*Layup Optimization in Fiber Reinforced Polymers Using Generative Adversarial
Networks*. It is suitable for supervised forward modelling, conditional
generation, constrained inverse design, leakage-controlled benchmarking, and
selection of laminates for physical validation.

## What is included

| Evidence layer | Records | Status | Intended use |
| --- | ---: | --- | --- |
| Numerical CLT laminates | 10,000 | Included | Model development and inverse-design benchmarking |
| NCAMP experimental summary statistics | 49 | Included | Material-card provenance and environmental context |
| Planned paired laminate experiments | 12 designs x at least 3 replicates | Protocol only; not observed | Produce the paired numerical-experimental v2 validation subset |

The term **numerical-experimental evidence package** is deliberate. The release
contains both experimental evidence and numerical records, but it does not
pretend that the CLT labels are measured responses. Every numerical record is
marked `fidelity=F0_CLT`; every copied NCAMP statistic is marked
`data_role=experimental_summary_statistic`; every future test row is marked
`status=planned_not_observed`.

## Main files

- `data/numerical_clt_v1.csv.gz` - 10,000 machine-readable laminate records.
- `data/numerical_clt_v1_sample.csv` - first 250 records for quick inspection.
- `data/material_card.csv` - the exact SI material card used by the generator.
- `data/experimental_ncamp_lamina_summary.csv` - transcribed NCAMP Table 2-1
  summary values, with original and SI units.
- `metadata/data_dictionary.csv` - field definitions and units.
- `metadata/provenance.json` - sources, rules, split policy, and limitations.
- `protocols/minimum_experimental_plan.csv` - frozen minimum physical-validation
  design strata.
- `protocols/experimental_observation_schema.csv` - schema for future raw tests.
- `src/generate_inverse_dataset.py` - deterministic generator.
- `src/validate_inverse_dataset.py` - release validator.
- `notebooks/build_and_validate_inverse_dataset.ipynb` - executable workflow.
- `reports/qa_report.json` - machine-readable QA result.

## Design space

All laminates use the angle alphabet

\[
\Theta=\{0^\circ,+45^\circ,-45^\circ,90^\circ\}.
\]

The released sequences satisfy:

- symmetry;
- balance, \(n_{+45}=n_{-45}\);
- outer ply at \(+45^\circ\) or \(-45^\circ\);
- maximum contiguity of three identical adjacent plies;
- at least 10% of each standard orientation;
- nominal ply counts of 8, 12, 16, 20, or 24.

Adjacent-ply disorientation is reported but is not restricted below
\(90^\circ\) in v1. Researchers who require a \(45^\circ\) rule can filter
`max_disorientation_deg <= 45` without regenerating the database.

## Material evidence

The baseline material is Hexcel IM7/8552 unidirectional prepreg under
room-temperature-dry conditions. The elastic constants and strengths were
selected from the measured means in Table 2-1 of NCAMP report
CAM-RP-2009-015 Rev B. The report states that the qualification panels,
specimens, and test setups were conformed and testing was witnessed by the FAA.

The exact values used are in `data/material_card.csv`. They are not generic
internet values and they are not silently mixed across material systems.

Primary source:

<https://www.wichita.edu/industry_and_defense/NIAR/Documents/Qual-CAM-RP-2009-015-Rev-B-Hexcel-8552-IM7-MPDR-04.16.19.pdf>

## Mathematical labels

For a ply with reduced stiffness \(\mathbf Q\), the transformed stiffness is
\(\bar{\mathbf Q}^{(k)}(\theta_k)\). With ply interfaces \(z_k\),

\[
\mathbf A=\sum_{k=1}^{N}\bar{\mathbf Q}^{(k)}(z_k-z_{k-1}),
\quad
\mathbf B=\frac12\sum_{k=1}^{N}\bar{\mathbf Q}^{(k)}
(z_k^2-z_{k-1}^2),
\]

\[
\mathbf D=\frac13\sum_{k=1}^{N}\bar{\mathbf Q}^{(k)}
(z_k^3-z_{k-1}^3).
\]

The generator stores the independent components of \(\mathbf A\) and
\(\mathbf D\). The numerical symmetry check confirms \(\mathbf B\) is zero to
floating-point tolerance.

Field names distinguish the physical units explicitly: extensional-stiffness
components use the suffix `_N_per_m`, while bending-stiffness components use
`_N_m` for N m.

The in-plane engineering constants are obtained from
\(\mathbf a=\mathbf A^{-1}\):

\[
E_x=\frac{1}{a_{11}h},\qquad
E_y=\frac{1}{a_{22}h},\qquad
G_{xy}=\frac{1}{a_{66}h},\qquad
\nu_{xy}=-\frac{a_{12}}{a_{11}}.
\]

First-ply capacities are reported for six unit resultants. At every top and
bottom ply surface, the sign-dependent Tsai-Hill index is evaluated as

\[
FI=
\left(\frac{\sigma_1}{X}\right)^2
-\frac{\sigma_1\sigma_2}{X^2}
+\left(\frac{\sigma_2}{Y}\right)^2
+\left(\frac{\tau_{12}}{S}\right)^2,
\qquad
RF=FI_{\max}^{-1/2},
\]

where \(X\) and \(Y\) use tensile or compressive allowables according to the
local stress sign. A maximum-stress reserve factor is also included.

## Split policy

Random row splitting is prohibited.

- `equivalence_group_hash` groups each layup with its global
  \(+45^\circ/-45^\circ\) sign mirror.
- Groups, not rows, are deterministically assigned 70/15/15 to training,
  validation, and in-distribution test partitions.
- All 24-ply laminates are held out as `test_ood_thickness`.
- `reports/qa_report.json` confirms that no equivalence group crosses a split.

## Reproduction

From the dataset root:

```bash
python src/generate_inverse_dataset.py --output .
python src/validate_inverse_dataset.py --dataset .
```

The generator uses a fixed random seed (`20260729`) and writes a build report.
The notebook provides the same workflow with the mathematical definitions.

## What can be claimed from v1

Defensible claims:

- inverse-design performance inside the declared CLT design space;
- group-safe in-distribution performance;
- thickness out-of-distribution performance on 24-ply laminates;
- rule compliance and material-card provenance;
- computational speed relative to repeated CLT evaluation.

Claims that require v2 paired experiments and/or higher-fidelity simulation:

- landing-gear component strength, contact response, or drop-impact behaviour;
- progressive damage, delamination growth, residual strength, or fatigue life;
- calibrated prediction intervals for manufactured specimens;
- superiority to FEM or experiments;
- generalization to glass, hybrid, woven, or other resin systems.

## Experimental extension

The minimum plan freezes 12 design strata with at least three independent
replicates. Raw channels must be retained, exclusions must be declared before
analysis, and specimen/batch identifiers must be used for splitting. Relevant
current standards named in the protocol include ASTM D3039/D3039M-17(2025),
ASTM D3518/D3518M-18(2025), ASTM D7264/D7264M-21, and ASTM
D7136/D7136M-25. Obtain the official standards before conducting tests.

## External verification

Recommended independent checks:

- York's balanced/symmetric laminate database:
  <https://doi.org/10.17632/rys232ynhf.3>
- Double-Double Laminate Finder:
  <https://doi.org/10.17632/2xzwppwxrw.1>

## Licence and citation

Release-authored data tables are provided under CC BY 4.0 and code under the MIT
licence. The NCAMP source remains subject to its own public-release statement;
this release transcribes factual summary values and cites the report. See
`LICENSES.md` and `THIRD_PARTY_NOTICES.md`.

Before depositing a DOI, confirm author order and ORCIDs in `CITATION.cff` and
`zenodo.json`.
