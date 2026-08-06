"""Guards for euro-area eligibility, observation status, and ranking.

The failure these protect against is a rank without a denominator, or a
denominator inflated by aggregates and ineligible geographies. They also pin
the observation status to Eurostat's per-series flags rather than the panel's
blanket ``observed`` label.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pt_debt_interest.eligibility import (
    EURO_AREA_MEMBERS,
    RANKING_METHOD,
    build_comparison_summary,
    build_eligibility_table,
    competition_rank,
    derive_observation_status,
    latest_common_year,
    three_year_average_ranking,
)
from pt_debt_interest.exceptions import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
PANEL = REPO_ROOT / "data" / "processed" / "eurostat_panel_metrics.csv"
PAPER = REPO_ROOT / "paper" / "portugal_public_debt_interest_report.tex"


def _panel() -> pd.DataFrame:
    if not PANEL.is_file():
        pytest.skip("comparator panel has not been generated")
    return pd.read_csv(PANEL)


def _latest_year(panel: pd.DataFrame) -> int:
    return int(pd.to_numeric(panel["year"], errors="coerce").max())


def _synthetic_panel() -> pd.DataFrame:
    rows = []
    values = {"PT": 1.9, "IT": 3.9, "DE": 1.1, "IE": 0.5, "EA20": 2.0, "SE": 1.0}
    aggregates = {"EA20"}
    for year in (2023, 2024, 2025):
        for geo, value in values.items():
            rows.append(
                {
                    "geo": geo,
                    "geo_name": geo,
                    "year": year,
                    "is_aggregate": geo in aggregates,
                    "interest_pct_gdp": value,
                    "debt_pct_gdp": 90.0,
                    "interest_mio_eur": 5000.0,
                    "nominal_gdp_mio_eur": 300000.0,
                    "average_debt_interest_rate_pct": 2.0,
                    "ten_year_yield_pct": 3.0,
                    "primary_balance_pct_gdp": 1.0,
                    "observation_status": "observed",
                }
            )
    return pd.DataFrame(rows)


def test_aggregates_excluded_from_rank() -> None:
    panel = _panel()
    year = _latest_year(panel)
    eligibility = build_eligibility_table(panel, year)

    aggregates = eligibility.loc[eligibility["is_aggregate"]]
    assert not aggregates.empty, "the panel should contain aggregates to exclude"
    assert not aggregates["included_in_rank"].any()
    for reason in aggregates["exclusion_reason"]:
        assert "aggregate geography" in reason


def test_non_euro_area_countries_excluded() -> None:
    eligibility = build_eligibility_table(_synthetic_panel(), 2025)
    outsider = eligibility.loc[eligibility["eurostat_code"].eq("SE")].iloc[0]
    assert not outsider["euro_area_member"]
    assert not outsider["included_in_rank"]
    assert "not a euro-area member" in outsider["exclusion_reason"]

    included = eligibility.loc[eligibility["included_in_rank"], "eurostat_code"]
    assert set(included).issubset(EURO_AREA_MEMBERS)


def test_competition_rank_ties() -> None:
    values = pd.Series([3.9, 2.2, 2.2, 1.1])
    ranks = competition_rank(values)
    assert list(ranks) == [1, 2, 2, 4], "ties must use competition ranking"
    assert RANKING_METHOD == "competition"


def test_rank_denominator_matches_eligibility() -> None:
    panel = _panel()
    year = _latest_year(panel)
    eligibility = build_eligibility_table(panel, year)
    summary = build_comparison_summary(panel, eligibility, year)

    assert summary["eligible_countries"] == int(eligibility["included_in_rank"].sum())
    assert summary["excluded_count"] == int((~eligibility["included_in_rank"]).sum())
    assert summary["eligible_countries"] + summary["excluded_count"] == len(eligibility)
    assert 1 <= int(summary["home_rank"]) <= int(summary["eligible_countries"])


def test_percentile_calculation() -> None:
    panel = _synthetic_panel()
    eligibility = build_eligibility_table(panel, 2025)
    summary = build_comparison_summary(panel, eligibility, 2025)

    # Eligible: PT 1.9, IT 3.9, DE 1.1, IE 0.5. Three are at or below PT.
    assert summary["eligible_countries"] == 4
    assert summary["percentile"] == pytest.approx(75.0)
    assert summary["home_rank"] == 2


def test_median_and_quartiles() -> None:
    panel = _synthetic_panel()
    eligibility = build_eligibility_table(panel, 2025)
    summary = build_comparison_summary(panel, eligibility, 2025)

    eligible_values = pd.Series([1.9, 3.9, 1.1, 0.5])
    assert summary["median"] == pytest.approx(float(eligible_values.median()))
    assert summary["first_quartile"] == pytest.approx(
        float(eligible_values.quantile(0.25))
    )
    assert summary["third_quartile"] == pytest.approx(
        float(eligible_values.quantile(0.75))
    )
    assert summary["home_minus_median"] == pytest.approx(
        1.9 - float(eligible_values.median())
    )


def test_observation_status_filter() -> None:
    """Status comes from Eurostat's flags, not from a blanket label."""
    panel = _panel()
    year = _latest_year(panel)

    # The panel labels every row observed; the derived status must not agree.
    assert set(panel.loc[panel["year"].eq(year), "observation_status"]) == {"observed"}
    eligibility = build_eligibility_table(panel, year)
    assert (eligibility["observation_status"] != "observed").any(), (
        "provisional Eurostat flags are being ignored"
    )

    # A rejected status excludes the geography.
    strict = build_eligibility_table(panel, year, accepted_statuses=("observed",))
    provisional = strict.loc[strict["observation_status"].eq("provisional")]
    assert not provisional.empty
    assert not provisional["included_in_rank"].any()
    for reason in provisional["exclusion_reason"]:
        assert "observation status not accepted" in reason

    row = pd.Series({"interest_pct_gdp_status": "p", "debt_pct_gdp_status": np.nan})
    assert derive_observation_status(row, ("interest_pct_gdp", "debt_pct_gdp")) == (
        "provisional"
    )
    clean = pd.Series({"interest_pct_gdp_status": np.nan})
    assert derive_observation_status(clean, ("interest_pct_gdp",)) == "observed"


