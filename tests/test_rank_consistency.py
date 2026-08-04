"""The rank tables must agree with each other and with the stated convention.

The fragility table once reported Portugal two ranks lower than the headline
table at an unperturbed value, because ``1.9 - 0.3`` evaluates to
``1.5999999999999999`` and lost a tie it should have joined. Nothing caught it:
both tables were internally consistent, both used the documented ranking
method, and the wrong number read as plausible. These tests are the guard.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pt_debt_interest.eligibility import (
    EURO_AREA_ADOPTION_YEAR,
    competition_rank,
    euro_area_members,
)
from pt_debt_interest.latex_tables import PERTURBATION_DECIMALS


def _panel(values: dict[str, float], year: int = 2025) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "geo": geo,
                "geo_name": geo,
                "year": year,
                "is_aggregate": False,
                "interest_pct_gdp": value,
                "debt_pct_gdp": 90.0,
                "interest_mio_eur": 1000.0,
                "nominal_gdp_mio_eur": 100000.0,
                "average_debt_interest_rate_pct": 2.0,
                "ten_year_yield_pct": 3.0,
                "primary_balance_pct_gdp": 0.0,
                "observation_status": "observed",
            }
            for geo, value in values.items()
        ]
    )


class TestPerturbationTies:
    """A perturbed value that lands on a comparator's value must tie with it."""

    def test_subtracting_a_shock_still_forms_the_tie(self) -> None:
        base, shock = 1.9, -0.30
        assert base + shock != 1.60, "the float hazard this test exists for is gone"
        assert round(base + shock, PERTURBATION_DECIMALS) == 1.60

    def test_adding_a_shock_still_forms_the_tie(self) -> None:
        base, shock = 1.9, 0.30
        assert base + shock != 2.20
        assert round(base + shock, PERTURBATION_DECIMALS) == 2.20

    def test_the_tie_changes_the_rank(self) -> None:
        """Not a cosmetic difference: the tie is worth two ranks."""
        values = [3.9, 3.2, 2.4, 2.2, 2.2, 1.6, 1.6]
        naive = pd.Series([*values, 1.9 - 0.30])
        rounded = pd.Series([*values, round(1.9 - 0.30, PERTURBATION_DECIMALS)])
        assert int(competition_rank(naive).iloc[-1]) == 8
        assert int(competition_rank(rounded).iloc[-1]) == 6


TABLES = Path("reports/tables")

published = pytest.mark.skipif(
    not (TABLES / "european_rank_sensitivity_2025.tex").is_file(),
    reason="comparison tables not generated in this working tree",
)


def _is_number(cell: str) -> bool:
    try:
        float(cell)
    except ValueError:
        return False
    return True


def _rows(name: str) -> list[list[str]]:
    text = (TABLES / name).read_text(encoding="utf-8")
    return [
        [cell.strip() for cell in line.replace(r"\\", "").split("&")]
        for line in text.splitlines()
        if "&" in line and not line.lstrip().startswith(("\\", "%"))
    ]


class TestPublishedTablesAgree:
    """The headline and fragility tables must not contradict each other."""

    @published
    def test_unperturbed_rank_matches_the_headline_table(self) -> None:
        headline = next(
            row for row in _rows("european_comparison_2025.tex") if "Portugal" in row
        )
        fragility = next(
            row
            for row in _rows("european_rank_sensitivity_2025.tex")
            if row[0] == "0.00"
        )
        assert fragility[2] == headline[0], (
            "the fragility table disagrees with the headline table at zero "
            f"perturbation: {fragility[2]} vs {headline[0]}"
        )

    @published
    def test_the_rank_is_fragile_upward_not_downward(self) -> None:
        """The direction the manuscript reports, asserted against the table."""
        ranks = {
            row[0]: int(row[2])
            for row in _rows("european_rank_sensitivity_2025.tex")
            if _is_number(row[0])
        }
        assert ranks["0.30"] < ranks["0.00"], "a higher burden must worsen the rank"
        assert ranks["-0.30"] == ranks["0.00"], (
            "a lower burden ties into the group below and holds the rank"
        )

    @published
    def test_the_2014_cross_section_uses_2014_membership(self) -> None:
        row = next(row for row in _rows("european_rank_change.tex") if row[0] == "2014")
        assert int(row[2]) == 18, "2014 must rank the eighteen members of that year"


class TestMembershipIsEvaluatedAtTheComparisonYear:
    """The paper states this rule in two places; it must hold in code."""

    def test_the_euro_area_had_eighteen_members_in_2014(self) -> None:
        assert len(euro_area_members(2014)) == 18

    def test_lithuania_and_croatia_are_excluded_from_2014(self) -> None:
        members = euro_area_members(2014)
        assert "LT" not in members and "HR" not in members

    def test_they_are_included_once_they_adopt(self) -> None:
        assert "LT" in euro_area_members(2015)
        assert "HR" in euro_area_members(2023)
        assert "HR" not in euro_area_members(2022)

    @pytest.mark.parametrize(
        ("year", "expected"),
        [(1999, 11), (2001, 12), (2007, 13), (2008, 15), (2009, 16),
         (2011, 17), (2014, 18), (2015, 19), (2023, 20)],
    )
    def test_membership_count_by_year(self, year: int, expected: int) -> None:
        assert len(euro_area_members(year)) == expected

    def test_every_member_has_an_adoption_year(self) -> None:
        assert len(EURO_AREA_ADOPTION_YEAR) == 20

    def test_a_non_member_year_is_reported_with_its_adoption_year(self) -> None:
        from pt_debt_interest.eligibility import build_eligibility_table

        panel = _panel({"PT": 4.8, "LT": 1.0}, year=2014)
        table = build_eligibility_table(panel, 2014)
        reason = table.loc[table["eurostat_code"].eq("LT"), "exclusion_reason"].iloc[0]
        assert "not a euro-area member in 2014" in reason
        assert "adopted 2015" in reason
