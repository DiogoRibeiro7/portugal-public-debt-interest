"""Generate LaTeX table fragments from processed analytical outputs."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd

from .panel import aggregate_flag_mask
from .scenarios import static_rate_shock_table


def _escape(value: object) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
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
        ("Implicit interest rate (\\%)", "implicit_interest_rate_average_debt_pct"),
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
            "Notes: Observed Eurostat ESA 2010 Portugal rows only. The implicit rate "
            "uses average debt. Interest is general-government interest payable."
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
                _fmt(group["implicit_interest_rate_average_debt_pct"].mean(), 2),
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
            "Impl. rate",
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
            _fmt(row.implicit_interest_rate_average_debt_pct, 2),
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
            "Impl. rate (\\%)",
            "Overall bal. (\\% GDP)",
            "Primary bal. (\\% GDP)",
            "Nom. growth (\\%)",
        ],
        rows=rows,
    )
    return _write(output_dir / "recent_dynamics.tex", content)


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
            _fmt(row.implicit_interest_rate_average_debt_pct, 2),
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
            "Impl. rate (\\%)",
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


def annual_portugal_table(frame: pd.DataFrame, output_dir: Path, main_start_year: int) -> Path:
    data = _observed_portugal(frame, main_start_year)
    rows = [
        [
            _int_text(row.year),
            _fmt(row.interest_pct_gdp, 1),
            _fmt(row.interest_mio_eur, 1),
            _fmt(row.debt_pct_gdp, 1),
            _fmt(row.implicit_interest_rate_average_debt_pct, 2),
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
            r"Year & Int./GDP & Interest & Debt/GDP & Impl. rate & "
            r"Overall bal. & Primary bal. & Nom. growth \\"
        ),
        (
            r" & (\%) & (EUR m) & (\%) & (\%) & (\% GDP) & "
            r"(\% GDP) & (\%) \\"
        ),
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        (
            r"Year & Int./GDP & Interest & Debt/GDP & Impl. rate & "
            r"Overall bal. & Primary bal. & Nom. growth \\"
        ),
        (
            r" & (\%) & (EUR m) & (\%) & (\%) & (\% GDP) & "
            r"(\% GDP) & (\%) \\"
        ),
        r"\midrule",
        r"\endhead",
        *(" & ".join(row) + r" \\" for row in rows),
        r"\bottomrule",
        r"\end{longtable}",
        r"\normalsize",
    ]
    return _write(output_dir / "annual_portugal_table.tex", "\n".join(lines) + "\n")


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
        _macro("LatestImplicitRatePct", _fmt(latest["implicit_interest_rate_average_debt_pct"], 2)),
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
            "ImplicitRatePctTwentyTwentyOne",
            _fmt(year_2021["implicit_interest_rate_average_debt_pct"], 2),
        ),
        _macro("DebtPctGdpTwentyFourteen", _fmt(year_2014["debt_pct_gdp"], 2)),
        _macro("DebtPctGdpTwentyTwenty", _fmt(year_2020["debt_pct_gdp"], 2)),
        _macro("DebtPctGdpTwentyTwentyTwo", _fmt(year_2022["debt_pct_gdp"], 2)),
        _macro(
            "ImplicitRatePctTwentyTwentyTwo",
            _fmt(year_2022["implicit_interest_rate_average_debt_pct"], 2),
        ),
        _macro("CrisisMeanInterestPctGdp", _fmt(crisis["interest_pct_gdp"].mean(), 2)),
        _macro("CrisisMeanInterestEurBn", _fmt(crisis["interest_mio_eur"].mean() / 1_000.0, 2)),
        _macro("CrisisMeanDebtPctGdp", _fmt(crisis["debt_pct_gdp"].mean(), 2)),
        _macro("RecentMeanInterestPctGdp", _fmt(recent["interest_pct_gdp"].mean(), 2)),
        _macro(
            "RecentMeanImplicitRatePct",
            _fmt(recent["implicit_interest_rate_average_debt_pct"].mean(), 2),
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
            "RecentImplicitRateIncreasePp",
            _fmt(
                _num(latest["implicit_interest_rate_average_debt_pct"])
                - _num(year_2022["implicit_interest_rate_average_debt_pct"]),
                2,
            ),
        ),
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


def generate_latex_tables(
    frame: pd.DataFrame,
    output_dir: Path,
    main_start_year: int,
    shocks_bps: list[int],
    panel_frame: pd.DataFrame | None = None,
) -> list[Path]:
    """Generate every LaTeX table fragment used by the paper."""
    observed = _observed_portugal(frame, main_start_year)
    latest_year = int(observed["year"].max())
    paths = [
        headline_macros(frame, output_dir, main_start_year, shocks_bps, panel_frame),
        summary_statistics_table(frame, output_dir, main_start_year),
        regime_averages_table(frame, output_dir, main_start_year),
        recent_dynamics_table(frame, output_dir),
        static_sensitivities_table(frame, output_dir, shocks_bps),
        annual_portugal_table(frame, output_dir, main_start_year),
    ]
    if panel_frame is not None:
        paths.append(european_comparison_table(panel_frame, output_dir, latest_year))
    return paths
