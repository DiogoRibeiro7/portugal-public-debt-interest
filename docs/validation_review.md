# Validation review

## Confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.storage.load_processed`
- Reproduction procedure: load an existing processed CSV or SQLite table whose `year` column is missing, malformed, or duplicated.
- Risk: corrupted persisted analytical datasets can be loaded and passed into reporting or plotting despite violating the annual-key contract enforced during save.
- Minimal correction: run the same annual-key validation after loading processed CSV or SQLite data.
- Regression test: `tests/test_storage.py::test_load_processed_rejects_duplicate_csv_years` and `tests/test_storage.py::test_load_processed_rejects_missing_sqlite_years`.

## Previous confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.panel.aggregate_flag_mask`, `src/pt_debt_interest.reporting._panel_summary`, and `src/pt_debt_interest.plotting.plot_european_comparison`
- Reproduction procedure: load comparator-panel rows from CSV where `is_aggregate` contains strings such as `"False"` and `"True"`.
- Risk: string `"False"` values are truthy under direct boolean casting, causing non-aggregate countries to be excluded from ranks, plots, and report summaries.
- Minimal correction: normalize aggregate flags from boolean-like strings and numeric flags before filtering comparator rows.
- Regression test: `tests/test_panel.py::test_build_panel_metrics_parses_string_aggregate_flags`, `tests/test_outputs.py::test_generate_report_parses_string_aggregate_flags`, and `tests/test_outputs.py::test_generate_all_plots_parses_string_aggregate_flags`.

## Earlier confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.reporting._observed_headline_rows`
- Reproduction procedure: call `generate_report` with non-numeric or infinite headline metrics such as `interest_pct_gdp` or `debt_pct_gdp`.
- Risk: report generation can fail during template preparation with low-level float conversion errors, or render invalid headline values.
- Minimal correction: validate observed headline rows as finite numeric values before selecting the latest and peak observations.
- Regression test: `tests/test_outputs.py::test_generate_report_rejects_non_numeric_headline_values` and `tests/test_outputs.py::test_generate_report_rejects_non_finite_headline_values`.

## Earlier confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.scenarios`
- Reproduction procedure: call static or refinancing scenario helpers with a non-finite or fractional `shock_bps` value.
- Risk: malformed shock values can produce invalid scenario arithmetic or ambiguous basis-point labels while bypassing direct-call validation.
- Minimal correction: require shock values to be numeric finite whole numbers before scenario calculations.
- Regression test: `tests/test_scenarios.py::test_static_rate_shock_table_rejects_non_finite_shock`, `tests/test_scenarios.py::test_static_rate_shock_table_rejects_fractional_shock`, `tests/test_scenarios.py::test_refinancing_pass_through_rejects_non_finite_shock`, and `tests/test_scenarios.py::test_refinancing_path_rejects_fractional_shock`.

## Previous confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.metrics.calculate_metrics`
- Reproduction procedure: call `calculate_metrics` with malformed optional percentage columns such as non-numeric `interest_pct_gdp_official` or infinite `overall_balance_pct_gdp`.
- Risk: optional percentage values can bypass validation and fail later during fill or arithmetic operations, producing unclear type errors or invalid derived fiscal balances.
- Minimal correction: require present optional percentage inputs to be numeric and finite before metric calculation.
- Regression test: `tests/test_metrics.py::test_calculate_metrics_rejects_non_numeric_official_interest_ratio` and `tests/test_metrics.py::test_calculate_metrics_rejects_non_finite_overall_balance`.

## Earlier confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.metrics._validate_growth_factors`
- Reproduction procedure: call `calculate_metrics` with `real_gdp_growth_pct` set to a non-numeric or infinite value.
- Risk: malformed optional real-growth inputs can be coerced into missing or invalid derived GDP-deflator values without a clear validation failure.
- Minimal correction: require present real-growth values to be numeric, finite, and greater than `-100`.
- Regression test: `tests/test_metrics.py::test_calculate_metrics_rejects_non_numeric_real_growth` and `tests/test_metrics.py::test_calculate_metrics_rejects_non_finite_real_growth`.

