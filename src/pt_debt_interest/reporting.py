"""Automatic Markdown report generation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from jinja2 import Template

from .scenarios import static_rate_shock_table

REPORT_TEMPLATE = Template(
    """# Portugal public-debt interest burden

## Coverage

- Main harmonised series: {{ main_start }}-{{ latest_year }}.
- Extended linked series begins in {{ first_year }} when AMECO data are available.
- Latest observation status: {{ latest_status }}.

## Latest observation

- Interest expenditure: **€{{ latest_interest_bn | round(2) }} billion**.
- Interest expenditure: **{{ latest_interest_ratio | round(2) }}% of GDP**.
- Gross debt: **{{ latest_debt_ratio | round(2) }}% of GDP**.
- Implicit interest rate: **{{ latest_implicit_rate | round(2) }}%**.
{% if latest_primary_balance is not none -%}
- Primary balance: **{{ latest_primary_balance | round(2) }}% of GDP**.
- Overall balance: **{{ latest_overall_balance | round(2) }}% of GDP**.
{% endif %}

## Interpretation

The nominal euro amount and the GDP ratio must be read together. The euro amount
can rise while the burden relative to GDP remains stable or falls when nominal
GDP grows or the debt ratio declines.

The implicit interest rate measures the cost of the outstanding portfolio. It
should not be interpreted as the same object as the current ten-year sovereign
yield, which affects the portfolio gradually as debt is issued or refinanced.

## Static full-pass-through sensitivities

{{ shock_table }}

These sensitivities are long-run arithmetic effects. They are not one-year
forecasts because the whole debt stock is not refinanced immediately.

## Methodological note

The main indicator is Eurostat ESA 2010 general-government interest payable
(`D41PAY`). Pre-1995 AMECO observations, when included, are labelled as a
linked series because earlier portions can draw on ESA 95 and ESA 79 accounting
frameworks. Forecast observations are not mixed with historical observations.
"""
)


def generate_report(
    frame: pd.DataFrame,
    destination: Path,
    main_start_year: int,
    shocks_bps: list[int],
) -> Path:
    """Generate a concise evidence-led Markdown report."""
    observed = frame.loc[frame["observation_status"] == "observed"].copy()
    latest = observed.sort_values("year").iloc[-1]
    shock_table = static_rate_shock_table(float(latest["debt_pct_gdp"]), shocks_bps)
    rendered = REPORT_TEMPLATE.render(
        main_start=main_start_year,
        first_year=int(frame["year"].min()),
        latest_year=int(latest["year"]),
        latest_status=str(latest["observation_status"]),
        latest_interest_bn=float(latest["interest_mio_eur"]) / 1_000.0,
        latest_interest_ratio=float(latest["interest_pct_gdp"]),
        latest_debt_ratio=float(latest["debt_pct_gdp"]),
        latest_implicit_rate=float(latest["implicit_interest_rate_pct"]),
        latest_primary_balance=(
            None
            if "primary_balance_pct_gdp" not in latest.index
            or pd.isna(latest["primary_balance_pct_gdp"])
            else float(latest["primary_balance_pct_gdp"])
        ),
        latest_overall_balance=(
            None
            if "overall_balance_pct_gdp" not in latest.index
            or pd.isna(latest["overall_balance_pct_gdp"])
            else float(latest["overall_balance_pct_gdp"])
        ),
        shock_table=shock_table.to_markdown(index=False, floatfmt=".3f"),
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")
    return destination
