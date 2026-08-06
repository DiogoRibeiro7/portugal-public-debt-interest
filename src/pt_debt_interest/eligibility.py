"""Eligibility, observation status, and ranking controls for the euro-area panel.

A rank without a denominator is not a finding. This module decides which
geographies are eligible for a comparison, records why the others were
excluded, derives an honest observation status from Eurostat's own per-series
flags, and computes the ranking with a documented method.

The observation status matters. The panel's own ``observation_status`` column
labels every row ``observed``; Eurostat's per-series flags say otherwise. The
status used here is derived from those flags, so a provisional value is
declared as provisional.
"""

from __future__ import annotations

from typing import Final

import numpy as np
import pandas as pd

from .exceptions import ValidationError
from .panel import aggregate_flag_mask

#: Year each state adopted the euro, by Eurostat geography code.
#:
#: Membership is a function of the comparison year, not of today. Ranking a
#: 2014 cross-section against the 2026 membership list silently admits
#: Lithuania (2015) and Croatia (2023) to a euro area that had eighteen
#: members at the time.
EURO_AREA_ADOPTION_YEAR: Final[dict[str, int]] = {
    "AT": 1999, "BE": 1999, "DE": 1999, "ES": 1999, "FI": 1999,
    "FR": 1999, "IE": 1999, "IT": 1999, "LU": 1999, "NL": 1999,
    "PT": 1999,
    "EL": 2001,
    "SI": 2007,
    "CY": 2008, "MT": 2008,
    "SK": 2009,
    "EE": 2011,
    "LV": 2014,
    "LT": 2015,
    "HR": 2023,
}

#: Every state that has ever adopted the euro. Membership at a given year must
#: go through :func:`euro_area_members`; this set is the union, not a snapshot.
EURO_AREA_MEMBERS: Final[frozenset[str]] = frozenset(EURO_AREA_ADOPTION_YEAR)


def euro_area_members(year: int) -> frozenset[str]:
    """Return the euro-area membership as it stood in ``year``."""
    return frozenset(
        geo for geo, adopted in EURO_AREA_ADOPTION_YEAR.items() if adopted <= year
    )

#: Series a geography must carry to enter the headline comparison.
REQUIRED_SERIES: Final[tuple[str, ...]] = (
    "interest_pct_gdp",
    "debt_pct_gdp",
    "interest_mio_eur",
    "nominal_gdp_mio_eur",
    "average_debt_interest_rate_pct",
)

#: Series reported for transparency but not required for eligibility.
OPTIONAL_SERIES: Final[tuple[str, ...]] = (
    "ten_year_yield_pct",
    "primary_balance_pct_gdp",
)

#: Eurostat flag letters mapped to a spoken status.
_FLAG_STATUS: Final[dict[str, str]] = {
    "p": "provisional",
    "e": "estimated",
    "f": "forecast",
    "d": "definition differs",
    "b": "break in series",
    "u": "low reliability",
}

RANKING_METHOD: Final[str] = "competition"


def derive_observation_status(
    row: pd.Series,
    series: tuple[str, ...] = REQUIRED_SERIES,
) -> str:
    """Derive a row's status from Eurostat's per-series flags.

    The most cautious flag present wins. When no series carries a flag the
    observation is reported as observed; anything else is named.
    """
    found: list[str] = []
    for name in series:
        flag = row.get(f"{name}_status")
        if flag is None or (isinstance(flag, float) and np.isnan(flag)):
            continue
        text = str(flag).strip().lower()
        for letter, status in _FLAG_STATUS.items():
            if letter in text:
                found.append(status)
    if not found:
        return "observed"
    for status in ("forecast", "low reliability", "estimated", "provisional"):
        if status in found:
            return status
    return found[0]


def build_eligibility_table(
    panel: pd.DataFrame,
    year: int,
    accepted_statuses: tuple[str, ...] = ("observed", "provisional"),
    required_series: tuple[str, ...] = REQUIRED_SERIES,
) -> pd.DataFrame:
    """Record eligibility, availability, and status for every geography."""
    if "geo" not in panel.columns or "year" not in panel.columns:
        raise ValidationError("panel must carry geo and year columns")
    snapshot = panel.loc[pd.to_numeric(panel["year"], errors="coerce").eq(year)].copy()
    if snapshot.empty:
        raise ValidationError(f"panel has no rows for {year}")
    snapshot["is_aggregate"] = aggregate_flag_mask(snapshot["is_aggregate"])
    members = euro_area_members(year)

    rows: list[dict[str, object]] = []
    for row in snapshot.itertuples():
        geo = str(row.geo)
        record: dict[str, object] = {
            "country": getattr(row, "geo_name", geo),
            "eurostat_code": geo,
            "euro_area_member": geo in members,
            "is_aggregate": bool(row.is_aggregate),
            "comparison_year": year,
        }
        series_row = snapshot.loc[snapshot["geo"].eq(geo)].iloc[0]
        for name in (*required_series, *OPTIONAL_SERIES):
            available = name in snapshot.columns and pd.notna(series_row.get(name))
            record[f"{name}_available"] = bool(available)

        status = derive_observation_status(series_row, required_series)
        record["observation_status"] = status
        record["accepted_status"] = status in accepted_statuses

        missing = [
            name for name in required_series if not record[f"{name}_available"]
        ]
        reasons: list[str] = []
        if record["is_aggregate"]:
            reasons.append("aggregate geography")
        if not record["euro_area_member"]:
            adopted = EURO_AREA_ADOPTION_YEAR.get(geo)
            reasons.append(
                f"not a euro-area member in {year} (adopted {adopted})"
                if adopted is not None
                else "not a euro-area member"
            )
        if missing:
            reasons.append("missing series: " + ", ".join(missing))
        if not record["accepted_status"]:
            reasons.append(f"observation status not accepted: {status}")

        record["included_in_rank"] = not reasons
        record["exclusion_reason"] = "; ".join(reasons) if reasons else ""
        rows.append(record)

    return pd.DataFrame(rows).sort_values("eurostat_code").reset_index(drop=True)


