"""The burden paper's claims about the repricing study must match its artefacts.

The burden manuscript now cites the companion study's corrections to two of its
own assumptions. Those figures are written into its prose, and the burden paper
has no macro machinery to generate them, so they can drift the moment the
repricing pipeline is rerun. These tests are the substitute: they read the
numbers back out of the manuscript and check them against the files that
produced them.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

BURDEN_PAPER = Path("paper/portugal_public_debt_interest_report.tex")
REPRICING_PROCESSED = Path("data/processed/repricing")

pytestmark = pytest.mark.skipif(
    not REPRICING_PROCESSED.is_dir(),
    reason="repricing artefacts absent; the burden paper still builds without them",
)


def _paper_text() -> str:
    return BURDEN_PAPER.read_text(encoding="utf-8")


def _quoted(pattern: str) -> float:
    match = re.search(pattern, _paper_text())
    assert match is not None, f"burden paper no longer contains: {pattern}"
    return float(match.group(1))


def test_one_year_bias_matches_the_kernel_artefact() -> None:
    bias = pd.read_csv(REPRICING_PROCESSED / "kernels" / "kernel_bias.csv")
    expected = float(
        bias.loc[bias["horizon_years"].eq(1), "total_bias_pp"].iloc[0]
    )
    quoted = _quoted(r"by ([\d.]+) percentage points, worth roughly")
    assert quoted == pytest.approx(expected, abs=0.005)


def test_first_year_fiscal_magnitude_matches_the_artefact() -> None:
    fiscal = pd.read_csv(REPRICING_PROCESSED / "kernels" / "kernel_bias_fiscal.csv")
    expected = float(
        fiscal.loc[fiscal["horizon_years"].eq(1), "bias_interest_mio_eur"].iloc[0]
    )
    quoted = _quoted(r"roughly EUR\s*\n?([\d]+) million of interest")
    # The paper rounds to a readable figure; it must not round to a wrong one.
    assert abs(quoted - expected) < 50.0


def test_growth_path_correction_matches_the_scenario_artefact() -> None:
    paths = pd.read_csv(REPRICING_PROCESSED / "scenarios" / "pass_through_paths.csv")
    window = paths.loc[paths["shock_bps"].eq(100) & paths["horizon_years"].eq(5)]
    zero = float(
        window.loc[window["growth_path"].eq("zero_growth"), "incremental_burden_pct_gdp"].iloc[0]
    )
    central = float(
        window.loc[window["growth_path"].eq("central"), "incremental_burden_pct_gdp"].iloc[0]
    )
    text = _paper_text()
    assert f"{zero:.3f} percent of GDP" in text
    assert f"{central:.3f} percent" in text

    reduction = (1.0 - central / zero) * 100.0
    quoted = _quoted(r"roughly\s*\n?([\d]+) percent of the measured effect")
    assert quoted == pytest.approx(reduction, abs=1.0)


def test_the_shape_reversal_caveat_is_present() -> None:
    """The one-year headline must not travel without the horizon caveat."""
    bias = pd.read_csv(REPRICING_PROCESSED / "kernels" / "kernel_bias.csv")
    indexed = bias.set_index("horizon_years")["shape_bias_pp"]
    assert indexed.loc[1] > 0 and indexed.loc[3] < 0 and indexed.loc[5] < 0
    assert "turns negative at three and five years" in _paper_text()


def test_the_floating_share_claim_matches_the_panel() -> None:
    panel = pd.read_csv(REPRICING_PROCESSED / "repricing_panel.csv")
    panel["period"] = pd.to_datetime(panel["period"])
    latest = panel.loc[panel["period"].eq(panel["period"].max())]
    floating = 100.0 - float(latest["share_fixed_rate_pct"].iloc[0])
    quoted = _quoted(r"About ([\d]+) percent of the stock is floating-rate")
    assert abs(quoted - floating) < 1.0
