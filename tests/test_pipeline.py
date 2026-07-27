import warnings
from pathlib import Path

import pandas as pd
import pytest

from pt_debt_interest.config import EurostatSeriesSpec, load_settings
from pt_debt_interest.exceptions import SourceError
from pt_debt_interest.pipeline import (
    _add_eurostat_row_provenance,
    _build_ameco_pre1995,
    _canonicalise_annual_table,
    _concat_preserving_columns,
    _fetch_available_panel_series,
    build_eurostat_panel,
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


def test_add_eurostat_row_provenance_collapses_series_metadata() -> None:
    frame = pd.DataFrame(
        {
            "year": [2024],
            "interest_mio_eur_retrieval_timestamp_utc": ["20260726T010000Z"],
            "debt_mio_eur_retrieval_timestamp_utc": ["20260726T010001Z"],
            "interest_mio_eur_source_sha256": ["abc"],
            "debt_mio_eur_source_sha256": ["def"],
            "interest_mio_eur_raw_file": ["eurostat_interest_20260726T010000Z.json"],
            "debt_mio_eur_raw_file": ["eurostat_debt_20260726T010001Z.json"],
        }
    )

    result = _add_eurostat_row_provenance(frame)

    assert result.loc[0, "retrieval_timestamp_utc"] == (
        "20260726T010000Z;20260726T010001Z"
    )
    assert result.loc[0, "source_checksum_sha256"] == "abc;def"
    assert "eurostat_interest_20260726T010000Z.json" in result.loc[0, "source_vintage"]


def test_clear_ameco_interim_removes_stale_file(tmp_path: Path) -> None:
    settings = load_settings("config/default.yaml")
    interim_dir = tmp_path / settings.paths.interim
    interim_dir.mkdir(parents=True)
    stale = interim_dir / "ameco_linked.csv"
    stale.write_text("year,value\n1994,1\n", encoding="utf-8")

    removed = clear_ameco_interim(settings, tmp_path)

    assert removed == stale
    assert not stale.exists()


def test_build_ameco_pre1995_rejects_non_positive_interest_ratio() -> None:
    frame = pd.DataFrame(
        {
            "year": [1994],
            "interest_bn_eur_ameco": [5.0],
            "interest_pct_gdp_ameco": [0.0],
        }
    )

    with pytest.raises(SourceError, match="interest_pct_gdp_ameco must be positive"):
        _build_ameco_pre1995(frame, 1995)


def test_build_ameco_pre1995_rejects_non_positive_debt_ratio() -> None:
    frame = pd.DataFrame(
        {
            "year": [1994],
            "interest_bn_eur_ameco": [5.0],
            "interest_pct_gdp_ameco": [5.0],
            "debt_pct_gdp_ameco": [0.0],
        }
    )

    with pytest.raises(SourceError, match="debt_pct_gdp_ameco must be positive"):
        _build_ameco_pre1995(frame, 1995)


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


def test_fetch_available_panel_series_raises_for_required_missing_series() -> None:
    class FakeClient:
        def fetch_series(
            self,
            name: str,
            spec: EurostatSeriesSpec,
            start_year: int,
            end_year: int,
        ) -> pd.DataFrame:
            if name == "interest":
                raise SourceError("Eurostat gov_10a_main returned no values")
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

    with pytest.raises(SourceError, match="mandatory comparator series interest failed"):
        _fetch_available_panel_series(FakeClient(), series, 2024, 2024)


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


def test_build_eurostat_panel_writes_metrics_and_missingness(tmp_path: Path) -> None:
    settings = load_settings("config/default.yaml")
    interim_dir = tmp_path / settings.paths.interim
    interim_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "geo": ["PT", "PT", "ES", "ES"],
            "year": [2021, 2022, 2021, 2022],
            "interest_mio_eur": [5.0, 6.0, 4.0, 5.0],
            "nominal_gdp_mio_eur": [100.0, 120.0, 100.0, 125.0],
            "debt_mio_eur": [100.0, 110.0, 90.0, 95.0],
            "source": ["Eurostat"] * 4,
            "accounting_basis": ["ESA2010"] * 4,
            "observation_status": ["observed"] * 4,
            "is_aggregate": [False] * 4,
        }
    ).to_csv(interim_dir / "eurostat_panel.csv", index=False)

    outputs = build_eurostat_panel(settings, tmp_path)

    assert outputs["metrics"].exists()
    assert outputs["missingness"].exists()
