# Source registry

## Eurostat

### Government revenue, expenditure and main aggregates

- Dataset: `gov_10a_main`
- Sector: `S13`
- Interest: `D41PAY`
- Fiscal balance: `B9`
- Units: `MIO_EUR`, `PC_GDP`

### Government deficit, debt and associated data

- Dataset: `gov_10dd_edpt1`
- Sector: `S13`
- Gross debt: `GD`
- Units: `MIO_EUR`, `PC_GDP`

### GDP and main components

- Dataset: `nama_10_gdp`
- GDP: `B1GQ`
- Current prices: `CP_MEUR`
- Real annual growth: `CLV_PCH_PRE`

### Long-term interest rate

- Dataset: `irt_lt_mcby_a`
- Indicator: `MCBY`

## European comparison panel

The comparator panel uses the same Eurostat datasets, items, units, sector filters, and time ranges as the Portugal series. Geography codes are configured in `project.comparison_geographies`. The default comparison universe is the complete euro-area country membership in the configured sample endpoint, plus `EA20` and `EU27_2020` aggregates for context. Aggregate rows remain labelled as aggregates and should not be counted as countries in cross-sectional statistics unless explicitly requested.

The `build-panel` command calculates the same fiscal metrics by geography, writes `data/processed/eurostat_panel_metrics.csv`, and records source coverage in `reports/eurostat_panel_missingness.csv`. Optional missing comparator series, such as unavailable aggregate bond-yield rows, are retained as nulls with a missing-reason column.

When panel metrics exist, the plotting and reporting stages add `08_european_comparison.{png,svg}`. The figure uses observed non-aggregate comparator rows for the latest available year and keeps euro-area aggregates out of the country ranking.

The plotting stage also writes `09_refinancing_shock_paths.{png,svg}` and `reports/refinancing_scenarios.csv` from the configured refinancing shares and rate shocks. These paths are deterministic arithmetic simulations from the processed Portugal dataset, not source observations.

## AMECO

- Current all-CSV archive: `ameco0_csv.zip`
- Interest, general government: `UYIG`
- General-government consolidated gross debt: `UDGG`
- Net lending/borrowing: `UBLG`
- AMECO implicit interest rate: `AYIGD`
- Unit code `319`: percentage of current-price GDP under EDP conventions
- Unit code `99`: billion ECU/euro

AMECO includes observations and European Commission forecasts. It can link ESA 2010, ESA 95, and ESA 79 portions. It is therefore used for historical context, not as a silent replacement for Eurostat.

## Raw cache and manifests

Each live source download is preserved in `data/raw/` with a UTC timestamp in the filename. A neighbouring `.manifest.json` file records the request URL, retrieval time, HTTP status, payload size, checksum, and source-specific selection metadata where available. These manifests are intended to make parser inputs auditable without editing raw files.

Eurostat interim rows retain per-series raw filenames, retrieval timestamps, and SHA-256 checksums. The processed annual table also carries row-level joined `source_database`, `source_table_or_series`, `source_vintage`, `retrieval_timestamp_utc`, and `source_checksum_sha256` fields so source revisions can be audited from the analytical output.

The build stage also writes `reports/source_coverage.csv`, which summarises the available year span, row count, and complete-core-observation count by source, database, accounting basis, observation status, and sample flag.
