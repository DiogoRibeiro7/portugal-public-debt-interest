# Validation review

## Confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.validation.validate_dataset`
- Reproduction procedure: call `validate_dataset` with a row whose `year` is null while the required `year` column exists.
- Risk: validation can crash during integer conversion instead of returning a structured failed check, making malformed processed datasets harder to diagnose through the CLI.
- Minimal correction: validate that core key values are non-null before duplicate-year, coverage, and identity checks.
- Regression test: `tests/test_validation.py::test_validation_reports_missing_core_values_without_crashing` and `tests/test_validation.py::test_validation_reports_missing_accounting_basis_values`.

## Previous confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.panel.validate_country_year_panel`
- Reproduction procedure: pass a comparator panel row with a missing `geo` or `year` key into `validate_country_year_panel`.
- Risk: rows with incomplete country-year keys can pass validation, then be dropped from grouped metric calculations or produce ambiguous missingness diagnostics.
- Minimal correction: reject null country-year keys before duplicate-key validation and report the affected key records.
- Regression test: `tests/test_panel.py::test_validate_country_year_panel_rejects_missing_keys`.

## Earlier confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.pipeline._fetch_available_panel_series`
- Reproduction procedure: make a mandatory comparator input, such as the interest-to-GDP series, raise `SourceError` while another comparator series succeeds.
- Risk: source acquisition can downgrade a mandatory comparator failure to an all-null missing column, hiding corrupted or unavailable core panel inputs until later stages.
- Minimal correction: preserve missing columns only for explicitly optional comparator series, currently `ten_year_yield_pct`, and raise immediately for mandatory comparator series failures.
- Regression test: `tests/test_pipeline.py::test_fetch_available_panel_series_raises_for_required_missing_series`.

## Earlier confirmed finding

- Severity: low
- File and symbol: `src/pt_debt_interest.panel.add_panel_ranks`
- Reproduction procedure: call `build_panel_metrics` with aggregate rows and inspect the `interest_burden_rank` or `implicit_rate_rank` dtype.
- Risk: rank outputs can be stored as generic object columns, making downstream CSV/SQLite consumers and tests less predictable even though the semantic type is nullable integer rank.
- Minimal correction: initialise rank columns as nullable `Int64` columns before assigning per-year ranks.
- Regression test: `tests/test_panel.py::test_build_panel_metrics_adds_country_ranks`.

## Earlier confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.sources.ameco.AmecoArchiveClient.extract`
- Reproduction procedure: call `extract` with valid selectors but a requested year range outside the selected AMECO row's year columns, such as 1900-1901 against the fixture.
- Risk: a configured AMECO source can be reported as successfully extracted even though no observations survive the requested time window, weakening source coverage diagnostics.
- Minimal correction: raise a `SourceError` when matched AMECO selectors produce no observations after year-range filtering.
- Regression test: `tests/test_ameco.py::test_ameco_archive_extract_rejects_empty_requested_range`.

## Earlier confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.config.HttpSection` and `src/pt_debt_interest.config.AnalysisSection`
- Reproduction procedure: instantiate `HttpSection(max_retries=0)` or `AnalysisSection(identity_tolerance_pp=-0.1)`.
- Risk: zero retries makes source clients skip all attempts and report a low-information `None` failure; negative validation tolerances make ordinary non-null identity differences fail every comparison.
- Minimal correction: require positive HTTP timeout, at least one retry, non-negative retry backoff, and non-negative validation tolerances.
- Regression test: `tests/test_config.py::test_http_config_rejects_invalid_retry_settings` and `tests/test_config.py::test_analysis_config_rejects_negative_tolerances`.

## Earlier confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.config.ProjectSection`
- Reproduction procedure: instantiate project settings with `extended_start_year > main_start_year`, or with `main_start_year > end_year`.
- Risk: source acquisition and linked-series assembly can run with empty, reversed, or misleading time windows even though each individual year value has the right type.
- Minimal correction: validate the project year ordering as `extended_start_year <= main_start_year <= end_year`.
- Regression test: `tests/test_config.py::test_project_config_rejects_extended_start_after_main_start` and `tests/test_config.py::test_project_config_rejects_main_start_after_end`.

## Prior confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.config.Settings`
- Reproduction procedure: load settings where `project.eurostat_geo` is `PT` but one configured Eurostat series has `filters.geo = ES`; separately, set `project.comparison_geographies` to include the same geography twice.
- Risk: the analysis could silently mix a non-Portugal source series into the Portugal dataset, or duplicate comparator panel rows after repeated downloads for the same geography.
- Minimal correction: validate that Eurostat series geography filters match `project.eurostat_geo` and that comparator geography codes are unique.
- Regression test: `tests/test_config.py::test_settings_rejects_eurostat_main_geo_mismatch` and `tests/test_config.py::test_project_config_rejects_duplicate_comparison_geographies`.

