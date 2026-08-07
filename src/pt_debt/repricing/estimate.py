"""Estimation of the subscription-response function.

Specification S1, frozen in ``docs/specification_log.md`` before any fitting.
Nothing here may be tuned toward the hypothesis: the pre-registered predictions
are reported whether or not they hold, and the sign of the first one is the
reverse of the original design's expectation.

The outcome is a one-sided bound, so every coefficient describes the response
of the *observable lower bound* on repricing, not of gross subscriptions. That
distinction belongs in every sentence that interprets these numbers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

import numpy as np
import pandas as pd
import statsmodels.api as sm

from pt_debt_interest.exceptions import ValidationError

#: Regressors, frozen as S1.
REGRESSORS: Final[tuple[str, ...]] = (
    "spread_widening_pp",
    "spread_narrowing_pp",
    "post_policy_break",
    "average_residual_term_years",
)

OUTCOME: Final[str] = "repriced_share"

#: Newey-West lag length. Twelve months allows a full year of autocorrelation
#: in a monthly series.
HAC_LAGS: Final[int] = 12

#: Fixed so the bootstrap is reproducible.
BOOTSTRAP_SEED: Final[int] = 20260802
BOOTSTRAP_REPLICATES: Final[int] = 1000

#: Block length for the moving-block bootstrap, in months. Serial dependence in
#: a monthly flow is not removed by resampling single observations.
BLOCK_MONTHS: Final[int] = 12


@dataclass
class EstimationResult:
    """Fitted specification with its replicates and diagnostics."""

    coefficients: pd.DataFrame
    observations: int
    r_squared: float
    asymmetry: dict[str, float]
    replicates: pd.DataFrame = field(repr=False)
    specification: str = "S1"


def _design(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    missing = {OUTCOME, *REGRESSORS}.difference(panel.columns)
    if missing:
        raise ValidationError(f"estimation requires columns: {sorted(missing)}")

    usable = panel.dropna(subset=[OUTCOME, *REGRESSORS]).copy()
    if usable.empty:
        raise ValidationError("no usable rows after dropping missing covariates")

    exog = usable[list(REGRESSORS)].astype(float)
    exog = sm.add_constant(exog)
    return exog, usable[OUTCOME].astype(float)


def _moving_block_indices(
    length: int, block: int, generator: np.random.Generator
) -> np.ndarray[Any, Any]:
    """Draw a moving-block resample of a serially dependent series."""
    if length <= block:
        return generator.integers(0, length, size=length)
    starts = generator.integers(0, length - block + 1, size=(length // block) + 1)
    drawn = np.concatenate([np.arange(start, start + block) for start in starts])
    return drawn[:length]


def fit(panel: pd.DataFrame, replicates: int = BOOTSTRAP_REPLICATES) -> EstimationResult:
    """Fit specification S1 and bootstrap it."""
    exog, endog = _design(panel)
    model = sm.OLS(endog, exog).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})

    coefficients = pd.DataFrame(
        {
            "term": model.params.index,
            "coefficient": model.params.to_numpy(),
            "std_error": model.bse.to_numpy(),
            "t_stat": model.tvalues.to_numpy(),
            "p_value": model.pvalues.to_numpy(),
        }
    )

    generator = np.random.default_rng(BOOTSTRAP_SEED)
    draws: list[dict[str, float]] = []
    values = exog.to_numpy()
    outcome = endog.to_numpy()
    for _ in range(replicates):
        index = _moving_block_indices(len(outcome), BLOCK_MONTHS, generator)
        try:
            replicate = sm.OLS(outcome[index], values[index]).fit()
        except (ValueError, np.linalg.LinAlgError):  # pragma: no cover - degenerate draw
            continue
        draws.append(dict(zip(exog.columns, replicate.params, strict=True)))

    replicate_frame = pd.DataFrame(draws)

    # The asymmetry test the design turns on: do widening and narrowing load
    # differently? Reported with an interval, and reported whether or not it is
    # distinguishable from zero.
    difference = (
        replicate_frame["spread_widening_pp"] - replicate_frame["spread_narrowing_pp"]
    )
    asymmetry = {
        "point_estimate": float(
            model.params["spread_widening_pp"] - model.params["spread_narrowing_pp"]
        ),
        "lower_2_5_pct": float(difference.quantile(0.025)),
        "upper_97_5_pct": float(difference.quantile(0.975)),
        "replicates": float(len(difference)),
    }
    asymmetry["distinguishable_from_zero"] = float(
        asymmetry["lower_2_5_pct"] > 0.0 or asymmetry["upper_97_5_pct"] < 0.0
    )

    return EstimationResult(
        coefficients=coefficients,
        observations=int(model.nobs),
        r_squared=float(model.rsquared),
        asymmetry=asymmetry,
        replicates=replicate_frame,
    )


def regime_stability(panel: pd.DataFrame, split: str = "2022-01-31") -> pd.DataFrame:
    """Refit on pre-tightening data and compare.

    If the response is itself regime dependent, that is a finding, and it is
    fatal to any fixed-kernel approach including the burden paper's.
    """
    boundary = pd.Timestamp(split)
    windows = {
        "pre_tightening": panel.loc[panel["period"] < boundary],
        "full_sample": panel,
    }
    rows: list[dict[str, object]] = []
    for name, window in windows.items():
        try:
            fitted = fit(window, replicates=200)
        except ValidationError:
            continue
        for row in fitted.coefficients.itertuples():
            rows.append(
                {
                    "window": name,
                    "term": row.term,
                    "coefficient": row.coefficient,
                    "std_error": row.std_error,
                    "observations": fitted.observations,
                }
            )
    return pd.DataFrame(rows)


def placebo(panel: pd.DataFrame) -> pd.DataFrame:
    """Falsification: a covariate theory says should not drive subscriptions.

    The share of the total stock that is fixed-rate is a portfolio composition
    statistic. A household deciding whether to subscribe does not observe it and
    has no reason to respond to it. If it loads strongly, identification is
    contaminated and the paper must say so.
    """
    if "share_fixed_rate_pct" not in panel.columns:
        raise ValidationError("placebo requires share_fixed_rate_pct")
    working = panel.dropna(subset=[OUTCOME, *REGRESSORS, "share_fixed_rate_pct"]).copy()
    exog = sm.add_constant(
        working[[*REGRESSORS, "share_fixed_rate_pct"]].astype(float)
    )
    model = sm.OLS(working[OUTCOME].astype(float), exog).fit(
        cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS}
    )
    return pd.DataFrame(
        {
            "term": model.params.index,
            "coefficient": model.params.to_numpy(),
            "std_error": model.bse.to_numpy(),
            "p_value": model.pvalues.to_numpy(),
        }
    )
