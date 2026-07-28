"""European comparator-panel helpers."""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from .config import EurostatSeriesSpec
from .exceptions import ValidationError
from .metrics import calculate_metrics

GEO_DISPLAY_NAMES = {
    "AT": "Austria",
    "BE": "Belgium",
    "CY": "Cyprus",
    "DE": "Germany",
    "EA20": "Euro area - 20 countries",
    "EE": "Estonia",
    "EL": "Greece",
    "ES": "Spain",
    "EU27_2020": "European Union - 27 countries",
    "FI": "Finland",
    "FR": "France",
    "HR": "Croatia",
    "IE": "Ireland",
    "IT": "Italy",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "LV": "Latvia",
    "MT": "Malta",
    "NL": "Netherlands",
    "PT": "Portugal",
    "SI": "Slovenia",
    "SK": "Slovakia",
}

AGGREGATE_GEOS = {"EA", "EA12", "EA19", "EA20", "EU27_2020"}
PANEL_MISSINGNESS_COLUMNS = [
    "interest_mio_eur",
    "interest_pct_gdp",
    "debt_mio_eur",
    "debt_pct_gdp",
    "nominal_gdp_mio_eur",
    "government_expenditure_mio_eur",
    "government_expenditure_pct_gdp",
    "implicit_interest_rate_average_debt_pct",
    "ten_year_yield_pct",
]
_TRUE_FLAG_VALUES = {"1", "true", "t", "yes", "y"}
_FALSE_FLAG_VALUES = {"0", "false", "f", "no", "n", ""}


def geography_metadata(geo: str) -> dict[str, object]:
    """Return stable display metadata for a Eurostat geography code."""
    return {
        "geo": geo,
        "geo_name": GEO_DISPLAY_NAMES.get(geo, geo),
        "is_aggregate": geo in AGGREGATE_GEOS,
        "aggregate_composition": geo if geo in AGGREGATE_GEOS else pd.NA,
    }


def series_specs_for_geo(
    series: dict[str, EurostatSeriesSpec],
    geo: str,
) -> dict[str, EurostatSeriesSpec]:
    """Copy configured Eurostat series specs and replace only the geography filter."""
    copied: dict[str, EurostatSeriesSpec] = {}
    for name, spec in series.items():
        filters = copy.deepcopy(spec.filters)
        filters["geo"] = geo
        copied[name] = EurostatSeriesSpec(
            dataset=spec.dataset,
            filters=filters,
            value_name=spec.value_name,
        )
    return copied


def aggregate_flag_mask(values: pd.Series) -> pd.Series:
    """Return normalized aggregate flags from mixed CSV/object values."""

    def convert(value: object) -> bool:
        if value is None or value is pd.NA or value is pd.NaT:
            return False
        if isinstance(value, float) and np.isnan(value):
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            numeric = float(value)
            if np.isfinite(numeric) and numeric in {0.0, 1.0}:
                return bool(numeric)
        text = str(value).strip().lower()
        if text in _TRUE_FLAG_VALUES:
            return True
        if text in _FALSE_FLAG_VALUES:
            return False
        raise ValidationError(f"aggregate flags must be boolean-like: {value!r}")

    return pd.Series([convert(value) for value in values], index=values.index, dtype=bool)


def validate_country_year_panel(frame: pd.DataFrame) -> None:
    """Reject duplicate country-year rows in a comparator panel."""
    key_columns = ["geo", "year"]
    missing = set(key_columns).difference(frame.columns)
    if missing:
        raise ValidationError(f"panel is missing required columns: {sorted(missing)}")
    null_keys = frame[key_columns].isna().any(axis=1)
    if null_keys.any():
        keys = frame.loc[null_keys, key_columns].to_dict(orient="records")
        raise ValidationError(f"panel contains missing country-year keys: {keys}")
    blank_geo = frame["geo"].astype(str).str.strip().eq("")
    if blank_geo.any():
        keys = frame.loc[blank_geo, key_columns].to_dict(orient="records")
        raise ValidationError(f"panel contains blank geography keys: {keys}")
    try:
        numeric_years = pd.to_numeric(frame["year"], errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValidationError("panel year keys must be numeric") from exc
    invalid_years = (~np.isfinite(numeric_years)) | numeric_years.mod(1).ne(0)
    if invalid_years.any():
        keys = frame.loc[invalid_years, key_columns].to_dict(orient="records")
        raise ValidationError(f"panel year keys must be whole numbers: {keys}")

    key_frame = frame[key_columns].copy()
    key_frame["year"] = numeric_years.astype(int)
    duplicated = key_frame.duplicated(subset=key_columns, keep=False)
    if duplicated.any():
        keys = frame.loc[duplicated, key_columns].to_dict(orient="records")
        raise ValidationError(f"duplicate country-year keys in panel: {keys}")


def panel_missingness(frame: pd.DataFrame, value_columns: list[str]) -> pd.DataFrame:
    """Summarise missing values by geography for selected analytical columns."""
    validate_country_year_panel(frame)
    records: list[dict[str, object]] = []
    for geo, group in frame.groupby("geo"):
        for column in value_columns:
            if column not in group.columns:
                records.append({"geo": geo, "column": column, "missing_count": len(group)})
            else:
                records.append(
                    {
                        "geo": geo,
                        "column": column,
                        "missing_count": int(group[column].isna().sum()),
                    }
                )
    return pd.DataFrame(records)


def build_panel_metrics(
    frame: pd.DataFrame,
    denominator: str,
    regime_boundaries: list[dict[str, object]] | None = None,
) -> pd.DataFrame:
    """Calculate fiscal metrics for each geography in a country-year panel."""
    validate_country_year_panel(frame)
    pieces: list[pd.DataFrame] = []
    for _, group in frame.groupby("geo", sort=True):
        pieces.append(
            calculate_metrics(
                group.sort_values("year"),
                denominator=denominator,
                regime_boundaries=regime_boundaries,
            )
        )
    output = pd.concat(pieces, ignore_index=True, sort=False)
    return add_panel_ranks(output)


def add_panel_ranks(frame: pd.DataFrame) -> pd.DataFrame:
    """Add per-year ranks for country rows, excluding aggregate geographies."""
    output = frame.copy()
    if "is_aggregate" in output.columns:
        country_mask = ~aggregate_flag_mask(output["is_aggregate"])
    else:
        country_mask = pd.Series(True, index=output.index)
    output["interest_burden_rank"] = pd.Series(pd.NA, index=output.index, dtype="Int64")
    output["average_debt_rate_rank"] = pd.Series(pd.NA, index=output.index, dtype="Int64")
    rank_columns = {
        "interest_burden_rank": "interest_pct_gdp",
        "average_debt_rate_rank": "implicit_interest_rate_average_debt_pct",
    }
    for rank_column, value_column in rank_columns.items():
        if value_column not in output.columns:
            continue
        ranks = output.loc[country_mask].groupby("year")[value_column].rank(
            ascending=False,
            method="min",
        )
        output.loc[ranks.index, rank_column] = ranks.astype("Int64")
    return output.sort_values(["geo", "year"]).reset_index(drop=True)