## Previous confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.metrics.assign_regime`
- Reproduction procedure: call `calculate_metrics` directly with `regime_boundaries` containing malformed boundary years, such as `{"start": 2020.5, "end": 2022}`.
- Risk: regime assignment can truncate malformed boundary years or raise low-level conversion errors outside the configuration-loading path.
- Minimal correction: validate direct-call regime boundary years as finite whole numbers before assigning labels.
- Regression test: `tests/test_metrics.py::test_calculate_metrics_rejects_fractional_regime_boundary_years` and `tests/test_metrics.py::test_calculate_metrics_rejects_non_numeric_regime_boundary_years`.

## Previous confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.config.HttpSection`, `src/pt_debt_interest.config.AnalysisSection`, and `src/pt_debt_interest.metrics.assign_regime`
- Reproduction procedure: construct settings with `NaN` or infinite HTTP timeout/backoff values, validation tolerances, or default refinancing shares; or calculate metrics with non-numeric or fractional regime boundary years.
- Risk: non-finite configuration values can pass load-time validation, while malformed regime boundaries can fail late or be truncated during annual regime assignment.
- Minimal correction: require finite numeric configuration values and parse regime boundary years as whole numbers before assigning regimes.
- Regression test: `tests/test_config.py::test_http_config_rejects_non_finite_retry_settings`, `tests/test_config.py::test_analysis_config_rejects_non_finite_tolerances`, `tests/test_config.py::test_analysis_config_rejects_non_finite_refinancing_shares`, `tests/test_metrics.py::test_calculate_metrics_rejects_fractional_regime_boundary_years`, and `tests/test_metrics.py::test_calculate_metrics_rejects_non_numeric_regime_boundary_years`.

## Previous confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.jsonstat._ordered_categories`
- Reproduction procedure: parse a JSON-stat payload whose category index contains duplicate labels, for example time labels `["2021", "2021", "2022"]`.
- Risk: duplicate category labels can produce ambiguous tidy rows even when declared dimension sizes and ordinal positions are valid.
- Minimal correction: reject duplicate category labels after ordering list-style or dict-style category indexes.
- Regression test: `tests/test_jsonstat.py::test_jsonstat_to_frame_rejects_duplicate_list_category_labels` and `tests/test_jsonstat.py::test_jsonstat_to_frame_rejects_duplicate_dict_category_labels`.

## Earlier confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.sources.eurostat._validate_requested_dimensions`
- Reproduction procedure: return a Eurostat JSON-stat response whose requested dimension, such as `geo`, has a fractional or non-finite `size` value while its category list still contains the requested value.
- Risk: malformed response metadata can pass requested-dimension validation, be cached to raw files, and fail only later in generic JSON-stat parsing.
- Minimal correction: validate requested-dimension sizes as non-negative finite whole numbers before accepting the source response.
- Regression test: `tests/test_jsonstat.py::test_eurostat_client_rejects_fractional_requested_dimension_size` and `tests/test_jsonstat.py::test_eurostat_client_rejects_non_finite_requested_dimension_size`.

## Previous confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.jsonstat.jsonstat_to_frame`
- Reproduction procedure: parse a JSON-stat payload whose `size` entry is fractional or negative, such as `3.5`.
- Risk: declared dimension sizes can be truncated or passed into coordinate calculations before validation, making malformed JSON-stat shapes harder to diagnose.
- Minimal correction: validate dimension sizes as non-negative finite whole numbers before category ordering and sparse-value coordinate mapping.
- Regression test: `tests/test_jsonstat.py::test_jsonstat_to_frame_rejects_fractional_dimension_size` and `tests/test_jsonstat.py::test_jsonstat_to_frame_rejects_negative_dimension_size`.

