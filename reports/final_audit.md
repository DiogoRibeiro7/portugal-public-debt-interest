# Final Audit

## Verification Run

Date: 2026-08-07

Audit subject: package version 0.5.0, source commit
`3abfa50` plus the release bump in this
working tree.

Commands completed successfully in the current environment:

- `pytest`: 353 passed, 4 warnings.
- `ruff check .`: passed.
- `mypy src`: passed, no issues in 35 source files.
- `poetry check --lock`: completed; Poetry reported warnings about duplicated
  legacy `[tool.poetry]` metadata and static PEP 621 metadata.
- `poetry install --with dev --no-interaction`: completed from `poetry.lock`.
- `poetry run pytest tests/test_release_metadata.py`: 10 passed.
- `python -m pt_debt_interest.cli tables`: completed.
- `pdflatex -interaction=nonstopmode -halt-on-error portugal_public_debt_interest_report.tex`: completed.

The live source-acquisition workflow was not rerun during this audit pass. The
committed release artefacts remain guarded by the burden-paper checksum baseline,
and live regeneration remains documented in `docs/reproducibility.md`.

## Release Artefacts

- Main PDF: `paper/portugal_public_debt_interest_report.pdf`.
- Main PDF page count: 27.
- Main PDF SHA-256:
  `77760ab76bb66a289fded1783c657d23b7aae6ea68ab7c1b48748366c5f052ca`.
- Main LaTeX source: `paper/portugal_public_debt_interest_report.tex`.
- Generated paper tables: `reports/tables/`.
- Generated paper figures: committed PDF figures under `reports/figures/`.
- Repricing manuscript: `paper/repricing/repricing_kernel.tex` and
  `paper/repricing/repricing_kernel.pdf`.
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
- The repricing manuscript now frames weighted average maturity as an
  incomplete timing statistic and presents uncertainty rather than a single
  identified behavioural correction.
- Current repricing support reports no longer repeat the superseded 10.90
  percentage-point or EUR 300 million claims, and the manuscript states that
  the central bias changes sign after the one-year horizon.

## Remaining Warnings

- The validation report retains a warning for the debt-ratio reconciliation in
  1997 and 1998. The paper now reports and interprets that warning.
- The main LaTeX build reports one small overfull line in the research-question
  paragraph, about 1.43 pt. The PDF builds successfully.
- Dependency resolution is locked by `poetry.lock`. Platform-specific wheel
  resolution should still be recorded through `pip freeze` in CI and release
  logs.
- A clean-room container rebuild was not performed in this audit pass.

## Archived Audits

The earlier July blocking audit has been moved to
`reports/archive/final_blocking_acceptance_audit_2026-07-31.md`. It is retained
as history only and should not be read as the current release audit.
