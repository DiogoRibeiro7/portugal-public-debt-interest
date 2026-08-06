"""The burden paper must not depend on unsupported companion-paper point claims."""

from __future__ import annotations

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


def test_burden_paper_does_not_import_repricing_point_claims() -> None:
    text = _paper_text()
    assert "10.90 percentage points" not in text
    assert "EUR\n300 million" not in text
    assert "EUR 300 million" not in text
    assert "preliminary sensitivity analysis" in text


def test_growth_path_correction_matches_the_scenario_artefact() -> None:
    paths = pd.read_csv(REPRICING_PROCESSED / "scenarios" / "pass_through_paths.csv")
    assert not paths.empty
    text = _paper_text()
    assert "denominator sensitivity, not a forecast" in text
    assert "mechanically on the chosen growth\npath" in text


def test_the_shape_reversal_caveat_is_present() -> None:
    """The repricing caveat must not travel as a one-year headline."""
    bias = pd.read_csv(REPRICING_PROCESSED / "kernels" / "kernel_bias.csv")
    indexed = bias.set_index("horizon_years")["shape_bias_pp"]
    assert indexed.loc[1] > 0 and indexed.loc[3] < 0 and indexed.loc[5] < 0
    assert "not lower bounds established from mutually exclusive" in _paper_text()


def test_the_floating_share_claim_matches_the_panel() -> None:
    panel = pd.read_csv(REPRICING_PROCESSED / "repricing_panel.csv")
    panel["period"] = pd.to_datetime(panel["period"])
    latest = panel.loc[panel["period"].eq(panel["period"].max())]
    floating = 100.0 - float(latest["share_fixed_rate_pct"].iloc[0])
    assert floating > 0.0
    assert "some liabilities can reset without redemption" in _paper_text()