## Previous confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.jsonstat._ordered_categories` and `src/pt_debt_interest.jsonstat._indexed_values`
- Reproduction procedure: parse a JSON-stat payload whose category positions or sparse observation indexes are numeric fractional values such as `1.5`.
- Risk: parser index conversion can truncate fractional JSON numbers, mapping observations or categories to the wrong dimension positions.
- Minimal correction: validate JSON-stat indexes as finite whole numbers before converting them to integers.
- Regression test: `tests/test_jsonstat.py::test_jsonstat_to_frame_rejects_fractional_category_position` and `tests/test_jsonstat.py::test_jsonstat_to_frame_rejects_fractional_sparse_index`.

## Previous confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.sources.ameco.AmecoArchiveClient._parse_code`
- Reproduction procedure: parse an AMECO series code with an unexpected extra dotted segment, such as `PRT.1.0.319.5.0.UYIG`, while configured selectors match by positional unit and variable codes.
- Risk: malformed AMECO codes can shift the parsed unit position and allow the wrong source row to be extracted as a valid linked series.
- Minimal correction: require the expected six-part AMECO code shape and finite whole-number unit codes before selector matching.
- Regression test: `tests/test_ameco.py::test_ameco_archive_extract_rejects_non_finite_unit_code`, `tests/test_ameco.py::test_ameco_code_parser_rejects_non_finite_unit_code`, and `tests/test_ameco.py::test_ameco_code_parser_rejects_extra_segments`.

## Previous confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.sources.eurostat.EurostatClient.fetch_series`, `src/pt_debt_interest.reporting._panel_summary`, and `src/pt_debt_interest.plotting.plot_european_comparison`
- Reproduction procedure: ingest a Eurostat response with fractional time labels, or generate optional comparator outputs with Portugal panel rows whose `year` value is fractional or non-finite.
- Risk: annual source labels and comparator output years can be silently truncated in chart/report labels or crash on non-finite year conversion.
- Minimal correction: reject non-annual Eurostat time labels and keep only finite whole-number comparator years before selecting Portugal's latest panel year.
- Regression test: `tests/test_jsonstat.py::test_eurostat_client_rejects_fractional_time_labels`, `tests/test_outputs.py::test_generate_report_skips_fractional_panel_year`, and `tests/test_outputs.py::test_generate_all_plots_skips_fractional_panel_year`.

## Earlier confirmed finding

- Severity: medium
- File and symbol: annual-key validation in `src/pt_debt_interest.metrics`, `src/pt_debt_interest.pipeline`, `src/pt_debt_interest.storage`, `src/pt_debt_interest.validation`, and `src/pt_debt_interest.panel`
- Reproduction procedure: pass fractional years, non-finite years, or equivalent duplicate years such as `2020` and `"2020"` through analytical, persistence, or comparator-panel validation paths.
- Risk: fractional annual keys can be silently truncated to integers or equivalent annual keys can bypass duplicate checks, creating ambiguous year-level outputs.
- Minimal correction: validate annual keys as finite numeric whole numbers before integer conversion, and run duplicate detection on normalized year keys where applicable.
- Regression test: `tests/test_metrics.py::test_calculate_metrics_rejects_fractional_years`, `tests/test_pipeline.py::test_canonical_table_rejects_fractional_year_values`, `tests/test_storage.py::test_save_processed_rejects_fractional_years_before_writing`, `tests/test_validation.py::test_validation_reports_fractional_year_values`, `tests/test_validation.py::test_validation_reports_missing_core_values_with_malformed_year`, and `tests/test_panel.py::test_validate_country_year_panel_rejects_equivalent_duplicate_years`.

## Earlier confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.storage._validate_annual_keys`
- Reproduction procedure: call `save_processed` with a processed frame whose `year` column contains a non-numeric value.
- Risk: persistence can raise a low-level conversion error while checking annual keys instead of rejecting malformed output with the project validation exception before any files are written.
- Minimal correction: coerce persisted annual keys to numeric values before duplicate detection and raise `ValidationError` for malformed years.
- Regression test: `tests/test_storage.py::test_save_processed_rejects_non_numeric_years_before_writing`.

