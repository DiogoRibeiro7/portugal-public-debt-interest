"""European comparator-panel helpers."""

from __future__ import annotations

import copy

import pandas as pd

from .config import EurostatSeriesSpec
from .exceptions import ValidationError
from .metrics import calculate_metrics

GEO_DISPLAY_NAMES = {
    "PT": "Portugal",
    "ES": "Spain",
    "IT": "Italy",
    "EL": "Greece",
    "IE": "Ireland",
    "EA20": "Euro area - 20 countries",
    "DE": "Germany",
    "NL": "Netherlands",
}

AGGREGATE_GEOS = {"EA", "EA12", "EA19", "EA20"}
PANEL_MISSINGNESS_COLUMNS = [
    "interest_mio_eur",
    "interest_pct_gdp",
    "debt_mio_eur",
    "debt_pct_gdp",
    "nominal_gdp_mio_eur",
    "implicit_interest_rate_pct",
    "ten_year_yield_pct",
]


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


def validate_country_year_panel(frame: pd.DataFrame) -> None:
    """Reject duplicate country-year rows in a comparator panel."""
    required = {"geo", "year"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValidationError(f"panel is missing required columns: {sorted(missing)}")
    duplicated = frame.duplicated(subset=["geo", "year"])
    if duplicated.any():
        keys = frame.loc[duplicated, ["geo", "year"]].to_dict(orient="records")
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
        country_mask = ~output["is_aggregate"].fillna(False).astype(bool)
    else:
        country_mask = pd.Series(True, index=output.index)
    output["interest_burden_rank"] = pd.Series(pd.NA, index=output.index, dtype="Int64")
    output["implicit_rate_rank"] = pd.Series(pd.NA, index=output.index, dtype="Int64")
    rank_columns = {
        "interest_burden_rank": "interest_pct_gdp",
        "implicit_rate_rank": "implicit_interest_rate_pct",
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
