# Specification log

Written as work proceeds, not reconstructed afterwards. The repository's claim
is reproducibility; a hidden specification search would undermine that more
thoroughly than any coding error, so every specification tried is recorded here
with its date and its reason.

## Freeze protocol

The estimation specification is frozen **before** any out-of-sample backtest is
run. The freeze is recorded below with the commit hash. Revisions after that
point do not replace the frozen specification: they are reported alongside it,
explicitly labelled as in-sample variants.

---

## S1 — frozen baseline

- **Frozen at**: commit `0b5b063`, 2026-08-02, before any estimation was run.
- **Status**: frozen. This is the specification the backtest will use.

**Outcome.** `repriced_share`, the share of the opening stock repriced in the
month. A one-sided lower bound (see `docs/repricing_data_model.md`): months of
net outflow enter as zero on the bound and are flagged, not dropped.

**Regressors.**

| Term | Reason |
| --- | --- |
| `spread_widening_pp` | The paper's directional prediction |
| `spread_narrowing_pp` | Entered separately so the two can load differently |
| `post_policy_break` | The June 2023 terms change, dated from the data |
| `average_residual_term_years` | Portfolio composition control |

**Estimator.** OLS with heteroskedasticity- and autocorrelation-consistent
(Newey–West) standard errors, 12 monthly lags.

**Why not cluster-robust.** The panel has two instrument classes. Cluster-robust
inference with two clusters is not valid, and reporting it would be worse than
not reporting it. HAC on the time dimension is the honest choice given a short
panel with many periods and few units. Stated in the manuscript.

**Why not a hazard model.** The redemption margin is not identified from net
stock. Recorded in `docs/repricing_design_revision.md`.

**Sample.** Savings certificates and Treasury certificates, monthly, from the
first month with a lagged covariate.

**Pre-registered predictions.**

1. `spread_widening_pp` loads positively: a wider spread in the certificate's
   favour draws subscriptions, repricing the stock faster.
2. Asymmetry: the widening and narrowing coefficients differ.
3. `post_policy_break` loads negatively and large: the terms change switched the
   channel off.

Prediction 1 is the reverse of the original design's hypothesis, which expected
redemptions to accelerate repricing when rates rose. That reversal is a result
and is reported as such.

---

## Specifications tried

| ID | Date | Description | Status |
| --- | --- | --- | --- |
| S1 | 2026-08-02 | Frozen baseline above | Frozen, then estimated once. Result: null. |

No other specification has been estimated. This table is appended to as work
proceeds, including specifications that are tried and discarded.

## Estimation outcome, S1

Fitted once, on the frozen specification, at commit `796c264`. Result recorded
in `reports/repricing/estimation.md`.

No coefficient is distinguishable from zero. The asymmetry interval is
[-0.0204, +0.0444] and covers zero. The placebo does not load, so the null is a
precision problem rather than a contamination problem.

**One specification has been estimated. No search was performed.** Any variant
from here is an in-sample variant, reported alongside S1 rather than replacing
it, and appended to the table above when it is run.

## Backtest, run on the frozen specification

Run at commit `55d8af3` on S1 as frozen. The specification was **not** revised
in response to the result, and no alternative was tried.

Primary cut 2021, with 2014 and 2018 as additional windows. Mean absolute error
on the effective rate, basis points:

| Cut | Estimated kernel | WAM benchmark |
| --- | --- | --- |
| 2014 | 52.44 | 55.69 |
| 2018 | 47.81 | **45.16** |
| 2021 | 14.24 | 14.66 |

The estimated kernel does not beat the benchmark. It wins narrowly at two cuts
and loses at one, by margins that are noise against the error levels. Reported
in `reports/repricing/pass_through.md` as a negative result.

**Total specifications estimated: one.**
