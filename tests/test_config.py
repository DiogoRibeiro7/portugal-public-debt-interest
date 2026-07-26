import pytest
from pydantic import ValidationError

from pt_debt_interest.config import AnalysisSection, ProjectSection, Settings, load_settings


def test_analysis_config_rejects_excess_refinancing_shares() -> None:
    with pytest.raises(ValidationError, match="outstanding stock"):
        AnalysisSection(default_refinancing_shares=[0.6, 0.5])


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


def test_settings_rejects_eurostat_main_geo_mismatch() -> None:
    payload = load_settings("config/default.yaml").model_dump()
    payload["eurostat"]["series"]["interest_mio_eur"]["filters"]["geo"] = "ES"

    with pytest.raises(ValidationError, match=r"project\.eurostat_geo"):
        Settings.model_validate(payload)