def competition_rank(values: pd.Series) -> pd.Series:
    """Rank descending with competition ties: 1, 2, 2, 4."""
    return values.rank(ascending=False, method="min").astype("Int64")


def latest_common_year(
    panel: pd.DataFrame,
    required_series: tuple[str, ...] = REQUIRED_SERIES,
) -> int:
    """Latest year in which every eligible country has every required series."""
    working = panel.copy()
    working["is_aggregate"] = aggregate_flag_mask(working["is_aggregate"])
    countries = working.loc[
        ~working["is_aggregate"] & working["geo"].isin(EURO_AREA_MEMBERS)
    ]
    if countries.empty:
        raise ValidationError("panel contains no euro-area countries")

    present = [name for name in required_series if name in countries.columns]
    complete_years: list[int] = []
    for year_key, group in countries.groupby("year"):
        year = int(float(str(year_key)))
        members = euro_area_members(year)
        if not members:
            continue
        member_group = group.loc[group["geo"].astype(str).isin(members)]
        expected = len(members)
        usable = group.dropna(subset=present)
        usable = usable.loc[usable["geo"].astype(str).isin(members)]
        if (
            member_group["geo"].nunique() == expected
            and usable["geo"].nunique() == expected
        ):
            complete_years.append(year)
    if not complete_years:
        raise ValidationError("no year has complete coverage for every country")
    return max(complete_years)


def build_comparison_summary(
    panel: pd.DataFrame,
    eligibility: pd.DataFrame,
    year: int,
    home: str = "PT",
    value_column: str = "interest_pct_gdp",
) -> dict[str, object]:
    """Summarise the home country's position with its denominator and spread."""
    included = eligibility.loc[eligibility["included_in_rank"], "eurostat_code"]
    snapshot = panel.loc[
        pd.to_numeric(panel["year"], errors="coerce").eq(year)
        & panel["geo"].isin(included)
    ].copy()
    if snapshot.empty:
        raise ValidationError(f"no eligible geographies for {year}")

    values = pd.to_numeric(snapshot[value_column], errors="coerce")
    snapshot["rank"] = competition_rank(values)
    home_rows = snapshot.loc[snapshot["geo"].eq(home)]
    if home_rows.empty:
        raise ValidationError(f"{home} is not eligible in {year}")
    home_row = home_rows.iloc[0]
    home_value = float(home_row[value_column])
    eligible_count = len(snapshot)
    home_rank = int(home_row["rank"])

    excluded = eligibility.loc[~eligibility["included_in_rank"]]
    home_status = str(
        eligibility.loc[
            eligibility["eurostat_code"].eq(home), "observation_status"
        ].iloc[0]
    )

    # Percentile: share of eligible countries at or below the home value.
    percentile = float((values <= home_value).sum()) / eligible_count * 100.0

    return {
        "comparison_year": year,
        "value_column": value_column,
        "ranking_method": RANKING_METHOD,
        "home": home,
        "home_value": home_value,
        "home_rank": home_rank,
        "eligible_countries": eligible_count,
        "percentile": percentile,
        "median": float(values.median()),
        "first_quartile": float(values.quantile(0.25)),
        "third_quartile": float(values.quantile(0.75)),
        "home_minus_median": home_value - float(values.median()),
        "excluded_count": len(excluded),
        "exclusion_reasons": "; ".join(
            sorted({str(reason) for reason in excluded["exclusion_reason"] if reason})
        ),
        "home_observation_status": home_status,
        "provisional_countries": int(
            (eligibility["observation_status"] != "observed").sum()
        ),
    }


def three_year_average_ranking(
    panel: pd.DataFrame,
    end_year: int,
    eligibility: pd.DataFrame,
    value_column: str = "interest_pct_gdp",
    minimum_observations: int = 2,
) -> pd.DataFrame:
    """Rank on a three-year average, requiring a minimum number of observations."""
    if minimum_observations < 1:
        raise ValidationError("a ranking average needs at least one observation")
    included = set(eligibility.loc[eligibility["included_in_rank"], "eurostat_code"])
    years = [end_year - 2, end_year - 1, end_year]
    window = panel.loc[
        pd.to_numeric(panel["year"], errors="coerce").isin(years)
        & panel["geo"].isin(included)
    ].copy()

    grouped = window.groupby(["geo", "geo_name"])[value_column]
    summary = grouped.agg(["mean", "count"]).reset_index()
    summary = summary.rename(columns={"mean": "average", "count": "observations"})
    summary["meets_minimum"] = summary["observations"] >= minimum_observations
    qualified = summary.loc[summary["meets_minimum"]].copy()
    qualified["rank"] = competition_rank(qualified["average"])
    return qualified.sort_values("rank").reset_index(drop=True)