## Earlier confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.panel.validate_country_year_panel`
- Reproduction procedure: pass a comparator panel row whose `geo` key is an empty or whitespace-only string.
- Risk: blank geography identifiers pass key validation and can then appear as legitimate rows in missingness summaries and rank calculations.
- Minimal correction: reject blank geography keys before duplicate detection.
- Regression test: `tests/test_panel.py::test_validate_country_year_panel_rejects_blank_geographies`.

## Earlier confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.reporting._panel_summary` and `src/pt_debt_interest.plotting.plot_european_comparison`
- Reproduction procedure: generate outputs with comparator-panel rows whose `year` value is non-numeric.
- Risk: optional European-comparison output can crash report or plot generation instead of being skipped as unavailable panel context.
- Minimal correction: coerce comparator-panel years to numeric values and drop malformed rows before selecting Portugal's latest comparator year.
- Regression test: `tests/test_outputs.py::test_generate_report_skips_malformed_panel_year` and `tests/test_outputs.py::test_generate_all_plots_skips_malformed_panel_year`.

## Earlier confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.validation.validate_dataset`
- Reproduction procedure: call `validate_dataset` with a non-numeric `year` value while the `year` column is present.
- Risk: validation can crash during later integer conversions instead of returning a structured failed check for malformed annual keys.
- Minimal correction: validate and normalize numeric annual keys before duplicate, coverage, and accounting-basis checks.
- Regression test: `tests/test_validation.py::test_validation_reports_non_numeric_year_values_without_crashing`.

## Earlier confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.config.AmecoSection`
- Reproduction procedure: configure two AMECO selectors with the same `output_name`, then load settings before extraction.
- Risk: duplicate linked-source output columns are only rejected at extraction time, after source work has already started.
- Minimal correction: reject duplicate AMECO `output_name` entries during configuration validation.
- Regression test: `tests/test_config.py::test_settings_rejects_duplicate_ameco_output_names`.

## Earlier confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.metrics.calculate_metrics`
- Reproduction procedure: call `calculate_metrics` with non-numeric or infinite values in `nominal_gdp_mio_eur` or `debt_mio_eur`.
- Risk: malformed denominators can produce calculation errors, infinite values, or misleading fiscal ratios instead of failing clearly at the metric boundary.
- Minimal correction: require present denominator values to be numeric, finite, and positive before any ratio or lagged-rate calculations.
- Regression test: `tests/test_metrics.py::test_calculate_metrics_rejects_non_numeric_gdp` and `tests/test_metrics.py::test_calculate_metrics_rejects_non_finite_debt`.

## Earlier confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.jsonstat.jsonstat_to_frame`
- Reproduction procedure: parse a JSON-stat response whose dict-style category indexes contain duplicate or out-of-range ordinal positions.
- Risk: flat observation values can be mapped to the wrong category labels, corrupting annual source rows before downstream duplicate-year checks run.
- Minimal correction: validate dict category index positions are integer, unique, and within the declared dimension size before ordering categories.
- Regression test: `tests/test_jsonstat.py::test_jsonstat_to_frame_rejects_duplicate_category_positions` and `tests/test_jsonstat.py::test_jsonstat_to_frame_rejects_out_of_range_category_position`.

## Earlier confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.sources.ameco.AmecoArchiveClient.extract`
- Reproduction procedure: use an AMECO archive where a configured selector row is present, but all requested-year cells for that selector are blank.
- Risk: source extraction can report success for a configured selector that contributed no numeric observations in the analysis window.
- Minimal correction: after requested-year filtering, reject selector outputs whose values are all missing.
- Regression test: `tests/test_ameco.py::test_ameco_archive_extract_rejects_selector_with_only_missing_values`.

