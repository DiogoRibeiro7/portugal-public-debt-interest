# Validation review

## Confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.sources.ameco.AmecoArchiveClient.extract`
- Reproduction procedure: build an AMECO zip containing the same configured series row twice, either within one CSV member or repeated across two CSV members, then call `extract`.
- Risk: the parser selected the first matching row with `.head(1)` or could merge duplicate output columns from multiple members, making the linked historical extension depend on archive layout instead of an explicit unique selector.
- Minimal correction: reject selectors that match more than one row in a member or more than one archive member.
- Regression test: `tests/test_ameco.py::test_ameco_archive_extract_rejects_duplicate_selector_rows` and `tests/test_ameco.py::test_ameco_archive_extract_rejects_duplicate_selector_members`.

## Previous confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.pipeline.fetch_eurostat`
- Reproduction procedure: run `pt-debt fetch-eurostat` and inspect `data/interim/eurostat_main.csv`; raw `.manifest.json` files contain retrieval timestamps and checksums, but `retrieval_timestamp_utc` is empty in the joined interim table.
- Risk: processed rows cannot be traced back to the exact retrieval timestamp or raw checksum without manually matching filenames in `data/raw/`, weakening reproducibility and making source revisions harder to audit.
- Minimal correction: propagate per-series raw filename, checksum, and retrieval timestamp from `EurostatClient.fetch_series`, collapse them into row-level provenance fields in the pipeline, and warn when source rows lack retrieval timestamps.
- Regression test: `tests/test_jsonstat.py::test_eurostat_client_returns_raw_provenance`, `tests/test_pipeline.py::test_add_eurostat_row_provenance_collapses_series_metadata`, and `tests/test_validation.py::test_validation_warns_on_missing_retrieval_timestamp`.

## Earlier confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.cli.all_command`
- Reproduction procedure: run the full pipeline after a previous successful AMECO fetch, then make the optional AMECO fetch fail while leaving `data/interim/ameco_linked.csv` in place.
- Risk: the build step could consume stale linked AMECO data after the optional source failed, making the processed dataset appear to include a fresh extension.
- Minimal correction: remove stale AMECO interim data when the optional fetch fails, and ignore AMECO interim data when AMECO is disabled.
- Regression test: `tests/test_pipeline.py::test_clear_ameco_interim_removes_stale_file`.

## Review notes

- `pytest`, `ruff check .`, and `mypy src` are expected to pass after the correction.
- A live Eurostat `gov_10a_main` request for Portugal `D41PAY`, `MIO_EUR`, `S13`, year 2023 returned JSON-stat dimensions `freq`, `unit`, `sector`, `na_item`, `geo`, and `time`, with size `[1, 1, 1, 1, 1, 1]` and a dict-valued `value` object. That matches the parser expectation that configured non-time dimensions resolve to a single category.
