# Contributing

Contributions should preserve the evidence boundaries, provenance, and
reproducibility guarantees of each release.

1. Create a focused branch and describe the affected release.
2. Do not replace third-party bytes or alter source attribution silently.
3. Document every schema change in the relevant data dictionary and README.
4. Regenerate the affected release SHA-256 manifest after an intentional file
   change.
5. Run `python scripts/validate_all.py` before opening a pull request.
6. Include the scientific rationale, compatibility impact, and validation
   result in the pull-request description.

New experiments must be identified as observed only when raw measurements,
specimen identifiers, acquisition metadata, and exclusions are available.
Planned protocols and analytical labels must remain distinguishable from
experimental observations.

