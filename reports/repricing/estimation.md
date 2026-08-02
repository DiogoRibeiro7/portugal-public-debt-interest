# Estimation: specification S1

Specification frozen at commit `796c264` **before** fitting, per
`docs/specification_log.md`. Nothing below was tuned toward the hypothesis, and
no alternative specification was estimated.

## Result: a well-measured null

| Term | Coefficient | HAC s.e. | t | p |
| --- | --- | --- | --- | --- |
| const | −0.0107 | 0.0181 | −0.59 | 0.56 |
| `spread_widening_pp` | **+0.0187** | 0.0148 | 1.27 | 0.20 |
| `spread_narrowing_pp` | +0.0077 | 0.0060 | 1.28 | 0.20 |
| `post_policy_break` | **−0.0213** | 0.0160 | −1.33 | 0.18 |
| `average_residual_term_years` | +0.0024 | 0.0029 | 0.82 | 0.41 |

Observations 494. R² 0.041. Newey–West standard errors, 12 monthly lags.

**No coefficient is distinguishable from zero at conventional levels.**

## The three pre-registered predictions

**1. Widening draws subscriptions — direction right, precision absent.**
The coefficient is positive, as predicted, and it is the largest in the
specification. It is not significant. A one percentage point wider spread is
associated with 1.9 percent more of the opening stock repriced per month, with
a standard error nearly as large as the estimate.

**2. Asymmetry — not detectable.**

| Quantity | Value |
| --- | --- |
| Widening minus narrowing | +0.0110 |
| 95 percent interval | [−0.0204, +0.0444] |
| Distinguishable from zero | **No** |

From 1,000 moving-block bootstrap replicates, 12-month blocks, seed 20260802.
The point estimate has the predicted sign. The interval covers zero comfortably
and is wide relative to the estimate. **This is the paper's sharpest prediction
and the data does not support it.**

**3. The policy break — direction right, precision absent.**
Negative and the second-largest term, as predicted, at p = 0.18.

## Falsification

The share of fixed-rate debt is a portfolio composition statistic a household
does not observe and has no reason to respond to. It should not load.

| Term | Coefficient | p |
| --- | --- | --- |
| `share_fixed_rate_pct` | −0.00019 | 0.86 |

It does not load, and adding it leaves the other coefficients essentially
unchanged. **Identification is not contaminated.** There is simply no
detectable signal at this precision.

## Regime stability

| Term | Pre-tightening (n=386) | Full sample (n=494) |
| --- | --- | --- |
| `spread_widening_pp` | +0.0324 | +0.0187 |
| `spread_narrowing_pp` | +0.0089 | +0.0077 |

The widening coefficient is larger before 2022 than over the full sample. Both
are imprecise, so the difference should not be read as regime dependence; it is
reported because a fixed-kernel assumption depends on it and a reader is
entitled to see it.

## What this means, stated plainly

The raw series shows an unmistakable episode: Certificados de Aforro grew 151
percent between June 2022 and May 2023, and subscriptions stopped within months
of the June 2023 terms change. That episode is real and visible without any
model.

What the frozen specification cannot do is attribute it to the competing-return
spread with any precision. Three reasons, none of which a different
specification would repair on its own:

1. **One episode.** The sample contains a single large widening event. A
   monthly regression cannot separate its timing from anything else moving at
   the same time.
2. **A proxy on the left of the spread.** The certificate's contractual
   remuneration rate is not published machine-readably, so a short-rate index
   stands in for it. Attenuation toward zero is the expected consequence, and
   its size is unknown.
3. **A bounded outcome.** The dependent variable is a one-sided lower bound on
   repricing, not the repriced amount. Months of net outflow contribute zeros
   that are not informative about subscriptions.

## What survives

The weighted-average-maturity bias result does **not** depend on any of this.
It needs the monthly average residual maturity series and the composition
split, both of which were acquired cleanly. That remains the paper's headline,
and it is unaffected by this null.

## What must not happen next

The specification is frozen. It must not be revised in search of significance.
Any variant explored from here is an in-sample variant, labelled as such and
reported alongside S1, and the count of specifications tried goes in the
manuscript.