def test_latest_common_year() -> None:
    panel = _panel()
    computed = latest_common_year(panel)
    assert isinstance(computed, int)
    assert computed <= _latest_year(panel)

    # Drop one country's latest observation: the common year must step back.
    reduced = panel.copy()
    year = _latest_year(panel)
    mask = reduced["geo"].eq("IE") & reduced["year"].eq(year)
    reduced.loc[mask, "interest_pct_gdp"] = np.nan
    assert latest_common_year(reduced) < computed


def test_latest_common_year_refuses_missing_required_column() -> None:
    panel = _synthetic_panel().drop(columns=["average_debt_interest_rate_pct"])
    with pytest.raises(ValidationError, match="missing required series"):
        latest_common_year(panel)


def test_three_year_average_requires_minimum_observations() -> None:
    panel = _synthetic_panel()
    eligibility = build_eligibility_table(panel, 2025)

    full = three_year_average_ranking(panel, 2025, eligibility, minimum_observations=2)
    assert len(full) == 4
    assert list(full["rank"]) == sorted(full["rank"])

    # Leave Ireland with a single observation in the window.
    sparse = panel.loc[
        ~(panel["geo"].eq("IE") & panel["year"].isin([2024, 2025]))
    ].copy()
    limited = three_year_average_ranking(
        sparse, 2025, eligibility, minimum_observations=2
    )
    assert "IE" not in set(limited["geo"])
    assert len(limited) == 3


def test_missing_values_not_replaced_with_zero() -> None:
    panel = _synthetic_panel()
    panel.loc[panel["geo"].eq("DE") & panel["year"].eq(2025), "interest_pct_gdp"] = (
        np.nan
    )
    eligibility = build_eligibility_table(panel, 2025)

    germany = eligibility.loc[eligibility["eurostat_code"].eq("DE")].iloc[0]
    assert not germany["interest_pct_gdp_available"]
    assert not germany["included_in_rank"]
    assert "missing series" in germany["exclusion_reason"]

    summary = build_comparison_summary(panel, eligibility, 2025)
    assert summary["eligible_countries"] == 3
    # A zero-filled Germany would drag the median down to 1.1 or below.
    assert summary["median"] == pytest.approx(1.9)


def test_figure_contains_median_reference() -> None:
    if not PAPER.is_file():
        pytest.skip("paper source is not present")
    source = PAPER.read_text(encoding="utf-8")
    assert "08_european_comparison" in source

    figure = REPO_ROOT / "reports" / "figures" / "08_european_comparison.svg"
    if not figure.is_file():
        pytest.skip("comparison figure has not been generated")
    content = figure.read_text(encoding="utf-8", errors="ignore")
    assert "Median" in content, "the figure carries no median reference line"
