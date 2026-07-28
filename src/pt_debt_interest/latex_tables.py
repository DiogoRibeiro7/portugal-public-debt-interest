"""Generate LaTeX table fragments from processed analytical outputs."""

from __future__ import annotations

import math
from pathlib import Path

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
    shock_table = static_rate_shock_table(float(latest["debt_pct_gdp"]), shocks_bps)
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
        summary_statistics_table(frame, output_dir, main_start_year),
        regime_averages_table(frame, output_dir, main_start_year),
        recent_dynamics_table(frame, output_dir),
        static_sensitivities_table(frame, output_dir, shocks_bps),
        annual_portugal_table(frame, output_dir, main_start_year),
    ]
    if panel_frame is not None:
        paths.append(european_comparison_table(panel_frame, output_dir, latest_year))
    return paths