## Earlier confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.scenarios`
- Reproduction procedure: call scenario helpers with `NaN` debt, refinancing shares, or nominal GDP path values.
- Risk: non-finite inputs bypass ordinary range checks and produce `NaN` scenario outputs that look like calculated results.
- Minimal correction: require finite numeric debt, refinancing-share, and nominal-GDP-path values before calculating scenario paths.
- Regression test: `tests/test_scenarios.py::test_static_rate_shock_table_rejects_non_finite_debt`, `tests/test_scenarios.py::test_refinancing_pass_through_rejects_non_finite_shares`, and `tests/test_scenarios.py::test_refinancing_path_rejects_non_finite_gdp_path`.

## Earlier confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.metrics.calculate_metrics`
- Reproduction procedure: call `calculate_metrics` directly with a missing or non-numeric `year` value.
- Risk: lagged metric calculation can sort or cast malformed annual keys later, producing low-quality errors or ambiguous annual outputs.
- Minimal correction: require non-missing, numeric annual keys before duplicate-year validation and metric calculation.
- Regression test: `tests/test_metrics.py::test_calculate_metrics_rejects_missing_years` and `tests/test_metrics.py::test_calculate_metrics_rejects_non_numeric_years`.

## Earlier confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.validation.validate_dataset`
- Reproduction procedure: call `validate_dataset` with two rows for the same `year`.
- Risk: duplicate-year diagnostics only report later duplicate rows, obscuring the full set of annual records involved in the key collision.
- Minimal correction: use `duplicated(keep=False)` when collecting affected duplicate years.
- Regression test: `tests/test_validation.py::test_validation_reports_all_duplicate_year_rows`.

## Earlier confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.pipeline._canonicalise_annual_table`
- Reproduction procedure: pass a combined annual table with a missing or non-numeric `year` value into `_canonicalise_annual_table`.
- Risk: canonicalization can crash with a raw conversion error before source-boundary validation, making malformed interim data harder to diagnose.
- Minimal correction: require present, non-missing, numeric annual keys before sorting and basis-boundary marking.
- Regression test: `tests/test_pipeline.py::test_canonical_table_rejects_missing_year_values` and `tests/test_pipeline.py::test_canonical_table_rejects_non_numeric_year_values`.

## Earlier confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.pipeline._build_ameco_pre1995`
- Reproduction procedure: pass linked AMECO extension data where `debt_pct_gdp_ameco` is zero while nominal GDP can be derived.
- Risk: the linked-series mapper can derive zero or negative debt stocks from invalid AMECO debt ratios, pushing a source-data error into later metric validation.
- Minimal correction: reject non-positive AMECO debt-to-GDP ratios before deriving debt stock.
- Regression test: `tests/test_pipeline.py::test_build_ameco_pre1995_rejects_non_positive_debt_ratio`.

## Earlier confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.pipeline._build_ameco_pre1995`
- Reproduction procedure: pass linked AMECO extension data where `interest_pct_gdp_ameco` is zero while interest amounts are present.
- Risk: the linked-series mapper can derive infinite nominal GDP values before later numeric masking, making an invalid AMECO denominator look like missing analytical output.
- Minimal correction: reject non-positive AMECO interest-to-GDP ratios before deriving nominal GDP from interest amounts.
- Regression test: `tests/test_pipeline.py::test_build_ameco_pre1995_rejects_non_positive_interest_ratio`.

## Earlier confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.sources.eurostat._validate_requested_dimensions`
- Reproduction procedure: return a Eurostat JSON-stat response whose `id` and `size` arrays have different lengths.
- Risk: source validation can raise a raw `ValueError` before the client reports a structured `SourceError`, making API schema changes harder to diagnose.
- Minimal correction: explicitly reject Eurostat `id`/`size` length mismatches before building the dimension-size mapping.
- Regression test: `tests/test_jsonstat.py::test_eurostat_client_rejects_id_size_mismatch`.

