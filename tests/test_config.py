import pytest
from pydantic import ValidationError

from pt_debt_interest.config import (
    AnalysisSection,
    HttpSection,
    ProjectSection,
    Settings,
    load_settings,
)


def test_analysis_config_rejects_excess_refinancing_shares() -> None:
    with pytest.raises(ValidationError, match="outstanding stock"):
        AnalysisSection(default_refinancing_shares=[0.6, 0.5])


def test_analysis_config_rejects_negative_tolerances() -> None:
    with pytest.raises(ValidationError, match="tolerances"):
        AnalysisSection(ratio_tolerance_pp=-0.1)

    with pytest.raises(ValidationError, match="tolerances"):
        AnalysisSection(identity_tolerance_pp=-0.1)


def test_analysis_config_rejects_overlapping_regimes() -> None:
    with pytest.raises(ValidationError, match="must not overlap"):
        AnalysisSection(
            regime_boundaries=[
                {"start": 2000, "end": 2005, "label": "First"},
                {"start": 2005, "end": 2010, "label": "Second"},
            ]
        )


def test_analysis_config_rejects_reversed_regime() -> None:
    with pytest.raises(ValidationError, match="start must be before"):
        AnalysisSection(
            regime_boundaries=[
                {"start": 2010, "end": 2009, "label": "Invalid"},
            ]
        )


def test_project_config_rejects_duplicate_comparison_geographies() -> None:
    with pytest.raises(ValidationError, match="comparison geographies"):
        ProjectSection(
            country_name="Portugal",
            eurostat_geo="PT",
            ameco_geo="PRT",
            end_year=2025,
            comparison_geographies=["PT", "ES", "PT"],
        )


def test_project_config_rejects_extended_start_after_main_start() -> None:
    with pytest.raises(ValidationError, match="extended_start_year"):
        ProjectSection(
            country_name="Portugal",
            eurostat_geo="PT",
            ameco_geo="PRT",
            main_start_year=1995,
            extended_start_year=2000,
            end_year=2025,
        )


def test_project_config_rejects_main_start_after_end() -> None:
    with pytest.raises(ValidationError, match="main_start_year"):
        ProjectSection(
            country_name="Portugal",
            eurostat_geo="PT",
            ameco_geo="PRT",
            main_start_year=2026,
            extended_start_year=1960,
            end_year=2025,
        )


def test_http_config_rejects_invalid_retry_settings() -> None:
    with pytest.raises(ValidationError, match="timeout_seconds"):
        HttpSection(timeout_seconds=0)

    with pytest.raises(ValidationError, match="max_retries"):
        HttpSection(max_retries=0)

    with pytest.raises(ValidationError, match="backoff_seconds"):
        HttpSection(backoff_seconds=-1)


def test_settings_rejects_eurostat_main_geo_mismatch() -> None:
    payload = load_settings("config/default.yaml").model_dump()
    payload["eurostat"]["series"]["interest_mio_eur"]["filters"]["geo"] = "ES"

    with pytest.raises(ValidationError, match=r"project\.eurostat_geo"):
        Settings.model_validate(payload)


def test_settings_rejects_duplicate_eurostat_value_names() -> None:
    payload = load_settings("config/default.yaml").model_dump()
    payload["eurostat"]["series"]["interest_pct_gdp_official"][
        "value_name"
    ] = "interest_mio_eur"

    with pytest.raises(ValidationError, match="value_name entries must be unique"):
        Settings.model_validate(payload)


def test_settings_rejects_duplicate_ameco_output_names() -> None:
    payload = load_settings("config/default.yaml").model_dump()
    payload["ameco"]["selectors"]["interest_bn_eur"][
        "output_name"
    ] = "interest_pct_gdp_ameco"

    with pytest.raises(ValidationError, match="output_name entries must be unique"):
        Settings.model_validate(payload)
