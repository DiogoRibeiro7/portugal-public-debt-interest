"""Generate LaTeX table fragments from processed analytical outputs."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd

from .display import (
    SOURCE_NOTE,
    format_residual,
    publication_label,
    round_components_to_total,
)
from .interest_decomposition import (
    build_interest_burden_counterfactuals,
    build_interest_burden_decomposition,
)
from .panel import aggregate_flag_mask
from .report_context import (
    build_debt_dynamics_context,
    write_debt_dynamics_context,
)
from .scenarios import static_rate_shock_table


def _escape(value: object) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for source, replacement in replacements.items():
        text = text.replace(source, replacement)
    return text


def _fmt(value: object, digits: int = 2) -> str:
    if value is None or value is pd.NA:
        return ""
    try:
        numeric = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(numeric):
        return ""
    return f"{numeric:.{digits}f}"


def _int_text(value: object) -> str:
    return str(int(float(value)))  # type: ignore[arg-type]


def _table(
    *,
    caption: str,
    label: str,
    columns: str,
    header: list[str],
    rows: list[list[str]],
    notes: str | None = None,
    resize: bool = True,
) -> str:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        rf"\caption{{{caption}}}",
        rf"\label{{{label}}}",
    ]
    if resize:
        lines.append(r"\resizebox{\textwidth}{!}{%")
    lines.extend(
        [
            rf"\begin{{tabular}}{{{columns}}}",
            r"\toprule",
            " & ".join(header) + r" \\",
            r"\midrule",
        ]
    )
    lines.extend(" & ".join(row) + r" \\" for row in rows)
    lines.extend([r"\bottomrule", r"\end{tabular}%"])
    if resize:
        lines.append("}")
    if notes is not None:
        lines.extend([r"\smallskip", rf"\small {notes}"])
    lines.append(r"\end{table}")
    return "\n".join(lines) + "\n"


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _macro(name: str, value: str) -> str:
    return rf"\newcommand{{\{name}}}{{{value}}}"


def _year_row(frame: pd.DataFrame, year: int) -> pd.Series[Any]:
    rows = frame.loc[frame["year"].eq(year)]
    if rows.empty:
        raise ValueError(f"missing row for year {year}")
    return rows.iloc[0]


def _rank_word(rank: int) -> str:
    words = {
        1: "first",
        2: "second",
        3: "third",
        4: "fourth",
        5: "fifth",
        6: "sixth",
        7: "seventh",
        8: "eighth",
        9: "ninth",
        10: "tenth",
    }
    return words.get(rank, str(rank))


def _count_word(count: int) -> str:
    words = {
        20: "twenty",
        21: "twenty-one",
        22: "twenty-two",
        23: "twenty-three",
        24: "twenty-four",
        25: "twenty-five",
    }
    return words.get(count, str(count))


def _num(value: object) -> float:
    return float(value)  # type: ignore[arg-type]


def _observed_portugal(frame: pd.DataFrame, main_start_year: int) -> pd.DataFrame:
    data = frame.copy()
    data["year"] = pd.to_numeric(data["year"], errors="raise").astype(int)
    return data.loc[
        (data["year"] >= main_start_year) & data["observation_status"].eq("observed")
    ].sort_values("year")


def summary_statistics_table(frame: pd.DataFrame, output_dir: Path, main_start_year: int) -> Path:
    data = _observed_portugal(frame, main_start_year)
    variables = [
        ("Interest/GDP (\\%)", "interest_pct_gdp"),
        ("Interest (EUR m)", "interest_mio_eur"),
        ("Government expenditure/GDP (\\%)", "government_expenditure_pct_gdp"),
        ("Government expenditure (EUR m)", "government_expenditure_mio_eur"),
        ("Government revenue/GDP (\\%)", "government_revenue_pct_gdp"),
        ("Government revenue (EUR m)", "government_revenue_mio_eur"),
        ("Debt/GDP (\\%)", "debt_pct_gdp"),
        ("Average-debt rate (\\%)", "average_debt_interest_rate_pct"),
        ("Overall balance/GDP (\\%)", "overall_balance_pct_gdp"),
        ("Primary balance/GDP (\\%)", "primary_balance_pct_gdp"),
        ("Nominal GDP growth (\\%)", "nominal_gdp_growth_pct"),
        ("Real GDP growth (\\%)", "real_gdp_growth_pct"),
        ("GDP deflator growth (\\%)", "gdp_deflator_growth_pct"),
        ("Ten-year yield (\\%)", "ten_year_yield_pct"),
    ]
    rows: list[list[str]] = []
    for label, column in variables:
        series = pd.to_numeric(data[column], errors="coerce").dropna()
        min_index = series.idxmin()
        max_index = series.idxmax()
        rows.append(
            [
                label,
                _fmt(series.mean(), 3),
                _fmt(series.std(), 3),
                _fmt(series.min(), 3),
                _int_text(data.loc[min_index, "year"]),
                _fmt(series.max(), 3),
                _int_text(data.loc[max_index, "year"]),
            ]
        )
    content = _table(
        caption="Summary statistics, Portugal ESA 2010 sample, 1995--2025",
        label="tab:summary-statistics",
        columns="lrrrrrr",
        header=["Variable", "Mean", "Std. dev.", "Min", "Min year", "Max", "Max year"],
        rows=rows,
        notes=(
            "Notes: Observed Eurostat ESA 2010 Portugal rows only. The average-debt "
            "rate uses average debt. Interest is general-government interest payable."
        ),
    )
    return _write(output_dir / "summary_statistics.tex", content)


def regime_averages_table(frame: pd.DataFrame, output_dir: Path, main_start_year: int) -> Path:
    data = _observed_portugal(frame, main_start_year)
    grouped = data.groupby("regime", sort=False)
    rows = []
    for regime, group in grouped:
        rows.append(
            [
                _escape(regime),
                f"{_int_text(group['year'].min())}--{_int_text(group['year'].max())}",
                _fmt(group["interest_pct_gdp"].mean(), 2),
                _fmt(group["interest_mio_eur"].mean(), 2),
                _fmt(group["debt_pct_gdp"].mean(), 2),
                _fmt(group["average_debt_interest_rate_pct"].mean(), 2),
                _fmt(group["nominal_gdp_growth_pct"].mean(), 2),
                _fmt(group["primary_balance_pct_gdp"].mean(), 2),
            ]
        )
    content = _table(
        caption="Regime averages, Portugal ESA 2010 sample",
        label="tab:regimes",
        columns="lrrrrrrr",
        header=[
            "Regime",
            "Years",
            "Int./GDP",
            "Int. EUR m",
            "Debt/GDP",
            "Avg. debt rate",
            "Nom. growth",
            "Prim. bal.",
        ],
        rows=rows,
        notes=(
            "Notes: All entries are regime means. Interest in euros is reported in "
            "million euros. The ten-year yield is excluded from the printed table to "
            "keep the regime table readable; its regime means are discussed in text."
        ),
    )
    return _write(output_dir / "regime_averages.tex", content)


def recent_dynamics_table(frame: pd.DataFrame, output_dir: Path, start_year: int = 2014) -> Path:
    data = frame.loc[
        (pd.to_numeric(frame["year"], errors="coerce") >= start_year)
        & frame["observation_status"].eq("observed")
    ].copy()
    data["year"] = pd.to_numeric(data["year"], errors="raise").astype(int)
    rows = [
        [
            _int_text(row.year),
            _fmt(row.interest_pct_gdp, 1),
            _fmt(row.interest_mio_eur, 1),
            _fmt(row.debt_pct_gdp, 1),
            _fmt(row.average_debt_interest_rate_pct, 2),
            _fmt(row.overall_balance_pct_gdp, 1),
            _fmt(row.primary_balance_pct_gdp, 1),
            _fmt(row.nominal_gdp_growth_pct, 2),
        ]
        for row in data.sort_values("year").itertuples()
    ]
    content = _table(
        caption="Recent annual dynamics, Portugal",
        label="tab:recent",
        columns="rrrrrrrr",
        header=[
            "Year",
            "Int./GDP (\\%)",
            "Interest (EUR m)",
            "Debt/GDP (\\%)",
            "Avg. debt rate (\\%)",
            "Overall bal. (\\% GDP)",
            "Primary bal. (\\% GDP)",
            "Nom. growth (\\%)",
        ],
        rows=rows,
    )
    return _write(output_dir / "recent_dynamics.tex", content)


def debt_dynamics_diagnostic_table(
    frame: pd.DataFrame,
    output_dir: Path,
    start_year: int = 2020,
    end_year: int = 2025,
) -> Path:
    """Write the generated debt-dynamics diagnostic table."""
    source = frame.copy()
    source["year"] = pd.to_numeric(source["year"], errors="raise").astype(int)
    source = source.sort_values("year")
    source["previous_debt_pct_gdp"] = source["debt_pct_gdp"].shift(1)
    data = source.loc[
        source["observation_status"].eq("observed") & source["year"].between(start_year, end_year)
    ].copy()
    data["year"] = pd.to_numeric(data["year"], errors="raise").astype(int)
    # Every column below is already a percentage or a percentage point. The
    # analytical decimals are never printed, so a reader cannot mistake 1.1610
    # for a debt ratio of 1.16 percent.
    rows = [
        [
            _int_text(row.year),
            _fmt(row.interest_pct_gdp, 2),
            _fmt(row.previous_debt_pct_gdp, 2),
            _fmt(row.nominal_gdp_growth_pct, 2),
            _fmt(row.average_debt_interest_rate_pct, 2),
            _fmt(row.debt_dynamics_interest_rate_pct, 2),
            _fmt(row.interest_growth_contribution_pp, 2),
            _fmt(row.primary_balance_contribution_pp, 2),
            _fmt(row.stock_flow_adjustment_pp, 2),
            _fmt(row.observed_debt_ratio_change_pp, 2),
            _fmt(row.reconstructed_debt_ratio_change_pp, 2),
            format_residual(row.debt_dynamics_reconciliation_error_pp),
        ]
        for row in data.sort_values("year").itertuples()
    ]
    content = _table(
        caption="Debt-dynamics diagnostic table, Portugal, 2020--2025",
        label="tab:debt-dynamics-diagnostic",
        columns="rrrrrrrrrrrr",
        header=[
            "Year",
            "Interest/GDP (\\%)",
            "Lagged debt/GDP (\\%)",
            "Nominal growth (\\%)",
            "$r^{AVG}$ (\\%)",
            "$r^{DD}$ (\\%)",
            "Interest-growth (pp)",
            "Primary balance (pp)",
            "Stock-flow (pp)",
            "Observed $\\Delta d$ (pp)",
            "Rebuilt $\\Delta d$ (pp)",
            "Error (pp)",
        ],
        rows=rows,
        notes=(
            "Notes: Every column is a percentage (\\%) or a percentage point (pp), "
            "as marked in the heading; no decimal ratios are displayed. "
            "$r^{AVG}$ is the average-debt rate and $r^{DD}$ the debt-dynamics "
            "rate. The first row uses the previous debt ratio available in the "
            "processed dataset. " + SOURCE_NOTE
        ),
    )
    return _write(output_dir / "debt_dynamics_diagnostic_2020_2025.tex", content)


def european_comparison_table(panel_frame: pd.DataFrame, output_dir: Path, year: int) -> Path:
    panel = panel_frame.copy()
    panel["year"] = pd.to_numeric(panel["year"], errors="coerce")
    panel = panel.loc[
        panel["year"].eq(year)
        & panel["observation_status"].eq("observed")
        & ~aggregate_flag_mask(panel["is_aggregate"])
    ].copy()
    panel = panel.sort_values(["interest_burden_rank", "geo_name"])
    rows = [
        [
            _int_text(row.interest_burden_rank),
            _escape(row.geo_name),
            _fmt(row.interest_pct_gdp, 1),
            _fmt(row.debt_pct_gdp, 1),
            _fmt(row.average_debt_interest_rate_pct, 2),
            _fmt(row.ten_year_yield_pct, 2),
            _fmt(row.primary_balance_pct_gdp, 1),
        ]
        for row in panel.itertuples()
    ]
    content = _table(
        caption=f"European comparator panel, {year}",
        label="tab:europe-2025",
        columns="llrrrrr",
        header=[
            "Rank",
            "Country",
            "Interest/GDP (\\%)",
            "Debt/GDP (\\%)",
            "Avg. debt rate (\\%)",
            "Ten-year yield (\\%)",
            "Primary bal. (\\% GDP)",
        ],
        rows=rows,
    )
    return _write(output_dir / "european_comparison_2025.tex", content)


def static_sensitivities_table(
    frame: pd.DataFrame,
    output_dir: Path,
    shocks_bps: list[int],
) -> Path:
    observed = frame.loc[frame["observation_status"].eq("observed")].sort_values("year")
    latest = observed.iloc[-1]
    shock_table = static_rate_shock_table(_num(latest["debt_pct_gdp"]), shocks_bps)
    rows = [
        [
            _fmt(row.baseline_debt_pct_gdp, 2),
            _int_text(row.shock_bps),
            _fmt(row.shock_rate_decimal, 3),
            _fmt(row.additional_interest_pct_gdp_full_pass_through, 3),
        ]
        for row in shock_table.itertuples()
    ]
    content = _table(
        caption=(
            "Static full-pass-through sensitivities at "
            f"{_int_text(latest['year'])} debt ratio"
        ),
        label="tab:shock",
        columns="rrrr",
        header=[
            "Debt/GDP (\\%)",
            "Shock (bps)",
            "Shock rate decimal",
            "Additional interest/GDP (percentage points)",
        ],
        rows=rows,
    )
    return _write(output_dir / "static_sensitivities.tex", content)


def _decomposition_effects(row: Any) -> tuple[float, float, float]:
    """Return the displayed total and its two effects, rounded to add up."""
    total = _num(row.total_change_pp)
    effects = round_components_to_total(
        [_num(row.rate_effect_pp), _num(row.debt_exposure_effect_pp)],
        total,
        3,
    )
    return round(total, 3), effects[0], effects[1]


def interest_burden_decomposition_table(frame: pd.DataFrame, output_dir: Path) -> Path:
    decomposition = build_interest_burden_decomposition(frame)
    rows = [
        [
            _int_text(row.start_year),
            _int_text(row.end_year),
            _fmt(row.start_reconstructed_burden_pct_gdp, 2),
            _fmt(row.end_reconstructed_burden_pct_gdp, 2),
            _fmt(_decomposition_effects(row)[0], 3),
            _fmt(_decomposition_effects(row)[1], 3),
            _fmt(_decomposition_effects(row)[2], 3),
            format_residual(row.decomposition_reconciliation_error_pp),
            _escape(publication_label(row.dominant_effect)),
            _fmt(row.official_start_burden_pct_gdp, 2),
            _fmt(row.official_end_burden_pct_gdp, 2),
        ]
        for row in decomposition.itertuples()
    ]
    content = _table(
        caption="Endpoint decomposition of reconstructed interest-burden changes",
        label="tab:interest-burden-endpoints",
        columns="rrrrrrrrlrr",
        header=[
            "Start",
            "End",
            "Start burden",
            "End burden",
            "Total (pp)",
            "Financing cost (pp)",
            "Debt exposure (pp)",
            "Error (pp)",
            "Dominant",
            "Official start",
            "Official end",
        ],
        rows=rows,
        notes=(
            "Notes: Burdens are percent of GDP; effects and errors are percentage "
            "points. Effects are shown to three decimals so that the two "
            "components add to the displayed total. The decomposition uses "
            "unrounded nominal interest, debt, and GDP. " + SOURCE_NOTE
        ),
    )
    return _write(output_dir / "interest_burden_decomposition_endpoints.tex", content)


def interest_burden_counterfactuals_table(frame: pd.DataFrame, output_dir: Path) -> Path:
    counterfactuals = build_interest_burden_counterfactuals(frame)
    rows = [
        [
            _int_text(row.year),
            _escape(publication_label(row.counterfactual)),
            _fmt(_num(row.average_debt_rate) * 100.0, 2),
            _fmt(_num(row.average_debt_exposure) * 100.0, 2),
            _fmt(row.interest_burden_pct_gdp, 2),
        ]
        for row in counterfactuals.itertuples()
    ]
    content = _table(
        caption="Arithmetic interest-burden counterfactuals, 2014 and 2025",
        label="tab:interest-burden-counterfactuals",
        columns="rlrrr",
        header=[
            "Year",
            "Scenario",
            "Average-debt rate (\\%)",
            "Debt exposure (\\% of GDP)",
            "Burden (\\% of GDP)",
        ],
        rows=rows,
        notes=(
            "Notes: These are arithmetic counterfactuals, not causal estimates. "
            "Every column is a percentage, as marked in the heading. " + SOURCE_NOTE
        ),
    )
    return _write(output_dir / "interest_burden_counterfactuals.tex", content)


def annual_portugal_table(frame: pd.DataFrame, output_dir: Path, main_start_year: int) -> Path:
    data = _observed_portugal(frame, main_start_year)
    rows = [
        [
            _int_text(row.year),
            _fmt(row.interest_pct_gdp, 1),
            _fmt(row.interest_mio_eur, 1),
            _fmt(row.debt_pct_gdp, 1),
            _fmt(row.average_debt_interest_rate_pct, 2),
            _fmt(row.overall_balance_pct_gdp, 1),
            _fmt(row.primary_balance_pct_gdp, 1),
            _fmt(row.nominal_gdp_growth_pct, 2),
        ]
        for row in data.itertuples()
    ]
    lines = [
        r"\scriptsize",
        r"\begin{longtable}{rrrrrrrr}",
        r"\caption{Annual Portugal ESA 2010 analytical table}\\",
        r"\label{tab:annual-all}\\",
        r"\toprule",
        (
            r"Year & Int./GDP & Interest & Debt/GDP & Avg. debt rate & "
            r"Overall bal. & Primary bal. & Nom. growth \\"
        ),
        (
            r" & (\\%) & (EUR m) & (\\%) & (\\%) & (\\% GDP) & "
            r"(\\% GDP) & (\\%) \\"
        ),
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        (
            r"Year & Int./GDP & Interest & Debt/GDP & Avg. debt rate & "
            r"Overall bal. & Primary bal. & Nom. growth \\"
        ),
        (
            r" & (\\%) & (EUR m) & (\\%) & (\\%) & (\\% GDP) & "
            r"(\\% GDP) & (\\%) \\"
        ),
        r"\midrule",
        r"\endhead",
        *(" & ".join(row) + r" \\" for row in rows),
        r"\bottomrule",
        r"\end{longtable}",
        r"\normalsize",
    ]
    return _write(output_dir / "annual_portugal_table.tex", "\n".join(lines) + "\n")


_DEBT_DYNAMICS_YEAR_WORDS = {
    "2020": "TwentyTwenty",
    "2022": "TwentyTwentyTwo",
    "2023": "TwentyTwentyThree",
}


def _scientific(value: float) -> str:
    """Render a residual without implying false precision or a negative zero."""
    magnitude = abs(float(value))
    if magnitude == 0.0:
        return "0"
    if magnitude < 1e-9:
        return "$< 10^{-9}$"
    return f"{magnitude:.2e}"


def _debt_dynamics_macros(frame: pd.DataFrame) -> list[str]:
    """Build report macros from the canonical debt-dynamics context."""
    context = build_debt_dynamics_context(frame)
    macros: list[str] = []
    for year, word in _DEBT_DYNAMICS_YEAR_WORDS.items():
        values = context["focus_years"][year]
        macros.append(
            _macro(
                f"DebtDynamicsInterestGrowth{word}Pp",
                _fmt(values["interest_growth_contribution_pp"], 2),
            )
        )
        macros.append(
            _macro(
                f"DebtStabilisingPb{word}PctGdp",
                _fmt(
                    values["debt_stabilising_primary_balance_before_sfa_pct_gdp"], 2
                ),
            )
        )
        macros.append(
            _macro(
                f"DebtDynamicsRate{word}Pct",
                _fmt(values["debt_dynamics_interest_rate_pct"], 2),
            )
        )
    stock_flow = context["stock_flow_adjustment"]
    macros.append(_macro("StockFlowMinPp", _fmt(stock_flow["minimum_pp"], 2)))
    macros.append(_macro("StockFlowMinYear", str(stock_flow["minimum_year"])))
    macros.append(_macro("StockFlowMaxPp", _fmt(stock_flow["maximum_pp"], 2)))
    macros.append(_macro("StockFlowMaxYear", str(stock_flow["maximum_year"])))
    macros.append(
        _macro(
            "DebtDynamicsMaxReconciliationErrorPp",
            _scientific(context["reconciliation"]["maximum_absolute_error_pp"]),
        )
    )
    return macros


def headline_macros(
    frame: pd.DataFrame,
    output_dir: Path,
    main_start_year: int,
    shocks_bps: list[int],
    panel_frame: pd.DataFrame | None = None,
) -> Path:
    """Write LaTeX macros for recurring paper headline values."""
    data = _observed_portugal(frame, main_start_year)
    latest_year = int(data["year"].max())
    first = _year_row(data, main_start_year)
    latest = _year_row(data, latest_year)
    year_2014 = _year_row(data, 2014)
    year_2019 = _year_row(data, 2019)
    year_2020 = _year_row(data, 2020)
    year_2021 = _year_row(data, 2021)
    year_2022 = _year_row(data, 2022)
    year_2023 = _year_row(data, 2023)
    summary_interest = pd.to_numeric(data["interest_pct_gdp"], errors="coerce")
    summary_interest_mio = pd.to_numeric(data["interest_mio_eur"], errors="coerce")
    summary_debt = pd.to_numeric(data["debt_pct_gdp"], errors="coerce")
    crisis = data.loc[data["regime"].eq("Sovereign-debt crisis and adjustment")]
    recent = data.loc[data["regime"].eq("Inflation and monetary tightening")]
    shock_table = static_rate_shock_table(_num(latest["debt_pct_gdp"]), shocks_bps)
    shock_by_bps = {int(_num(row.shock_bps)): row for row in shock_table.itertuples()}
    decomposition = build_interest_burden_decomposition(frame)
    interval_2014_2025 = decomposition.loc[
        decomposition["start_year"].eq(2014) & decomposition["end_year"].eq(2025)
    ].iloc[0]
    interval_1996_2025 = decomposition.loc[
        decomposition["start_year"].eq(1996) & decomposition["end_year"].eq(2025)
    ].iloc[0]
    panel_rank = ""
    panel_count = ""
    if panel_frame is not None:
        panel = panel_frame.copy()
        panel["year"] = pd.to_numeric(panel["year"], errors="coerce")
        panel = panel.loc[
            panel["year"].eq(latest_year)
            & panel["observation_status"].eq("observed")
            & ~aggregate_flag_mask(panel["is_aggregate"])
        ]
        portugal = panel.loc[panel["geo"].eq("PT")]
        if not portugal.empty:
            rank = int(_num(portugal.iloc[0]["interest_burden_rank"]))
            panel_rank = _rank_word(rank)
            panel_count = _count_word(len(panel))

    macros = [
        _macro("MainStartYear", _int_text(main_start_year)),
        _macro("LatestYear", _int_text(latest_year)),
        _macro("MainSampleObservations", _int_text(len(data))),
        _macro("InitialInterestPctGdp", _fmt(first["interest_pct_gdp"], 2)),
        _macro("InitialInterestEurBn", _fmt(_num(first["interest_mio_eur"]) / 1_000.0, 2)),
        _macro("LatestInterestPctGdp", _fmt(latest["interest_pct_gdp"], 2)),
        _macro("LatestInterestEurBn", _fmt(_num(latest["interest_mio_eur"]) / 1_000.0, 2)),
        _macro(
            "LatestGovernmentExpenditureEurBn",
            _fmt(_num(latest["government_expenditure_mio_eur"]) / 1_000.0, 2),
        ),
        _macro(
            "LatestGovernmentExpenditurePctGdp",
            _fmt(latest["government_expenditure_pct_gdp"], 2),
        ),
        _macro(
            "LatestGovernmentRevenueEurBn",
            _fmt(_num(latest["government_revenue_mio_eur"]) / 1_000.0, 2),
        ),
        _macro("LatestGovernmentRevenuePctGdp", _fmt(latest["government_revenue_pct_gdp"], 2)),
        _macro("LatestDebtPctGdp", _fmt(latest["debt_pct_gdp"], 2)),
        _macro("LatestAverageDebtRatePct", _fmt(latest["average_debt_interest_rate_pct"], 2)),
        _macro("LatestTenYearYieldPct", _fmt(latest["ten_year_yield_pct"], 2)),
        _macro("LatestOverallBalancePctGdp", _fmt(latest["overall_balance_pct_gdp"], 2)),
        _macro("LatestPrimaryBalancePctGdp", _fmt(latest["primary_balance_pct_gdp"], 2)),
        _macro(
            "InterestBurdenDeclinePp",
            _fmt(_num(first["interest_pct_gdp"]) - _num(latest["interest_pct_gdp"]), 2),
        ),
        _macro(
            "InterestBillIncreaseEurBn",
            _fmt(
                (_num(latest["interest_mio_eur"]) - _num(first["interest_mio_eur"]))
                / 1_000.0,
                2,
            ),
        ),
        _macro("InterestMeanPctGdp", _fmt(summary_interest.mean(), 2)),
        _macro("InterestMinPctGdp", _fmt(summary_interest.min(), 2)),
        _macro("InterestMaxPctGdp", _fmt(summary_interest.max(), 2)),
        _macro("InterestBillMeanEurBn", _fmt(summary_interest_mio.mean() / 1_000.0, 2)),
        _macro("InterestBillMaxEurBn", _fmt(summary_interest_mio.max() / 1_000.0, 2)),
        _macro("InterestBillMaxYear", _int_text(data.loc[summary_interest_mio.idxmax(), "year"])),
        _macro("DebtMeanPctGdp", _fmt(summary_debt.mean(), 2)),
        _macro("DebtMinPctGdp", _fmt(summary_debt.min(), 2)),
        _macro("DebtMinYear", _int_text(data.loc[summary_debt.idxmin(), "year"])),
        _macro("DebtMaxPctGdp", _fmt(summary_debt.max(), 2)),
        _macro("DebtMaxYear", _int_text(data.loc[summary_debt.idxmax(), "year"])),
        _macro("InterestPctGdpTwentyFourteen", _fmt(year_2014["interest_pct_gdp"], 2)),
        _macro("InterestPctGdpTwentyNineteen", _fmt(year_2019["interest_pct_gdp"], 2)),
        _macro("InterestPctGdpTwentyTwentyOne", _fmt(year_2021["interest_pct_gdp"], 2)),
        _macro(
            "AverageDebtRatePctTwentyTwentyOne",
            _fmt(year_2021["average_debt_interest_rate_pct"], 2),
        ),
        _macro("DebtPctGdpTwentyFourteen", _fmt(year_2014["debt_pct_gdp"], 2)),
        _macro("DebtPctGdpTwentyTwenty", _fmt(year_2020["debt_pct_gdp"], 2)),
        _macro("DebtPctGdpTwentyTwentyTwo", _fmt(year_2022["debt_pct_gdp"], 2)),
        _macro(
            "AverageDebtRatePctTwentyTwentyTwo",
            _fmt(year_2022["average_debt_interest_rate_pct"], 2),
        ),
        _macro("CrisisMeanInterestPctGdp", _fmt(crisis["interest_pct_gdp"].mean(), 2)),
        _macro("CrisisMeanInterestEurBn", _fmt(crisis["interest_mio_eur"].mean() / 1_000.0, 2)),
        _macro("CrisisMeanDebtPctGdp", _fmt(crisis["debt_pct_gdp"].mean(), 2)),
        _macro("RecentMeanInterestPctGdp", _fmt(recent["interest_pct_gdp"].mean(), 2)),
        _macro(
            "RecentMeanAverageDebtRatePct",
            _fmt(recent["average_debt_interest_rate_pct"].mean(), 2),
        ),
        _macro("RecentMeanNominalGrowthPct", _fmt(recent["nominal_gdp_growth_pct"].mean(), 2)),
        _macro("NominalGdpGrowthTwentyTwentyTwo", _fmt(year_2022["nominal_gdp_growth_pct"], 2)),
        _macro("RealGdpGrowthTwentyTwentyTwo", _fmt(year_2022["real_gdp_growth_pct"], 2)),
        _macro("GdpDeflatorGrowthTwentyTwentyTwo", _fmt(year_2022["gdp_deflator_growth_pct"], 2)),
        _macro("NominalGdpGrowthTwentyTwentyThree", _fmt(year_2023["nominal_gdp_growth_pct"], 2)),
        _macro("GdpDeflatorGrowthTwentyTwentyThree", _fmt(year_2023["gdp_deflator_growth_pct"], 2)),
        _macro(
            "RecentDebtDeclinePp",
            _fmt(_num(year_2022["debt_pct_gdp"]) - _num(latest["debt_pct_gdp"]), 2),
        ),
        _macro(
            "RecentInterestBillIncreaseEurBn",
            _fmt(
                (_num(latest["interest_mio_eur"]) - _num(year_2022["interest_mio_eur"]))
                / 1_000.0,
                2,
            ),
        ),
        _macro(
            "RecentAverageDebtRateIncreasePp",
            _fmt(
                _num(latest["average_debt_interest_rate_pct"])
                - _num(year_2022["average_debt_interest_rate_pct"]),
                2,
            ),
        ),
        _macro(
            "DecompTotalTwentyFourteenToLatestPp",
            _fmt(interval_2014_2025.total_change_pp, 2),
        ),
        _macro(
            "DecompRateTwentyFourteenToLatestPp",
            _fmt(interval_2014_2025.rate_effect_pp, 2),
        ),
        _macro(
            "DecompExposureTwentyFourteenToLatestPp",
            _fmt(interval_2014_2025.debt_exposure_effect_pp, 2),
        ),
        _macro(
            "DecompErrorTwentyFourteenToLatestPp",
            format_residual(interval_2014_2025.decomposition_reconciliation_error_pp),
        ),
        _macro(
            "DecompDominantTwentyFourteenToLatest",
            _escape(interval_2014_2025.dominant_effect),
        ),
        _macro(
            "DecompTotalNineteenNinetySixToLatestPp",
            _fmt(interval_1996_2025.total_change_pp, 2),
        ),
        _macro(
            "DecompRateNineteenNinetySixToLatestPp",
            _fmt(interval_1996_2025.rate_effect_pp, 2),
        ),
        _macro(
            "DecompExposureNineteenNinetySixToLatestPp",
            _fmt(interval_1996_2025.debt_exposure_effect_pp, 2),
        ),
        _macro(
            "DecompErrorNineteenNinetySixToLatestPp",
            format_residual(interval_1996_2025.decomposition_reconciliation_error_pp),
        ),
        _macro(
            "DecompDominantNineteenNinetySixToLatest",
            _escape(interval_1996_2025.dominant_effect),
        ),
        *_debt_dynamics_macros(frame),
        _macro("PortugalComparatorRankWord", panel_rank),
        _macro("ComparatorCountryCountWord", panel_count),
        _macro(
            "ShockFiftyAdditionalPp",
            _fmt(shock_by_bps[50].additional_interest_pct_gdp_full_pass_through, 3),
        ),
        _macro(
            "ShockHundredAdditionalPp",
            _fmt(shock_by_bps[100].additional_interest_pct_gdp_full_pass_through, 3),
        ),
        _macro(
            "ShockTwoHundredAdditionalPp",
            _fmt(shock_by_bps[200].additional_interest_pct_gdp_full_pass_through, 3),
        ),
        _macro(
            "ShockHundredApproxPp",
            _fmt(shock_by_bps[100].additional_interest_pct_gdp_full_pass_through, 2),
        ),
    ]
    return _write(output_dir / "paper_headlines.tex", "\n".join(macros) + "\n")


def refinancing_assumptions_table(
    assumptions: pd.DataFrame,
    output_dir: Path,
    main_scenario: str,
) -> Path:
    """Write the refinancing assumptions so the reader can audit the model."""
    per_scenario = (
        assumptions.sort_values(["scenario", "horizon_year"])
        .groupby("scenario", as_index=False)
        .first()
    )
    rows = []
    for row in per_scenario.itertuples():
        marker = " (main)" if str(row.scenario) == main_scenario else ""
        rows.append(
            [
                _escape(str(row.scenario).capitalize() + marker),
                _fmt(_num(row.annual_refinancing_share) * 100.0, 2),
                _fmt(row.implied_average_maturity_years, 1),
                _int_text(row.horizon_years),
                _fmt(row.initial_average_portfolio_rate_pct, 2),
                _fmt(row.baseline_new_issuance_rate_pct, 2),
                _fmt(row.debt_pct_gdp, 2),
                _escape(str(row.debt_ratio_path)),
            ]
        )
    content = _table(
        caption="Stylised refinancing scenario assumptions",
        label="tab:refinancing-assumptions",
        columns="lrrrrrrl",
        header=[
            "Scenario",
            "Annual repricing (\\%)",
            "Implied maturity (years)",
            "Horizon (years)",
            "Initial portfolio rate (\\%)",
            "Baseline issuance rate (\\%)",
            "Debt (\\% of GDP)",
            "Debt and GDP paths",
        ],
        rows=rows,
        notes=(
            "Notes: A stylised cohort model, not a forecast. The central "
            "scenario applies a uniform annual repricing share consistent with "
            "the published average maturity of the debt stock of 7.2 years in "
            "2024 (IGCP, Annual Report 2024, page 22); the uniform shape is an "
            "approximation applied here, not IGCP's redemption schedule. The "
            "slow and fast scenarios carry no external source and exist to "
            "bracket the assumption. The debt ratio and nominal GDP are held "
            "fixed across the horizon. " + SOURCE_NOTE
        ),
    )
    return _write(output_dir / "refinancing_assumptions.tex", content)


def generate_latex_tables(
    frame: pd.DataFrame,
    output_dir: Path,
    main_start_year: int,
    shocks_bps: list[int],
    panel_frame: pd.DataFrame | None = None,
    context_dir: Path | None = None,
    refinancing_assumptions: pd.DataFrame | None = None,
    refinancing_main_scenario: str = "central",
) -> list[Path]:
    """Generate every LaTeX table fragment and numeric context used by the paper."""
    observed = _observed_portugal(frame, main_start_year)
    latest_year = int(observed["year"].max())
    generated_dir = context_dir if context_dir is not None else output_dir.parent / "generated"
    paths = [
        write_debt_dynamics_context(frame, generated_dir),
        headline_macros(frame, output_dir, main_start_year, shocks_bps, panel_frame),
        summary_statistics_table(frame, output_dir, main_start_year),
        regime_averages_table(frame, output_dir, main_start_year),
        recent_dynamics_table(frame, output_dir),
        debt_dynamics_diagnostic_table(frame, output_dir),
        interest_burden_decomposition_table(frame, output_dir),
        interest_burden_counterfactuals_table(frame, output_dir),
        static_sensitivities_table(frame, output_dir, shocks_bps),
        annual_portugal_table(frame, output_dir, main_start_year),
    ]
    if panel_frame is not None:
        paths.append(european_comparison_table(panel_frame, output_dir, latest_year))
    if refinancing_assumptions is not None and not refinancing_assumptions.empty:
        paths.append(
            refinancing_assumptions_table(
                refinancing_assumptions, output_dir, refinancing_main_scenario
            )
        )
    return paths
