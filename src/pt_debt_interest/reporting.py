"""Automatic Markdown report generation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from jinja2 import Template

from .scenarios import static_rate_shock_table

REPORT_TEMPLATE = Template(
    """# Portugal public-debt interest burden

## Executive findings

- Latest observed year: **{{ latest_year }}**.
- Interest expenditure: **EUR {{ latest_interest_bn | round(2) }} billion**, or
  **{{ latest_interest_ratio | round(2) }}% of GDP**.
- Gross debt: **{{ latest_debt_ratio | round(2) }}% of GDP**.
- Implicit interest rate: **{{ latest_implicit_rate | round(2) }}%**.
{% if latest_primary_balance is not none -%}
- Primary balance: **{{ latest_primary_balance | round(2) }}% of GDP**.
- Overall balance: **{{ latest_overall_balance | round(2) }}% of GDP**.
{% endif %}

## Definitions

Interest expenditure is Eurostat ESA 2010 general-government interest payable
(`D41PAY`). The main burden measure is interest divided by nominal GDP. The
implicit interest rate uses the configured debt denominator and is not the same
object as the ten-year sovereign yield.

## Historical evolution

- Main harmonised series: **{{ main_start }}-{{ latest_year }}**.
- Extended linked series begins in **{{ first_year }}** when AMECO data are available.
- Highest observed interest burden in the generated dataset:
  **{{ peak_interest_ratio | round(2) }}% of GDP in {{ peak_interest_year }}**.

## Debt, rates, and GDP decomposition

{% if latest_nominal_growth is not none -%}
- Latest observed nominal GDP growth: **{{ latest_nominal_growth | round(2) }}%**.
{% endif -%}
{% if latest_real_growth is not none -%}
- Latest observed real GDP growth: **{{ latest_real_growth | round(2) }}%**.
{% endif -%}
{% if latest_deflator_growth is not none -%}
- Latest observed GDP-deflator growth: **{{ latest_deflator_growth | round(2) }}%**.
{% endif %}

## Fiscal-balance interpretation

The nominal euro amount and the GDP ratio must be read together. The euro amount
can rise while the burden relative to GDP remains stable or falls when nominal
GDP grows or the debt ratio declines.

## European comparison

{% if panel_latest_year is not none -%}
In **{{ panel_latest_year }}**, Portugal ranked **{{ portugal_interest_rank }}** of
**{{ comparator_count }}** non-aggregate comparator countries by interest
expenditure as a percentage of GDP.
{% else -%}
Comparator-panel metrics were not available when this report was generated.
{% endif %}

## Scenarios

### Static full-pass-through sensitivities

{{ shock_table }}

These sensitivities are long-run arithmetic effects. They are not one-year
forecasts because the whole debt stock is not refinanced immediately.

## Limitations

Pre-1995 AMECO observations, when included, are labelled as a linked series
because earlier portions can draw on ESA 95 and ESA 79 accounting frameworks.
Forecast observations are not mixed with historical observations.

## Source and revision appendix

- Latest observation status: **{{ latest_status }}**.
- Sources in generated annual table: **{{ sources }}**.
- Accounting bases in generated annual table: **{{ accounting_bases }}**.
{% if figure_names -%}
- Generated figure files: {{ figure_names }}.
{% endif %}
"""
)


def _optional_float(row: pd.Series, column: str) -> float | None:
    if column not in row.index or pd.isna(row[column]):
        return None
    return float(row[column])


def _joined_values(frame: pd.DataFrame, column: str) -> str:
    if column not in frame.columns:
        return "not available"
    values = sorted(frame[column].dropna().astype(str).unique())
    return ", ".join(values) if values else "not available"


def _panel_summary(panel_frame: pd.DataFrame | None) -> dict[str, int | None]:
    if panel_frame is None or panel_frame.empty:
        return {
            "panel_latest_year": None,
            "portugal_interest_rank": None,
            "comparator_count": None,
        }
    required = {"geo", "year", "interest_pct_gdp"}
    if not required.issubset(panel_frame.columns):
        return {
            "panel_latest_year": None,
            "portugal_interest_rank": None,
            "comparator_count": None,
        }
    panel = panel_frame.copy()
    if "observation_status" in panel.columns:
        panel = panel.loc[panel["observation_status"] == "observed"]
    if "is_aggregate" in panel.columns:
        panel = panel.loc[~panel["is_aggregate"].fillna(False).astype(bool)]
    panel = panel.dropna(subset=["interest_pct_gdp"])
    if panel.empty or "PT" not in set(panel["geo"].astype(str)):
        return {
            "panel_latest_year": None,
            "portugal_interest_rank": None,
            "comparator_count": None,
        }
    latest_year = int(panel["year"].max())
    latest = panel.loc[panel["year"].eq(latest_year)].copy()
    if "PT" not in set(latest["geo"].astype(str)):
        return {
            "panel_latest_year": None,
            "portugal_interest_rank": None,
            "comparator_count": None,
        }
    ranks = latest["interest_pct_gdp"].rank(ascending=False, method="min").astype(int)
    pt_position = latest.index[latest["geo"].astype(str).eq("PT")][0]
    return {
        "panel_latest_year": latest_year,
        "portugal_interest_rank": int(ranks.loc[pt_position]),
        "comparator_count": len(latest),
    }


def generate_report(
    frame: pd.DataFrame,
    destination: Path,
    main_start_year: int,
    shocks_bps: list[int],
    panel_frame: pd.DataFrame | None = None,
    figure_paths: list[Path] | None = None,
) -> Path:
    """Generate a concise evidence-led Markdown report."""
    observed = frame.loc[frame["observation_status"] == "observed"].copy()
    latest = observed.sort_values("year").iloc[-1]
    peak_interest = observed.sort_values("interest_pct_gdp", ascending=False).iloc[0]
    shock_table = static_rate_shock_table(float(latest["debt_pct_gdp"]), shocks_bps)
    panel_summary = _panel_summary(panel_frame)
    figure_names = (
        ", ".join(path.name for path in figure_paths if path.suffix.lower() in {".png", ".svg"})
        if figure_paths
        else ""
    )
    rendered = REPORT_TEMPLATE.render(
        main_start=main_start_year,
        first_year=int(frame["year"].min()),
        latest_year=int(latest["year"]),
        latest_status=str(latest["observation_status"]),
        latest_interest_bn=float(latest["interest_mio_eur"]) / 1_000.0,
        latest_interest_ratio=float(latest["interest_pct_gdp"]),
        latest_debt_ratio=float(latest["debt_pct_gdp"]),
        latest_implicit_rate=float(latest["implicit_interest_rate_pct"]),
        latest_primary_balance=_optional_float(latest, "primary_balance_pct_gdp"),
        latest_overall_balance=_optional_float(latest, "overall_balance_pct_gdp"),
        latest_nominal_growth=_optional_float(latest, "nominal_gdp_growth_pct"),
        latest_real_growth=_optional_float(latest, "real_gdp_growth_pct"),
        latest_deflator_growth=_optional_float(latest, "gdp_deflator_growth_pct"),
        peak_interest_ratio=float(peak_interest["interest_pct_gdp"]),
        peak_interest_year=int(peak_interest["year"]),
        sources=_joined_values(frame, "source"),
        accounting_bases=_joined_values(frame, "accounting_basis"),
        figure_names=figure_names,
        shock_table=shock_table.to_markdown(index=False, floatfmt=".3f"),
        **panel_summary,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")
    return destination
