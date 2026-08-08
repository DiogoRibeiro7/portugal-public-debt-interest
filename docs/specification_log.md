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
| S1 | 2026-08-02 | Frozen baseline above | Frozen, then estimated once. Estimator corrected 2026-08-08; specification unchanged. |

No other specification has been estimated. This table is appended to as work
proceeds, including specifications that are tried and discarded.

## Estimation outcome, S1

Fitted once, on the frozen specification, at commit `796c264`. Result recorded
in `reports/repricing/estimation.md`.

Originally recorded as a null: no coefficient distinguishable from zero, with
a placebo that did not load. Both statements were artefacts of estimating on
a class-major stacked panel, and neither survives the corrected monthly
estimator.

Current reading: Several associations are precisely estimated after correcting the calendar-time estimator, but the behavioural interpretation is not identified: the asymmetry test remains unresolved and the placebo warns of common-time contamination. Spread widening is +0.0214 (p = 0.0004), the
asymmetry interval [-0.016, +0.046] still covers zero, and the placebo loads
at p = 0.07. The specification was not touched in either revision.

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
| 2014 | 46.91 | **43.24** |
| 2018 | 13.79 | **12.92** |
| 2021 | **9.24** | 9.81 |

The estimated kernel does not systematically beat the benchmark. It wins at
2021 — the cut that places the whole tightening episode out of sample, and
therefore the only one where a behavioural channel has anything to do — and
loses at 2014 and 2018, by margins that are small against the error levels.
Reported in `reports/repricing/pass_through.md` as a negative result.

These figures have been revised twice since this log was first written, and the
specification was not touched either time. The original table
(52.44/55.69, 47.81/45.16, 14.24/14.66) came from a backtest that applied each
year's yield to the entire cumulative repriced share rather than to the cohort
that repriced, built its kernel at zero shock — which silences the behavioural
channel whatever response is supplied — and used the end-of-sample portfolio
state at every cut. The second revision followed from feeding the model named
after the estimate the fitted response instead of zero. Both were
implementation defects, not specification changes, which is why the count below
still reads one.

**Total specifications estimated: one.**
