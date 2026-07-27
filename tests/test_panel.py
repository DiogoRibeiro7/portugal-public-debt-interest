import pandas as pd
import pytest

from pt_debt_interest.config import EurostatSeriesSpec
from pt_debt_interest.exceptions import ValidationError
from pt_debt_interest.panel import (
    build_panel_metrics,
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


def test_validate_country_year_panel_rejects_missing_keys() -> None:
    frame = pd.DataFrame({"geo": ["PT", None], "year": [2020, 2021]})

    with pytest.raises(ValidationError, match="missing country-year keys"):
        validate_country_year_panel(frame)


def test_validate_country_year_panel_rejects_blank_geographies() -> None:
    frame = pd.DataFrame({"geo": ["PT", "  "], "year": [2020, 2021]})

    with pytest.raises(ValidationError, match="blank geography keys"):
        validate_country_year_panel(frame)


def test_panel_missingness_reports_missing_columns() -> None:
    frame = pd.DataFrame({"geo": ["PT", "PT"], "year": [2020, 2021], "value": [1.0, None]})

    result = panel_missingness(frame, ["value", "missing_value"])

    assert result.loc[result["column"] == "value", "missing_count"].iloc[0] == 1
    assert result.loc[result["column"] == "missing_value", "missing_count"].iloc[0] == 2


def test_build_panel_metrics_adds_country_ranks() -> None:
    frame = pd.DataFrame(
        {
            "geo": ["PT", "PT", "ES", "ES", "EA20", "EA20"],
            "year": [2021, 2022, 2021, 2022, 2021, 2022],
            "interest_mio_eur": [5.0, 6.0, 4.0, 5.0, 20.0, 21.0],
            "nominal_gdp_mio_eur": [100.0, 120.0, 100.0, 125.0, 500.0, 550.0],
            "debt_mio_eur": [100.0, 110.0, 90.0, 95.0, 400.0, 410.0],
            "source": ["Eurostat"] * 6,
            "accounting_basis": ["ESA2010"] * 6,
            "observation_status": ["observed"] * 6,
            "is_aggregate": [False, False, False, False, True, True],
        }
    )

    result = build_panel_metrics(frame, denominator="average_debt")

    pt_2022 = result.loc[(result["geo"] == "PT") & (result["year"] == 2022)].iloc[0]
    es_2022 = result.loc[(result["geo"] == "ES") & (result["year"] == 2022)].iloc[0]
    ea_2022 = result.loc[(result["geo"] == "EA20") & (result["year"] == 2022)].iloc[0]
    assert pt_2022["interest_burden_rank"] == 1
    assert es_2022["interest_burden_rank"] == 2
    assert pd.isna(ea_2022["interest_burden_rank"])
    assert str(result["interest_burden_rank"].dtype) == "Int64"
    assert str(result["implicit_rate_rank"].dtype) == "Int64"
