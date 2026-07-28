# Portugal Public-Debt Interest Burden

A reproducible analysis of the interest paid by Portugal's general government, in euros and as a percentage of GDP.

The authoritative series begins in 1995 and uses harmonised ESA 2010 data from Eurostat. An optional AMECO extension can add earlier observations, while preserving an explicit accounting-basis and observed/forecast distinction.

## Description

This project builds a transparent annual dataset for Portugal's public-debt interest burden. It downloads official Eurostat and AMECO data, reconciles interest, debt, GDP, and balance ratios, calculates derived metrics, and produces validation checks, charts, and a Markdown report suitable for research or publication workflows.

## Research questions

- How much interest does Portugal's general government pay each year?
- How has the burden changed relative to nominal GDP?
- Was the decline driven by lower effective rates, a lower debt ratio, nominal growth, or inflation?
- How quickly do market-rate changes pass through to the effective cost of the debt stock?
- How does Portugal compare with Spain, Italy, Greece, Ireland, the euro area, and selected low-risk benchmarks?

## Main outputs

- `data/processed/portugal_debt_interest.csv`: annual analytical dataset.
- `data/processed/portugal_debt_interest.sqlite`: optional SQL copy.
- `data/processed/eurostat_panel_metrics.csv`: optional comparator-panel metrics.
- `reports/figures/`: publication-ready charts.
- `reports/summary.md`: automatically generated analytical summary.
- `reports/validation.json`: data-quality and identity checks.
- `reports/reproducibility.json`: build metadata, config hash, Python version,
  package version, and git revision.

## Methodological boundary

The main indicator is general-government interest payable under ESA 2010, Eurostat national-accounts item `D41PAY`, divided by nominal GDP. It is not central-government cash interest, debt redemptions, or the yield on newly issued bonds.

The post-1995 series is kept separate from any linked pre-1995 AMECO extension. Forecast observations are also labelled and excluded from historical estimates unless explicitly requested.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Or use Poetry:

```bash
poetry install --with dev
```

## Run

```bash
pt-debt all --config config/default.yaml
```

Individual stages:

```bash
pt-debt fetch-eurostat
pt-debt fetch-ameco
pt-debt fetch-panel
pt-debt build-panel
pt-debt build
pt-debt validate
pt-debt plot
pt-debt report
```

When `data/processed/eurostat_panel_metrics.csv` exists, `pt-debt plot` and
`pt-debt report` include the European comparison outputs. Scenario-path charts
use the refinancing shares and rate shocks configured in `config/default.yaml`.

The default pipeline writes both CSV and SQLite outputs. Set `storage.backend: csv` or `storage.backend: sqlite` in the configuration to write only one format.

## Offline development

Tests use local JSON-stat and AMECO fixtures. No network access is required:

```bash
pytest
```

## Repository layout

```text
config/       Data sources and analysis settings
data/         Raw, interim, and processed data
notebooks/    Guided exploratory analysis
reports/      Generated figures, tables, and reports
src/          Python package
tests/       Unit and integration tests with fixtures
docs/        Methodology, source registry, and data dictionary
```

## Reproducibility rules

1. Raw downloads are immutable and timestamped.
2. Every processed row records its source, accounting basis, and status.
3. Official and calculated GDP ratios are both retained and reconciled.
4. Forecasts never silently replace observations.
5. Pre-1995 linked data never silently overwrite the ESA 2010 series.
6. Each build records reproducibility metadata and source coverage diagnostics.
