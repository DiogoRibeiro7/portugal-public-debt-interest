# Portugal Public-Debt Interest Burden

A reproducible analysis of the interest paid by Portugal's general government, in euros and as a percentage of GDP.

The authoritative series begins in 1995 and uses harmonised ESA 2010 data from Eurostat. An optional AMECO extension can add earlier observations, while preserving an explicit accounting-basis and observed/forecast distinction.

## Description

This project builds a transparent annual dataset for Portugal's public-debt interest burden. It downloads official Eurostat and AMECO data, reconciles interest, government expenditure, government revenue, debt, GDP, and balance ratios, calculates derived metrics, and produces validation checks, charts, and a Markdown report suitable for research or publication workflows.

## Research questions

- How much interest does Portugal's general government pay each year?
- How has the burden changed relative to nominal GDP?
- Was the decline driven by lower effective rates, a lower debt ratio, nominal growth, or inflation?
- How quickly do market-rate changes pass through to the effective cost of the debt stock?
- How does Portugal compare with the euro-area country universe under harmonised Eurostat definitions?

## Main outputs

- `data/processed/portugal_debt_interest.csv`: annual analytical dataset.
- `data/processed/portugal_debt_interest.sqlite`: optional SQL copy.
- `data/processed/eurostat_panel_metrics.csv`: optional comparator-panel metrics.
- `reports/figures/`: publication-ready charts as PNG, SVG, and PDF files.
- `reports/tables/`: generated LaTeX table fragments used by the paper.
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
pt-debt tables
```

When `data/processed/eurostat_panel_metrics.csv` exists, `pt-debt plot` and
`pt-debt report` include the European comparison outputs. Scenario-path charts
use the refinancing shares and rate shocks configured in `config/default.yaml`.

The default pipeline writes both CSV and SQLite outputs. Set `storage.backend: csv` or `storage.backend: sqlite` in the configuration to write only one format.

## Notebooks

`notebooks/` holds the guided analysis. Each notebook is a reader: it consumes
the artefacts written by `pt-debt all` and never fetches from the network or
writes to `data/`. They are committed **with their outputs**, so the figures and
tables are readable on GitHub even though `data/processed/` and
`reports/figures/` are git-ignored.

| Notebook | Question it answers |
| --- | --- |
| `01_portugal_debt_interest.ipynb` | How large is the interest bill, why did the euro amount and the GDP ratio move in opposite directions, and how much of total public spending does it absorb? |
| `02_data_quality_and_provenance.ipynb` | What is in the dataset, where did each value come from, and where do the official and calculated figures disagree? |
| `03_debt_dynamics_and_decomposition.ipynb` | Was the change in the burden the price of the debt or its quantity, and what moved the debt ratio? |
| `04_rate_pass_through_and_scenarios.ipynb` | How fast do market yields reach the effective cost of the stock, and what would a rate shock do? |
| `05_european_comparison.ipynb` | Where does Portugal sit in the euro-area distribution, and is that about price or quantity? |

The notebooks reuse `pt_debt_interest` rather than reimplementing its formulas.
Notebook 03 recomputes the burden decomposition from the library and asserts
that both accounting identities close before interpreting them, so a change in
the library surfaces as a failing cell rather than a stale chart.

`notebooks/nbtools.py` is shared infrastructure, not analysis: artefact loading,
the harmonised-sample filter, and one chart style. It also puts `src/` on the
path, so the notebooks run from a plain checkout without an editable install.

To re-execute them after refreshing the data:

```bash
pt-debt all --config config/default.yaml
cd notebooks
jupyter nbconvert --to notebook --execute --inplace *.ipynb
```

## Offline development

Tests use local JSON-stat and AMECO fixtures. No network access is required:

```bash
pytest
```

## Citation

Citation metadata is provided in `CITATION.cff` for GitHub and reference-manager
workflows.

## Repository layout

```text
config/       Data sources and analysis settings
data/         Raw, interim, and processed data
notebooks/    Guided analysis, committed with executed outputs
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

Dependency-resolution and live-data regeneration details are documented in
`docs/reproducibility.md`.
