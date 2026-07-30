"""Publication-presentation guards for the generated tables.

These tests read the generated LaTeX fragments rather than the analytical
frames, because the failures they guard against are display failures: a decimal
ratio printed under a percentage heading, a table that does not add up, a
negative zero, or an internal identifier reaching the page.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from pt_debt_interest.display import (
    PUBLICATION_LABELS,
    components_sum_to_total,
    format_residual,
    publication_label,
    round_components_to_total,
)
from pt_debt_interest.latex_tables import interest_burden_decomposition_table

REPO_ROOT = Path(__file__).resolve().parents[1]
TABLES = REPO_ROOT / "reports" / "tables"

DIAGNOSTIC = "debt_dynamics_diagnostic_2020_2025.tex"
DECOMPOSITION = "interest_burden_decomposition_endpoints.tex"
COUNTERFACTUALS = "interest_burden_counterfactuals.tex"

#: Columns of the diagnostic table that are percentages or percentage points.
#: A decimal ratio in any of them would sit far below these magnitudes.
DIAGNOSTIC_UNIT_COLUMNS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)


def _generated(name: str) -> str:
    path = TABLES / name
    if not path.is_file():
        pytest.skip(f"{name} has not been generated")
    return path.read_text(encoding="utf-8")


def _body_rows(content: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in content.splitlines():
        if not re.match(r"^\d{4} &", line):
            continue
        cells = [cell.strip() for cell in line.rstrip("\\ ").split("&")]
        rows.append(cells)
    return rows


def _header_cells(content: str) -> list[str]:
    for index, line in enumerate(content.splitlines()):
        if line.strip() == r"\toprule":
            header = content.splitlines()[index + 1]
            return [cell.strip() for cell in header.rstrip("\\ ").split("&")]
    raise AssertionError("table has no header row")


def test_diagnostic_table_uses_consistent_display_units() -> None:
    content = _generated(DIAGNOSTIC)
    header = _header_cells(content)

    # Every column after the year must declare its unit.
    for cell in header[1:]:
        assert r"\%" in cell or "pp" in cell, f"column {cell!r} declares no unit"

    assert "decimal ratio" not in content.split(r"\midrule")[0]
    assert "no decimal ratios are displayed" in content


def test_no_decimal_ratio_displayed_as_percent_without_conversion() -> None:
    content = _generated(DIAGNOSTIC)
    rows = _body_rows(content)
    assert rows, "diagnostic table has no rows"

    for cells in rows:
        year = cells[0]
        # The lagged debt ratio is the clearest tell: a decimal ratio would
        # print as 1.16 rather than 116.10.
        lagged_debt = float(cells[2])
        assert lagged_debt > 10.0, (
            f"{year}: lagged debt/GDP {lagged_debt} looks like a decimal ratio"
        )

        # Contribution terms are percentage points, so the pandemic year has to
        # be an order of magnitude above a decimal ratio.
        if year == "2020":
            assert float(cells[6]) > 1.0, "interest-growth contribution is not in pp"
            assert float(cells[8]) > 1.0, "stock-flow adjustment is not in pp"
            assert abs(float(cells[9])) > 1.0, "observed change is not in pp"


def test_decomposition_display_components_sum_to_total() -> None:
    content = _generated(DECOMPOSITION)
    rows = _body_rows(content)
    assert rows, "decomposition table has no rows"

    for cells in rows:
        total = float(cells[4])
        rate = float(cells[5])
        exposure = float(cells[6])
        assert components_sum_to_total([rate, exposure], total, 3), (
            f"{cells[0]}-{cells[1]}: {rate} + {exposure} != {total}"
        )


def test_round_components_to_total_is_additive() -> None:
    # The three intervals that drifted before the additive rounding was added.
    cases = [
        ([-1.279197, -0.542421], -1.821619),
        ([-0.944546, 0.903322], -0.041224),
        ([-0.901609, -0.112655], -1.014264),
    ]
    for components, total in cases:
        rounded = round_components_to_total(components, total, 3)
        assert sum(rounded) == pytest.approx(round(total, 3), abs=1e-9)
        for original, displayed in zip(components, rounded, strict=True):
            assert abs(original - displayed) <= 0.001 + 1e-9


def test_reconciliation_error_display_not_negative_zero() -> None:
    for name in (DIAGNOSTIC, DECOMPOSITION):
        content = _generated(name)
        assert "-0.00000000" not in content, f"{name} prints a negative zero"
        assert not re.search(r"&\s*-0\.0+\s*(&|\\\\)", content), f"{name} prints a signed zero"

    assert format_residual(-0.0) == "$< 10^{-10}$"
    assert format_residual(-1.734723475976807e-16) == "$< 10^{-10}$"
    assert not format_residual(-1e-11).startswith("-0.")
    # A real failure must stay visible rather than being hidden by the floor.
    assert format_residual(-0.25) == "-0.250"


def test_publication_labels_contain_no_internal_identifiers() -> None:
    for name in (DECOMPOSITION, COUNTERFACTUALS):
        content = _generated(name)
        body = content.split(r"\midrule")[1]
        assert "debt\\_exposure" not in body, f"{name} leaks an internal identifier"
        assert "rate\\_2014\\_with\\_exposure\\_2025" not in body
        assert "rate\\_2025\\_with\\_exposure\\_2014" not in body
        assert not re.search(r"[a-z]+\\_[a-z]", body), f"{name} contains a snake_case identifier"

    assert publication_label("debt_exposure") == "Debt exposure"
    assert publication_label("rate") == "Financing cost"
    assert publication_label("rate_2014_with_exposure_2025") == "2014 rate with 2025 debt exposure"
    # An unknown identifier is humanised, never passed through raw.
    assert "_" not in publication_label("some_new_internal_name")


def test_publication_source_note_is_human_readable() -> None:
    for name in (DIAGNOSTIC, DECOMPOSITION, COUNTERFACTUALS):
        content = _generated(name)
        assert "Source: author calculations from Eurostat data." in content
        assert "basis: not applicable" not in content
        assert "status: not applicable" not in content


def test_generated_tables_reproduce_from_the_display_layer(tmp_path: Path) -> None:
    """The display rules must hold for a freshly generated table, not only the
    committed one."""
    interest_burden_decomposition_table(_frame(), tmp_path)

    decomposition = (tmp_path / DECOMPOSITION).read_text(encoding="utf-8")
    for cells in _body_rows(decomposition):
        assert components_sum_to_total([float(cells[5]), float(cells[6])], float(cells[4]), 3)
    assert "-0.00000000" not in decomposition
    assert "debt\\_exposure" not in decomposition.split(r"\midrule")[1]


def _frame() -> pd.DataFrame:
    # 1995 is present only so that 1996 has a lagged debt stock; the endpoint
    # decomposition drops any year without one.
    years = [1995, 1996, 2000, 2007, 2014, 2019, 2020, 2021, 2022, 2023, 2025]
    debt = [95.0, 100.0, 110.0, 140.0, 210.0, 230.0, 240.0, 235.0, 220.0, 215.0, 200.0]
    gdp = [100.0, 108.0, 140.0, 180.0, 210.0, 250.0, 260.0, 270.0, 280.0, 295.0, 310.0]
    rates = [
        0.050,
        0.048,
        0.042,
        0.038,
        0.035,
        0.025,
        0.023,
        0.021,
        0.019,
        0.020,
        0.022,
    ]
    interest = [4.75]
    for index in range(1, len(years)):
        interest.append(rates[index] * (debt[index - 1] + debt[index]) / 2.0)
    return pd.DataFrame(
        {
            "year": years,
            "interest_mio_eur": interest,
            "interest_pct_gdp": [
                round(value / current * 100.0, 1)
                for value, current in zip(interest, gdp, strict=True)
            ],
            "average_debt_interest_rate": rates,
            "average_debt_interest_rate_pct": [rate * 100.0 for rate in rates],
            "debt_mio_eur": debt,
            "nominal_gdp_mio_eur": gdp,
            "observation_status": ["observed"] * len(years),
            "regime": ["sample"] * len(years),
            "debt_pct_gdp": [
                value / current * 100.0 for value, current in zip(debt, gdp, strict=True)
            ],
            "government_expenditure_mio_eur": [50.0] * len(years),
            "government_expenditure_pct_gdp": [45.0] * len(years),
            "government_revenue_mio_eur": [52.0] * len(years),
            "government_revenue_pct_gdp": [47.0] * len(years),
            "ten_year_yield_pct": [3.0] * len(years),
            "overall_balance_pct_gdp": [0.0] * len(years),
            "primary_balance_pct_gdp": [2.0] * len(years),
            "nominal_gdp_growth_pct": [float("nan")] + [4.0] * (len(years) - 1),
            "real_gdp_growth_pct": [2.0] * len(years),
            "gdp_deflator_growth_pct": [2.0] * len(years),
        }
    )


def test_publication_label_table_covers_the_known_identifiers() -> None:
    for identifier, label in PUBLICATION_LABELS.items():
        assert "_" not in label, f"{identifier} maps to a snake_case label"
        assert label[0].isupper() or label[0].isdigit()
