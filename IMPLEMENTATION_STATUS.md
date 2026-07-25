# Implementation status

## Completed

- Typed configuration and CLI.
- Eurostat JSON-stat ingestion and raw-response caching.
- AMECO ZIP/CSV extraction by dotted series code.
- Main 1995 onward ESA 2010 series and optional pre-1995 linked extension.
- Official-versus-calculated ratio reconciliation.
- Interest burden, implicit rate, GDP deflator, primary balance, and regime labels.
- Static and gradual refinancing scenarios.
- CSV and SQLite persistence.
- Five core figures and an automatic Markdown report.
- Network-free tests and a synthetic end-to-end integration run.

## Verified locally

- `pytest`: 4 tests passed.
- Python bytecode compilation completed.
- CLI help and command registration completed.
- Synthetic 1995–2025 integration run produced the processed dataset, validation output, five figures, and report.

## Not verified in this execution environment

External DNS/network access was unavailable from the build container. The live Eurostat and AMECO requests were therefore not executed here. The configured codes and endpoints are documented, and parsers are tested against local fixtures. The first live run should inspect source manifests and dimension checks before publishing analytical results.

`ruff` and `mypy` were not installed in the build container. They are included in the development dependencies and CI workflow, but no claim is made that those two checks were executed here.
