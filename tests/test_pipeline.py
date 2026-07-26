import warnings
from pathlib import Path

import pandas as pd

from pt_debt_interest.config import EurostatSeriesSpec, load_settings
from pt_debt_interest.exceptions import SourceError
from pt_debt_interest.pipeline import (
    _canonicalise_annual_table,
    _concat_preserving_columns,
    _fetch_available_panel_series,
    clear_ameco_interim,
)


def test_canonical_table_adds_provenance_and_basis_break() -> None:
    frame = pd.DataFrame(
        {
            "year": [1994, 1995],
            "source": ["AMECO", "Eurostat"],
            "accounting_basis": ["linked_ESA2010_ESA95_ESA79", "ESA2010"],
            "observation_status": ["observed", "observed"],
        }
    )

    result = _canonicalise_annual_table(frame, 1995)

    assert "source_vintage" in result.columns
    assert "retrieval_timestamp_utc" in result.columns
    assert bool(result.loc[result["year"] == 1995, "basis_break"].iloc[0]) is True
    assert result["year"].tolist() == [1994, 1995]


def test_clear_ameco_interim_removes_stale_file(tmp_path: Path) -> None:
    settings = load_settings("config/default.yaml")
    interim_dir = tmp_path / settings.paths.interim
    interim_dir.mkdir(parents=True)
    stale = interim_dir / "ameco_linked.csv"
    stale.write_text("year,value\n1994,1\n", encoding="utf-8")

    removed = clear_ameco_interim(settings, tmp_path)

    assert removed == stale
    assert not stale.exists()


def test_fetch_available_panel_series_preserves_missing_series() -> None:
    class FakeClient:
        def fetch_series(
            self,
            name: str,
            spec: EurostatSeriesSpec,
            start_year: int,
            end_year: int,
        ) -> pd.DataFrame:
            if name == "yield":
                raise SourceError("Eurostat irt_lt_mcby_a returned geo=[]; expected EA20")
            return pd.DataFrame({"year": [2024], spec.value_name: [1.5]})

    series = {
        "interest": EurostatSeriesSpec(
            dataset="gov_10a_main",
            filters={"geo": "EA20"},
            value_name="interest_pct_gdp",
        ),
        "yield": EurostatSeriesSpec(
            dataset="irt_lt_mcby_a",
            filters={"geo": "EA20"},
            value_name="ten_year_yield_pct",
        ),
    }

    result = _fetch_available_panel_series(FakeClient(), series, 2024, 2024)

    assert result.loc[0, "interest_pct_gdp"] == 1.5
    assert pd.isna(result.loc[0, "ten_year_yield_pct"])
    assert "returned geo=[]" in result.loc[0, "ten_year_yield_pct_missing_reason"]


def test_concat_preserving_columns_avoids_all_null_warning() -> None:
    pieces = [
        pd.DataFrame({"geo": ["PT"], "value": [1.0], "optional": [pd.NA]}),
        pd.DataFrame({"geo": ["EA20"], "value": [2.0], "optional": ["missing"]}),
    ]

    with warnings.catch_warnings():
        warnings.filterwarnings("error", category=FutureWarning)
        result = _concat_preserving_columns(pieces)

    assert result["geo"].tolist() == ["PT", "EA20"]
    assert "optional" in result.columns
