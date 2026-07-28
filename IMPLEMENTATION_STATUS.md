# Implementation status

## Completed

- Typed configuration and CLI.
- Eurostat JSON-stat ingestion with raw-response caching and source manifests.
- AMECO ZIP/CSV extraction by validated dotted series code.
- Main 1995 onward ESA 2010 series and optional pre-1995 linked extension.
- Official-versus-calculated ratio reconciliation.
- Interest burden, implicit rate, GDP deflator, primary balance, and regime labels.
- Static and gradual refinancing scenarios.
- CSV and SQLite persistence with annual-key validation on save and load.
- Comparator-panel metrics, ranks, missingness diagnostics, plots, and report summaries.
- Publication-oriented figures and automatic Markdown report generation.
- Network-free unit and integration tests with local fixtures.

## Verified locally

- `pytest`: 133 tests passed.
- `ruff check .`: passed.
- `mypy src`: passed.
- Live configured pipeline completed with `python -m pt_debt_interest.cli all --config config/default.yaml`.
- Live report generation completed with `python -m pt_debt_interest.cli report --config config/default.yaml`.

## Notes

- Generated raw, interim, processed, figure, and report artifacts are intentionally ignored except for `.gitkeep` placeholders.
- The repository is ready for normal development and publication workflow use.
- GitHub Actions should be checked after each push for the supported Python matrix.
