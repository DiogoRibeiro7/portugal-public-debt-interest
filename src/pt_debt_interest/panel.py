"""European comparator-panel helpers."""

from __future__ import annotations

import copy

import pandas as pd

from .config import EurostatSeriesSpec
from .exceptions import ValidationError

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
