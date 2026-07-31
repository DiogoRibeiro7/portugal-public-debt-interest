# Changelog

## v0.1.2 - 2026-07-31

- Cut a follow-up Zenodo-backed patch release.

## v0.1.1 - 2026-07-31

- Added Zenodo metadata for GitHub release archiving.
- Added ORCID and contact metadata to the citation file.
- Updated the manuscript author block with affiliations, ORCID number, and corresponding-author email.

## v0.1.0 - 2026-07-28

- Built the Portugal public-debt interest burden pipeline with Eurostat and AMECO ingestion.
- Added annual metrics, reconciliation checks, scenario calculations, comparator-panel outputs, plots, and Markdown reporting.
- Added CSV and SQLite persistence with validation on write and read.
- Hardened source parsing, configuration validation, annual-key handling, scenario inputs, report inputs, and comparator-panel flags.
- Added local fixture-based tests, linting, type checking, and GitHub Actions CI configuration.
- Added government expenditure and revenue measures in euros and as percentages of GDP.
- Added generated LaTeX table fragments, headline macros, vector figure outputs, and citation metadata.

## Verification

- `pytest`: 147 tests passed.
- `ruff check .`: passed.
- `mypy src`: passed.
- Live configured pipeline completed with `python -m pt_debt_interest.cli all --config config/default.yaml`.
- LaTeX table generation and report compilation completed.

## Known External Blocker

- GitHub Actions could not start because the GitHub account billing/spending limit blocks runner execution.
