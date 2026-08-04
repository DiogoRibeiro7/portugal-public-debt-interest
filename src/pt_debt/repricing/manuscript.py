"""Generate every number the repricing manuscript quotes.

No value is typed into the LaTeX source. The manuscript reads macros emitted
here from the processed artefacts, and ``verify_manuscript_values`` fails the
build if a hand-typed number appears where a macro should be.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

import pandas as pd

from pt_debt.repricing.estimate import OUTCOME, REGRESSORS
from pt_debt_interest.exceptions import ValidationError

#: LaTeX control sequences cannot contain digits, so horizons and cut years
#: are spelled out in macro names.
WORDS: Final[dict[int, str]] = {
    1: "One", 3: "Three", 5: "Five", 10: "Ten",
    2014: "Fourteen", 2018: "Eighteen", 2021: "TwentyOne",
}

MACRO_FILENAME: Final[str] = "generated_values.tex"


def _macro(name: str, value: object) -> str:
    return rf"\newcommand{{\{name}}}{{{value}}}"


def _row(frame: pd.DataFrame, column: str, value: str | int) -> pd.Series:
    match = frame.loc[frame[column].eq(value)]
    if match.empty:
        raise ValidationError(f"no row with {column} == {value!r}")
    return match.iloc[0]


def build_macros(processed_dir: Path, panel_path: Path) -> list[str]:
    """Read the artefacts and emit the manuscript's macros."""
    bias = pd.read_csv(processed_dir / "kernels" / "kernel_bias.csv")
    fiscal = pd.read_csv(processed_dir / "kernels" / "kernel_bias_fiscal.csv")
    coefficients = pd.read_csv(processed_dir / "estimates" / "s1_coefficients.csv")
    replicates = pd.read_csv(
        processed_dir / "estimates" / "s1_bootstrap_replicates.csv"
    )
    placebo = pd.read_csv(processed_dir / "estimates" / "s1_placebo.csv")
    backtest = pd.read_csv(processed_dir / "scenarios" / "backtest_summary.csv")
    paths = pd.read_csv(processed_dir / "scenarios" / "pass_through_paths.csv")
    panel = pd.read_csv(panel_path)
    panel["period"] = pd.to_datetime(panel["period"])

    macros: list[str] = []

    # --- portfolio state
    latest = panel.loc[panel["period"].eq(panel["period"].max())]
    fixed_share = float(latest["share_fixed_rate_pct"].iloc[0])
    macros += [
        _macro("PortfolioAsOf", latest["period"].max().strftime("%B %Y")),
        _macro(
            "AverageResidualMaturity",
            f"{float(latest['average_residual_term_years'].iloc[0]):.2f}",
        ),
        _macro("FixedRateSharePct", f"{fixed_share:.1f}"),
        _macro("FloatingSharePct", f"{100.0 - fixed_share:.1f}"),
        _macro("RetailSharePct", f"{float(latest['share_of_total_debt'].sum()) * 100.0:.1f}"),
    ]

    # --- the retail episode, from the raw panel
    retail = (
        panel.loc[panel["instrument_class"].eq("savings_certificates")]
        .set_index("period")["outstanding_mio_eur"]
        .sort_index()
    )
    start, end = retail.loc["2022-06-30"], retail.loc["2023-05-31"]
    macros += [
        _macro("RetailStockStartBn", f"{start / 1000.0:.1f}"),
        _macro("RetailStockPeakBn", f"{end / 1000.0:.1f}"),
        _macro("RetailGrowthPct", f"{(end / start - 1.0) * 100.0:.0f}"),
        _macro("RetailPeakInflowMio", f"{retail.diff().max():,.0f}"),
    ]

    # --- kernel bias
    for horizon in (1, 3, 5, 10):
        row = _row(bias, "horizon_years", horizon)
        macros += [
            _macro(f"BiasTotalH{WORDS[horizon]}", f"{row['total_bias_pp']:.2f}"),
            _macro(f"BiasShapeH{WORDS[horizon]}", f"{row['shape_bias_pp']:.2f}"),
            _macro(f"BiasBehaviourH{WORDS[horizon]}", f"{row['behaviour_bias_pp']:.2f}"),
            _macro(f"WamShareH{WORDS[horizon]}", f"{row['wam_implied_share']:.4f}"),
            _macro(f"EstimatedShareH{WORDS[horizon]}", f"{row['estimated_share']:.4f}"),
        ]
    fiscal_one = _row(fiscal, "horizon_years", 1)
    macros += [
        _macro("BiasInterestPctGdpHOne", f"{fiscal_one['bias_interest_pct_gdp']:.3f}"),
        _macro("BiasInterestMioHOne", f"{fiscal_one['bias_interest_mio_eur']:,.0f}"),
    ]

    # --- estimation
    widening = _row(coefficients, "term", "spread_widening_pp")
    macros += [
        _macro("SpreadWideningCoef", f"{widening['coefficient']:+.4f}"),
        _macro("SpreadWideningSe", f"{widening['std_error']:.4f}"),
        _macro("SpreadWideningP", f"{widening['p_value']:.2f}"),
        _macro(
            "EstimationObservations",
            f"{len(panel.dropna(subset=[OUTCOME, *REGRESSORS])):,}",
        ),
    ]
    difference = replicates["spread_widening_pp"] - replicates["spread_narrowing_pp"]
    macros += [
        _macro("AsymmetryPoint", f"{difference.mean():+.3f}"),
        _macro("AsymmetryLow", f"{difference.quantile(0.025):+.3f}"),
        _macro("AsymmetryHigh", f"{difference.quantile(0.975):+.3f}"),
        _macro("BootstrapReplicates", f"{len(difference):,}"),
    ]
    placebo_row = _row(placebo, "term", "share_fixed_rate_pct")
    macros += [
        _macro("PlaceboCoef", f"{placebo_row['coefficient']:+.5f}"),
        _macro("PlaceboP", f"{placebo_row['p_value']:.2f}"),
    ]

    # --- backtest
    for cut in (2014, 2018, 2021):
        window = backtest.loc[backtest["cut_year"].eq(cut)]
        for model, label in (
            ("estimated_kernel", "Est"),
            ("wam_benchmark", "Wam"),
        ):
            value = _row(window, "model", model)["mean_abs_error_bps"]
            macros.append(_macro(f"Backtest{label}{WORDS[cut]}", f"{value:.2f}"))

    # --- growth-path correction
    at_five = paths.loc[paths["shock_bps"].eq(100) & paths["horizon_years"].eq(5)]
    zero = _row(at_five, "growth_path", "zero_growth")["incremental_burden_pct_gdp"]
    central = _row(at_five, "growth_path", "central")["incremental_burden_pct_gdp"]
    macros += [
        _macro("ShockBurdenZeroGrowth", f"{zero:.3f}"),
        _macro("ShockBurdenCentralGrowth", f"{central:.3f}"),
        _macro("GrowthCorrectionPct", f"{(1.0 - central / zero) * 100.0:.0f}"),
    ]
    return macros


