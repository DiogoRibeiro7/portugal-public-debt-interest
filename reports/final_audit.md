# Final Audit

## Verification Run

Date: 2026-08-09

Audit subject: package version 0.6.0, source commit `187193e`.

### Test status depends on the environment, and both are recorded

An earlier version of this audit reported only the first line below, which
is true of a populated working tree and not of what a reviewer receives.
A clean checkout skips tests whose inputs are generated rather than
committed -- processed repricing artefacts, cross-paper outputs, and checks
that need a git worktree. Those skips are expected, not failures.

| Environment | Result |
| --- | --- |
| Author's populated working tree at commit `187193e` | 371 passed, 0 skipped |
| Reviewer clean checkout of the prior revision-6 archive, no pipeline run | 345 passed, 19 skipped |

Both runs reported zero failures. The clean-checkout row is retained because it
corrects the release-note count a reviewer observed in the submitted archive.
A reviewer wanting the full local suite should run `pt-debt all` and
`pt-debt repricing build-panel` before `pt-debt repricing all`.

Commands completed successfully in the author's environment:

- `pytest`: 371 passed, 4 warnings.
- `ruff check .`: passed.
- `mypy src`: passed, no issues in 35 source files.
- `pytest tests/test_repricing_kernel.py tests/test_repricing_estimate.py tests/test_repricing_simulate.py tests/test_repricing_manuscript.py tests/test_release_metadata.py`: 70 passed.
- `pt-debt repricing build-panel --config config/repricing.yaml`: completed.
- `pt-debt repricing all --config config/repricing.yaml`: completed.
- `pdflatex -interaction=nonstopmode -halt-on-error portugal_public_debt_interest_report.tex`: completed.
- `pdflatex -interaction=nonstopmode -halt-on-error repricing_kernel.tex`: completed twice.

The live source-acquisition workflow was not rerun during this audit pass. The
committed release artefacts remain guarded by the burden-paper checksum baseline,
and live regeneration remains documented in `docs/reproducibility.md`.

## Release Artefacts

- Main PDF: `paper/portugal_public_debt_interest_report.pdf`.
- Main PDF page count: 27.
- Main PDF SHA-256:
  `4d588e6e17bb322292611e548f43124b1edbcfc4e2dd0275cf126eb199fd0dd9`.
- Main LaTeX source: `paper/portugal_public_debt_interest_report.tex`.
- Generated paper tables: `reports/tables/`.
- Generated paper figures: committed PDF figures under `reports/figures/`.
- Repricing manuscript: `paper/repricing/repricing_kernel.tex` and
  `paper/repricing/repricing_kernel.pdf`.
- Repricing PDF page count: 15.
- Repricing PDF SHA-256:
  `6a5d3f9fed21166a6bf6bfdf7ff62675508ad41168fd201db322c47ce2446812`.
- Release metadata: `CITATION.cff`, `.zenodo.json`, `pyproject.toml`, and
  `CHANGELOG.md`.

The repository intentionally does not commit substantive files under `data/raw`,
`data/interim`, or `data/processed`; only `.gitkeep` placeholders are tracked in
those directories. Local ignored data may exist in a working copy, but they are
not part of the submitted source archive.

## Data and Method Checks

- The main burden paper uses the 1995-2025 Eurostat ESA 2010 sample for
  historical empirical figures, tables, and decompositions.
- Portugal's 2024 and 2025 comparison rows are isolated in the provisional-year
  robustness appendix.
- The 1997-1998 debt-ratio discrepancy is reported as a bounded measurement
  issue and is not left as an uninterpreted warning.
- Euro-area ranks use the comparison-year membership universe, exclude
  aggregates, disclose provisional status, and use competition ranking.
- Cross-country average-debt-rate language is descriptive and no longer treats
  the measure as a directly comparable funding-cost ranking.
- The main burden paper no longer imports the companion repricing paper's former
  10.90 percentage-point or EUR 300 million point claims.
- Refinancing scenarios are labelled as stylised deterministic scenarios and
  disclose that the central path uses the IGCP 2024 average-maturity statistic.
- The burden paper cites the companion repricing paper under its current title:
  `What Reprices and How Fast in Weighted-Average-Maturity Pass-Through`.
- The repricing manuscript now frames weighted average maturity as an
  incomplete timing statistic and presents uncertainty rather than a single
  identified behavioural correction.
- Current repricing support reports no longer repeat the superseded 10.90
  percentage-point or EUR 300 million claims, and the manuscript states that
  the central scenario-minus-WAM difference changes sign after the one-year
  horizon.

## Remaining Warnings

- The validation report retains a warning for the debt-ratio reconciliation in
  1997 and 1998. The paper now reports and interprets that warning.
- The current LaTeX builds report no overfull boxes and no undefined
  references. The repricing bibliography retains one harmless underfull line.
- Dependency resolution is locked by `poetry.lock`. Platform-specific wheel
  resolution should still be recorded through `pip freeze` in CI and release
  logs.
- A clean-room container rebuild was not performed in this audit pass.

## Archived Audits

The earlier July blocking audit has been moved to
`reports/archive/final_blocking_acceptance_audit_2026-07-31.md`. It is retained
as history only and should not be read as the current release audit.
