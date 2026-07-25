import pandas as pd
import pytest

from pt_debt_interest.config import EurostatSeriesSpec
from pt_debt_interest.exceptions import ValidationError
from pt_debt_interest.panel import (
    geography_metadata,
    panel_missingness,
    series_specs_for_geo,
    validate_country_year_panel,
)


def test_series_specs_for_geo_replaces_only_geography() -> None:
    series = {
        "interest": EurostatSeriesSpec(
            dataset="gov_10a_main",
            filters={"freq": "A", "unit": "PC_GDP", "sector": "S13", "geo": "PT"},
            value_name="interest_pct_gdp",
        )
    }

    result = series_specs_for_geo(series, "ES")

    assert result["interest"].filters["geo"] == "ES"
    assert series["interest"].filters["geo"] == "PT"
    assert result["interest"].filters["sector"] == "S13"


def test_geography_metadata_marks_euro_area_aggregate() -> None:
    metadata = geography_metadata("EA20")

    assert metadata["is_aggregate"] is True
    assert metadata["aggregate_composition"] == "EA20"


def test_validate_country_year_panel_rejects_duplicates() -> None:
    frame = pd.DataFrame({"geo": ["PT", "PT"], "year": [2020, 2020]})

    with pytest.raises(ValidationError, match="duplicate country-year"):
        validate_country_year_panel(frame)


def test_panel_missingness_reports_missing_columns() -> None:
    frame = pd.DataFrame({"geo": ["PT", "PT"], "year": [2020, 2021], "value": [1.0, None]})

    result = panel_missingness(frame, ["value", "missing_value"])

    assert result.loc[result["column"] == "value", "missing_count"].iloc[0] == 1
    assert result.loc[result["column"] == "missing_value", "missing_count"].iloc[0] == 2
