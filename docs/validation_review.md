# Validation review

## Confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.reporting.generate_report`
- Reproduction procedure: call `generate_report` with observed rows where `implicit_interest_rate_pct` is missing, or with that column absent.
- Risk: the generated report could render headline values such as `nan%` or fail with an uninformative column error, making missing mandatory report inputs look like analytical results.
- Minimal correction: require the report input to include all headline columns and at least one observed row with complete headline metrics before rendering.
- Regression test: `tests/test_outputs.py::test_generate_report_rejects_missing_required_columns` and `tests/test_outputs.py::test_generate_report_rejects_incomplete_headline_rows`.

## Previous confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.metrics.calculate_metrics`
- Reproduction procedure: call `calculate_metrics` with two rows for the same `year` and valid interest, GDP, and debt columns.
- Risk: lagged calculations such as nominal GDP growth and implicit interest rates can be computed across two observations for the same calendar year, producing misleading rates before later storage validation has a chance to reject duplicate annual keys.
- Minimal correction: reject duplicate annual years at the start of metric calculation.
- Regression test: `tests/test_metrics.py::test_calculate_metrics_rejects_duplicate_years`.

## Earlier confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.jsonstat.jsonstat_to_frame`
- Reproduction procedure: pass a JSON-stat payload whose `size` says a dimension has more categories than `dimension.*.category.index`, or whose sparse `value`/`status` map contains an index outside the declared product of sizes.
- Risk: a malformed or changed API response could be partially parsed or fail later with a generic indexing error, making source-schema corruption harder to distinguish from ordinary missing data.
- Minimal correction: validate category counts against declared dimension sizes and reject sparse `value` or `status` indexes that are non-integer or outside the declared cube.
- Regression test: `tests/test_jsonstat.py::test_jsonstat_to_frame_rejects_dimension_size_mismatch`, `tests/test_jsonstat.py::test_jsonstat_to_frame_rejects_out_of_range_sparse_index`, and `tests/test_jsonstat.py::test_jsonstat_to_frame_rejects_non_integer_sparse_index`.

## Prior confirmed finding

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