## Earlier confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.config.EurostatSection`
- Reproduction procedure: configure two Eurostat series with the same `value_name`, then load settings before fetching.
- Risk: source joins can produce suffixed or ambiguous output columns, causing required analytical inputs to disappear or point to the wrong source series.
- Minimal correction: reject duplicate Eurostat `value_name` entries during configuration validation.
- Regression test: `tests/test_config.py::test_settings_rejects_duplicate_eurostat_value_names`.

## Earlier confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.storage.save_processed`
- Reproduction procedure: call `save_processed` with a processed frame containing a null `year` value.
- Risk: processed outputs can persist rows without annual keys; SQLite unique indexes do not reject null keys, so downstream annual reads can become ambiguous.
- Minimal correction: reject missing `year` values before writing CSV or SQLite outputs.
- Regression test: `tests/test_storage.py::test_save_processed_rejects_missing_years_before_writing`.

## Earlier confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.metrics.calculate_metrics`
- Reproduction procedure: call `calculate_metrics` with `real_gdp_growth_pct` equal to `-100` while nominal GDP growth is present.
- Risk: GDP-deflator growth can be calculated by dividing through a zero or negative real-GDP factor, yielding infinite or undefined values that are later masked.
- Minimal correction: reject real GDP growth values less than or equal to `-100%` before factor-based GDP-deflator calculations.
- Regression test: `tests/test_metrics.py::test_calculate_metrics_rejects_invalid_real_growth_factor`.

## Earlier confirmed finding

- Severity: medium
- File and symbol: `src/pt_debt_interest.scenarios`
- Reproduction procedure: call `static_rate_shock_table`, `refinancing_pass_through`, or `refinancing_path_from_gdp` with a zero or negative debt stock.
- Risk: interest-burden scenario outputs can silently report zero or inverted effects from invalid debt inputs, making a source-data error look like an analytical result.
- Minimal correction: reject non-positive debt stocks before calculating static or refinancing shock effects.
- Regression test: `tests/test_scenarios.py::test_static_rate_shock_table_rejects_non_positive_debt`, `tests/test_scenarios.py::test_refinancing_pass_through_rejects_non_positive_debt`, and `tests/test_scenarios.py::test_refinancing_path_rejects_non_positive_debt_stock`.

## Earlier confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.metrics.calculate_metrics`
- Reproduction procedure: call `calculate_metrics` with `nominal_gdp_mio_eur` equal to zero or `debt_mio_eur` less than or equal to zero.
- Risk: divisions by invalid denominators can produce infinite or undefined fiscal ratios that are masked to missing values later, obscuring a source-data integrity error.
- Minimal correction: reject non-positive GDP and debt denominator values before calculating ratios and lagged interest rates.
- Regression test: `tests/test_metrics.py::test_calculate_metrics_rejects_non_positive_gdp` and `tests/test_metrics.py::test_calculate_metrics_rejects_non_positive_debt`.

## Earlier confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.validation.validate_dataset`
- Reproduction procedure: call `validate_dataset` with a row whose `year` is null while the required `year` column exists.
- Risk: validation can crash during integer conversion instead of returning a structured failed check, making malformed processed datasets harder to diagnose through the CLI.
- Minimal correction: validate that core key values are non-null before duplicate-year, coverage, and identity checks.
- Regression test: `tests/test_validation.py::test_validation_reports_missing_core_values_without_crashing` and `tests/test_validation.py::test_validation_reports_missing_accounting_basis_values`.

## Earlier confirmed finding

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
- Reproduction procedure: call `build_panel_metrics` with aggregate rows and inspect the `interest_burden_rank` or `average_debt_rate_rank` dtype.
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
- Reproduction procedure: call `generate_report` with observed rows where `implicit_interest_rate_average_debt_pct` is missing, or with that column absent.
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
- Minimal correction: validate that stylised refinancing scenario shares sum to no more than one and that regime boundaries have non-reversed, non-overlapping year ranges.
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