## Prior confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.sources.eurostat.EurostatClient.fetch_series`
- Reproduction procedure: return a JSON-stat response whose time category labels contain the same year twice, then call `fetch_series`.
- Risk: duplicate annual labels could enter the source table and later outer joins as ambiguous annual observations, corrupting lagged calculations or causing later failures away from the source boundary.
- Minimal correction: reject duplicate converted `year` values immediately after parsing one Eurostat series.
- Regression test: `tests/test_jsonstat.py::test_eurostat_client_rejects_duplicate_time_labels`.

## Prior confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.validation.validate_dataset`
- Reproduction procedure: call `validate_dataset` with a frame missing `year` or `accounting_basis`.
- Risk: validation could crash with a raw `KeyError` before writing a structured result, making corrupted processed files harder to diagnose through the CLI.
- Minimal correction: add an explicit core-column validation check and return a failed validation payload before running checks that depend on those columns.
- Regression test: `tests/test_validation.py::test_validation_reports_missing_core_columns` and `tests/test_validation.py::test_validation_reports_missing_accounting_basis_without_crashing`.

## Earlier validation finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.plotting`
- Reproduction procedure: run output-generation tests in an environment where Matplotlib defaults to the Tk backend but Tk is unavailable or partially configured.
- Risk: chart generation can fail for environmental GUI reasons even though the project only writes PNG/SVG files, making reporting outputs less reproducible in CI or headless automation.
- Minimal correction: select Matplotlib's noninteractive `Agg` backend before importing `pyplot`.
- Regression test: `tests/test_outputs.py::test_generate_all_plots_uses_latest_panel_year_with_portugal` exercises file-based figure generation under the test runner.

## Earlier validation finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.plotting.plot_european_comparison` and `src/pt_debt_interest.reporting._panel_summary`
- Reproduction procedure: pass a comparator panel where Spain has a valid 2024 row, while Portugal's latest valid row is 2023.
- Risk: the European comparison can be generated for a year without Portugal, losing the highlighted country in the figure, while the report can suppress the comparison despite a valid earlier Portugal comparator year.
- Minimal correction: select the latest comparator year where Portugal has a valid observed non-aggregate interest-burden value, then compare all available non-aggregate rows in that year.
- Regression test: `tests/test_outputs.py::test_generate_all_plots_uses_latest_panel_year_with_portugal` and `tests/test_outputs.py::test_generate_report_uses_latest_panel_year_with_portugal`.

## Earlier comparison finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.plotting.refinancing_shock_paths`
- Reproduction procedure: call `generate_all_plots` with configured shocks and shares when the latest observed row has `debt_pct_gdp` or `interest_pct_gdp` missing.
- Risk: the refinancing figure can be generated from an incomplete baseline, producing `NaN` scenario paths or a blank analytical chart without a clear data-quality signal.
- Minimal correction: build refinancing scenarios only from observed rows with complete baseline interest and debt metrics, and skip the optional scenario output if no such row exists.
- Regression test: `tests/test_outputs.py::test_refinancing_shock_paths_uses_latest_complete_observed_row` and `tests/test_outputs.py::test_refinancing_shock_paths_skips_incomplete_baseline`.

## Earlier output finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.reporting.generate_report`
- Reproduction procedure: call `generate_report` with observed rows where `implicit_interest_rate_pct` is missing, or with that column absent.
- Risk: the generated report could render headline values such as `nan%` or fail with an uninformative column error, making missing mandatory report inputs look like analytical results.
- Minimal correction: require the report input to include all headline columns and at least one observed row with complete headline metrics before rendering.
- Regression test: `tests/test_outputs.py::test_generate_report_rejects_missing_required_columns` and `tests/test_outputs.py::test_generate_report_rejects_incomplete_headline_rows`.

## Earlier reporting finding

- Severity: high
- File and symbol: `src/pt_debt_interest.metrics.calculate_metrics`
- Reproduction procedure: call `calculate_metrics` with two rows for the same `year` and valid interest, GDP, and debt columns.
- Risk: lagged calculations such as nominal GDP growth and implicit interest rates can be computed across two observations for the same calendar year, producing misleading rates before later storage validation has a chance to reject duplicate annual keys.
- Minimal correction: reject duplicate annual years at the start of metric calculation.
- Regression test: `tests/test_metrics.py::test_calculate_metrics_rejects_duplicate_years`.

## Earlier metrics finding

- Severity: high
- File and symbol: `src/pt_debt_interest.jsonstat.jsonstat_to_frame`
- Reproduction procedure: pass a JSON-stat payload whose `size` says a dimension has more categories than `dimension.*.category.index`, or whose sparse `value`/`status` map contains an index outside the declared product of sizes.
- Risk: a malformed or changed API response could be partially parsed or fail later with a generic indexing error, making source-schema corruption harder to distinguish from ordinary missing data.
- Minimal correction: validate category counts against declared dimension sizes and reject sparse `value` or `status` indexes that are non-integer or outside the declared cube.
- Regression test: `tests/test_jsonstat.py::test_jsonstat_to_frame_rejects_dimension_size_mismatch`, `tests/test_jsonstat.py::test_jsonstat_to_frame_rejects_out_of_range_sparse_index`, and `tests/test_jsonstat.py::test_jsonstat_to_frame_rejects_non_integer_sparse_index`.

