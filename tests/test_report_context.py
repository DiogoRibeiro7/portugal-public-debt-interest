"""Guards that every debt-dynamics number in the report is generated.

Two kinds of check live here. The first group verifies that the generated
context is computed on the debt-dynamics rate rather than the average-debt
descriptive rate. The second group scans the paper source to confirm that no
debt-dynamics value is typed into LaTeX by hand.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import pytest

from pt_debt_interest.metrics import calculate_metrics
from pt_debt_interest.report_context import (
    build_debt_dynamics_context,
    load_debt_dynamics_context,
    write_debt_dynamics_context,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PAPER = REPO_ROOT / "paper" / "portugal_public_debt_interest_report.tex"
PROCESSED = REPO_ROOT / "data" / "processed" / "portugal_debt_interest.csv"

#: Values produced by the superseded average-debt rate. They must never
#: reappear in the report source.
STALE_AVERAGE_RATE_VALUES = ("10.49", "-12.07", "-8.77", "-4.29", "4.67")


def _analytical_frame() -> pd.DataFrame:
    """Build a frame with the columns the debt-dynamics context needs."""
    years = list(range(2018, 2026))
    interest_mio_eur = [6805.8, 6226.9, 5697.1, 5117.8, 4608.0, 5553.3, 5934.8, 5964.5]
    debt_mio_eur = [
        249_000.0,
        250_500.0,
        270_500.0,
        281_000.0,
        279_500.0,
        272_000.0,
        270_901.9,
        275_062.8,
    ]
    nominal_gdp_mio_eur = [
        205_000.0,
        214_500.0,
        201_600.0,
        217_000.0,
        244_500.0,
        271_000.0,
        289_784.3,
        306_749.6,
    ]
    frame = pd.DataFrame(
        {
            "year": years,
            "interest_mio_eur": interest_mio_eur,
            "debt_mio_eur": debt_mio_eur,
            "nominal_gdp_mio_eur": nominal_gdp_mio_eur,
            "overall_balance_pct_gdp": [-0.4, 0.1, -5.8, -2.8, -0.3, 1.1, 0.6, 0.7],
        }
    )
    return calculate_metrics(frame)


def _pb_star(rate_decimal: float, growth_pct: float, lagged_debt_pct: float) -> float:
    growth = growth_pct / 100.0
    return ((rate_decimal - growth) / (1.0 + growth)) * (lagged_debt_pct / 100.0) * 100.0


def _paper_source() -> str:
    if not PAPER.is_file():
        pytest.skip("paper source is not present")
    return PAPER.read_text(encoding="utf-8")


def _debt_dynamics_prose(source: str) -> str:
    """Return the debt-dynamics narrative block of the paper.

    Anchored on the generated macro rather than a prose phrase: the narrative
    is edited freely, but the macro is the thing under test.
    """
    start = source.index(r"\DebtDynamicsInterestGrowthTwentyTwentyPp")
    start = source.rindex("\n\n", 0, start) + 2
    end = source.index(r"\label{sec:burden-decomposition}", start)
    return source[start:end]


def test_report_context_2022_pb_star_uses_r_dd() -> None:
    frame = _analytical_frame()
    context = build_debt_dynamics_context(frame, focus_years=(2020, 2022, 2023))
    values = context["focus_years"]["2022"]

    from_debt_dynamics_rate = _pb_star(
        values["debt_dynamics_interest_rate_pct"] / 100.0,
        values["nominal_gdp_growth_pct"],
        values["lagged_debt_pct_gdp"],
    )
    from_average_debt_rate = _pb_star(
        values["average_debt_interest_rate_pct"] / 100.0,
        values["nominal_gdp_growth_pct"],
        values["lagged_debt_pct_gdp"],
    )

    reported = values["debt_stabilising_primary_balance_before_sfa_pct_gdp"]
    assert reported == pytest.approx(from_debt_dynamics_rate, abs=1e-9)
    assert reported != pytest.approx(from_average_debt_rate, abs=1e-6)


def test_report_context_2023_pb_star_uses_r_dd() -> None:
    frame = _analytical_frame()
    context = build_debt_dynamics_context(frame, focus_years=(2020, 2022, 2023))
    values = context["focus_years"]["2023"]

    from_debt_dynamics_rate = _pb_star(
        values["debt_dynamics_interest_rate_pct"] / 100.0,
        values["nominal_gdp_growth_pct"],
        values["lagged_debt_pct_gdp"],
    )
    from_average_debt_rate = _pb_star(
        values["average_debt_interest_rate_pct"] / 100.0,
        values["nominal_gdp_growth_pct"],
        values["lagged_debt_pct_gdp"],
    )

    reported = values["debt_stabilising_primary_balance_before_sfa_pct_gdp"]
    assert reported == pytest.approx(from_debt_dynamics_rate, abs=1e-9)
    assert reported != pytest.approx(from_average_debt_rate, abs=1e-6)


def test_report_context_matches_debt_dynamics_dataset(tmp_path: Path) -> None:
    frame = _analytical_frame()
    written = write_debt_dynamics_context(frame, tmp_path, focus_years=(2020, 2022, 2023))
    context = load_debt_dynamics_context(tmp_path)

    assert written.is_file()
    assert json.loads(written.read_text(encoding="utf-8")) == context

    indexed = frame.set_index("year")
    for year_text, values in context["focus_years"].items():
        row = indexed.loc[int(year_text)]
        assert values["interest_growth_contribution_pp"] == pytest.approx(
            float(row["interest_growth_contribution_pp"])
        )
        assert values["debt_stabilising_primary_balance_before_sfa_pct_gdp"] == (
            pytest.approx(float(row["debt_stabilising_primary_balance_before_sfa_pct_gdp"]))
        )
        assert values["stock_flow_adjustment_pp"] == pytest.approx(
            float(row["stock_flow_adjustment_pp"])
        )

    stock_flow = pd.to_numeric(indexed["stock_flow_adjustment_pp"]).dropna()
    assert context["stock_flow_adjustment"]["minimum_year"] == int(stock_flow.idxmin())
    assert context["stock_flow_adjustment"]["maximum_year"] == int(stock_flow.idxmax())
    assert context["stock_flow_adjustment"]["minimum_pp"] == pytest.approx(float(stock_flow.min()))
    assert context["stock_flow_adjustment"]["maximum_pp"] == pytest.approx(float(stock_flow.max()))


def test_context_matches_the_processed_dataset() -> None:
    """The shipped context must agree with the processed analytical dataset."""
    if not PROCESSED.is_file():
        pytest.skip("processed dataset has not been generated")
    frame = pd.read_csv(PROCESSED)
    context = build_debt_dynamics_context(frame)
    indexed = frame.set_index("year")

    for year_text, values in context["focus_years"].items():
        row = indexed.loc[int(year_text)]
        assert values["debt_stabilising_primary_balance_before_sfa_pct_gdp"] == (
            pytest.approx(float(row["debt_stabilising_primary_balance_before_sfa_pct_gdp"]))
        )


def test_no_stale_average_rate_debt_dynamics_values() -> None:
    prose = _debt_dynamics_prose(_paper_source())
    for stale in STALE_AVERAGE_RATE_VALUES:
        assert stale not in prose, (
            f"stale average-debt-rate value {stale} is still typed into the report"
        )


def test_debt_dynamics_prose_values_are_generated() -> None:
    prose = _debt_dynamics_prose(_paper_source())

    required_macros = (
        r"\DebtDynamicsInterestGrowthTwentyTwentyPp",
        r"\DebtStabilisingPbTwentyTwentyTwoPctGdp",
        r"\DebtStabilisingPbTwentyTwentyThreePctGdp",
        r"\StockFlowMinPp",
        r"\StockFlowMinYear",
        r"\StockFlowMaxPp",
        r"\StockFlowMaxYear",
    )
    for macro in required_macros:
        assert macro in prose, f"{macro} is not used in the debt-dynamics prose"

    # No bare decimal may remain in the narrative: every quantity is a macro.
    # Layout arguments such as `width=0.9\textwidth` are not reported numbers,
    # so graphics directives are dropped before scanning.
    narrative = re.sub(r"\\includegraphics\[[^\]]*\]\{[^}]*\}", "", prose)
    bare_decimals = re.findall(r"(?<![\w.{])-?\d+\.\d+", narrative)
    assert not bare_decimals, f"hand-typed values remain in the prose: {bare_decimals}"


def test_maximum_reconciliation_error_reported_correctly() -> None:
    source = _paper_source()
    assert r"\DebtDynamicsMaxReconciliationErrorPp" in source, (
        "the maximum reconciliation error is not reported"
    )

    if not PROCESSED.is_file():
        pytest.skip("processed dataset has not been generated")
    frame = pd.read_csv(PROCESSED)
    context = build_debt_dynamics_context(frame)
    reported = context["reconciliation"]["maximum_absolute_error_pp"]
    expected = (
        pd.to_numeric(frame["debt_dynamics_reconciliation_error_pp"], errors="coerce").abs().max()
    )
    assert reported == pytest.approx(float(expected))
    assert reported < 1e-9