def write_macros(processed_dir: Path, panel_path: Path, output_dir: Path) -> Path:
    """Write the generated macros beside the manuscript."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / MACRO_FILENAME
    path.write_text("\n".join(build_macros(processed_dir, panel_path)) + "\n", encoding="utf-8")
    return path


def verify_manuscript_values(tex_path: Path) -> list[str]:
    """Return hand-typed numbers found in the manuscript body.

    Every quantity must arrive through a macro. Structural numbers -- font
    sizes, figure widths, years in prose -- are excluded, so what remains is a
    result typed by hand.
    """
    if not tex_path.is_file():
        raise ValidationError(f"manuscript not found: {tex_path}")
    source = tex_path.read_text(encoding="utf-8")
    body = source.split(r"\begin{document}")[-1].split(r"\begin{thebibliography}")[0]
    body = re.sub(r"\\includegraphics\[[^\]]*\]\{[^}]*\}", " ", body)
    body = re.sub(r"\\(?:label|ref|cite|input)\{[^}]*\}", " ", body)
    body = re.sub(r"%[^\n]*", " ", body)
    # Four-digit years are prose, not results.
    body = re.sub(r"(?<!\d)(19|20)\d{2}(?!\d)", " ", body)
    return re.findall(r"(?<![\w.])-?\d+\.\d+", body)


def undefined_macros(tex_path: Path, macro_path: Path) -> list[str]:
    """Return generated-style macros the manuscript calls but nothing defines.

    A macro that vanishes from the artefacts -- a horizon dropped, a cut date
    renamed -- would otherwise surface as a LaTeX error at compile time, or
    worse, as a silently empty number.
    """
    defined = set(
        re.findall(r"\\newcommand\{\\(\w+)\}", macro_path.read_text(encoding="utf-8"))
    )
    body = tex_path.read_text(encoding="utf-8").split(r"\begin{document}")[-1]
    used = set(re.findall(r"\\([A-Z]\w+)", body))
    return sorted(name for name in used - defined if not name.isupper())