## Earlier parser finding

- Severity: high
- File and symbol: `src/pt_debt_interest.storage.save_processed`
- Reproduction procedure: call `save_processed` with a frame containing duplicate `year` values while the configured backend includes CSV output.
- Risk: `build_dataset` persists outputs before the CLI validation stage, so duplicate annual keys could be written to `data/processed/portugal_debt_interest.csv` before validation reports the dataset invalid. SQLite would later fail on the unique index, but CSV output could already be stale or corrupted.
- Minimal correction: validate that processed annual outputs include a `year` column and contain no duplicate years before creating output directories or writing any backend.
- Regression test: `tests/test_storage.py::test_save_processed_rejects_duplicate_years_before_writing` and `tests/test_storage.py::test_save_processed_requires_year_column`.

## Earlier config finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.config.AnalysisSection`
- Reproduction procedure: instantiate `AnalysisSection(default_refinancing_shares=[0.6, 0.5])`, or instantiate it with overlapping regime windows such as 2000-2005 and 2005-2010.
- Risk: an invalid refinancing schedule could fail only at plotting time, and overlapping regime boundaries could silently assign a year to whichever label appears first rather than to an unambiguous period.
- Minimal correction: validate that configured refinancing shares sum to no more than one and that regime boundaries have non-reversed, non-overlapping year ranges.
- Regression test: `tests/test_config.py::test_analysis_config_rejects_excess_refinancing_shares`, `tests/test_config.py::test_analysis_config_rejects_overlapping_regimes`, and `tests/test_config.py::test_analysis_config_rejects_reversed_regime`.

## Earlier source finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.sources.ameco.AmecoArchiveClient.extract`
- Reproduction procedure: build an AMECO zip containing the same configured series row twice, either within one CSV member or repeated across two CSV members, then call `extract`.
- Risk: the parser selected the first matching row with `.head(1)` or could merge duplicate output columns from multiple members, making the linked historical extension depend on archive layout instead of an explicit unique selector.
- Minimal correction: reject selectors that match more than one row in a member or more than one archive member.
- Regression test: `tests/test_ameco.py::test_ameco_archive_extract_rejects_duplicate_selector_rows` and `tests/test_ameco.py::test_ameco_archive_extract_rejects_duplicate_selector_members`.

## Earlier provenance finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.pipeline.fetch_eurostat`
- Reproduction procedure: run `pt-debt fetch-eurostat` and inspect `data/interim/eurostat_main.csv`; raw `.manifest.json` files contain retrieval timestamps and checksums, but `retrieval_timestamp_utc` is empty in the joined interim table.
- Risk: processed rows cannot be traced back to the exact retrieval timestamp or raw checksum without manually matching filenames in `data/raw/`, weakening reproducibility and making source revisions harder to audit.
- Minimal correction: propagate per-series raw filename, checksum, and retrieval timestamp from `EurostatClient.fetch_series`, collapse them into row-level provenance fields in the pipeline, and warn when source rows lack retrieval timestamps.
- Regression test: `tests/test_jsonstat.py::test_eurostat_client_returns_raw_provenance`, `tests/test_pipeline.py::test_add_eurostat_row_provenance_collapses_series_metadata`, and `tests/test_validation.py::test_validation_warns_on_missing_retrieval_timestamp`.

## Initial stale-data finding

- Severity: high
- File and symbol: `src/pt_debt_interest.cli.all_command`
- Reproduction procedure: run the full pipeline after a previous successful AMECO fetch, then make the optional AMECO fetch fail while leaving `data/interim/ameco_linked.csv` in place.
- Risk: the build step could consume stale linked AMECO data after the optional source failed, making the processed dataset appear to include a fresh extension.
- Minimal correction: remove stale AMECO interim data when the optional fetch fails, and ignore AMECO interim data when AMECO is disabled.
- Regression test: `tests/test_pipeline.py::test_clear_ameco_interim_removes_stale_file`.

## Review notes

- `pytest`, `ruff check .`, and `mypy src` are expected to pass after the correction.
- A live Eurostat `gov_10a_main` request for Portugal `D41PAY`, `MIO_EUR`, `S13`, year 2023 returned JSON-stat dimensions `freq`, `unit`, `sector`, `na_item`, `geo`, and `time`, with size `[1, 1, 1, 1, 1, 1]` and a dict-valued `value` object. That matches the parser expectation that configured non-time dimensions resolve to a single category.
