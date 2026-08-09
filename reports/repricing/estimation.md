# Estimation: specification S1

Specification frozen at commit `796c264` **before** fitting, per
`docs/specification_log.md`. Nothing below was tuned toward the hypothesis, and
no alternative specification was estimated.

## Result: precise associations, unidentified behaviour

| Term | Coefficient | HAC s.e. | t | p |
| --- | --- | --- | --- | --- |
| const | −0.0130 | 0.0056 | −2.31 | 0.02 |
| `spread_widening_pp` | **+0.0214** | 0.0061 | 3.51 | 0.0004 |
| `spread_narrowing_pp` | −0.0007 | 0.0016 | −0.44 | 0.66 |
| `post_policy_break` | **−0.0250** | 0.0079 | −3.16 | 0.002 |
| `average_residual_term_years` | +0.0031 | 0.0010 | 3.25 | 0.001 |

Observations 304. R² 0.343. Newey-West standard errors, 12 monthly lags.

These numbers changed when the estimator was corrected. The fit previously ran
on the stacked class-month panel, which is sorted by instrument class then
period: every month of one class preceded every month of the other, so calendar
time jumped backwards at the boundary. A twelve-month bootstrap block could
straddle a fifteen-year gap and the Newey-West lag structure did not correspond
to month-to-month dependence. Each class-month also carried equal weight
regardless of the euros behind it. Estimation now runs on the two retail
classes aggregated to one euro-weighted monthly series. The previous table read
+0.0187 (se 0.0148, p = 0.20) on 494 rows with R² 0.041, and concluded that no
coefficient was distinguishable from zero.

The spread-widening coefficient is now statistically detectable, but it is
still not identified. The falsification test no longer passes cleanly, and the
left-hand-side variable is a positive outstanding-value change that can include
capitalised interest as well as new principal. The coefficient is therefore
reported as a descriptive association, not as a structural household response.
Nothing downstream treats it as identified: the kernel's central behavioural
effect stays at zero.

## The three pre-registered predictions

1. Widening draws subscriptions: direction right, and now precise.
The coefficient is positive, as predicted, and it is the largest in the
specification. A one percentage point wider spread is associated with 2.1
percent more of the opening stock repriced per month (se 0.6). Precision is no
longer the binding problem; identification is.

2. Asymmetry: not detectable.

| Quantity | Value |
| --- | --- |
| Widening minus narrowing | +0.0110 |
| 95 percent interval | [−0.0204, +0.0444] |
| Distinguishable from zero | **No** |

From 1,000 moving-block bootstrap replicates, 12-month blocks, seed 20260802.
The point estimate has the predicted sign. The interval covers zero comfortably
and is wide relative to the estimate. This is the paper's sharpest prediction,
and the data does not support it.

3. The policy break: direction right, and precise.
Negative and the second-largest term, as predicted, at p = 0.002.

## Falsification

The share of fixed-rate debt is a portfolio composition statistic a household
does not observe and has no reason to respond to. It should not load.

| Term | Coefficient | p |
| --- | --- | --- |
| `share_fixed_rate_pct` | −0.00051 | 0.07 |

It now loads, marginally, and that is the most important number in this report.
Under the previous stacked-panel estimator it sat at −0.00019 with p = 0.86 and
was read as reassurance. On the corrected monthly series it is close enough to
conventional significance to be a warning instead.

A statistic no household observes should carry no weight. That it does, at the
same time as the main coefficient became significant, is the signature of
common time variation the specification cannot separate from the spread. Both
terms are picking up something that moves with the calendar.

This is why the spread coefficient is reported as descriptive rather than
identified, and why the kernel's central behavioural effect stays at zero. A
placebo cannot validate identification in any case; it can only fail to reject
one contamination channel. Here it does not even do that.

## Regime stability

| Term | Pre-tightening (n=250) | Full sample (n=304) |
| --- | --- | --- |
| `spread_widening_pp` | +0.0237 | +0.0214 |
| `spread_narrowing_pp` | +0.0003 | −0.0007 |

The widening coefficient is slightly larger before 2022 than over the full
sample, and the gap is much smaller than the stacked-panel fit suggested
(+0.0324 against +0.0187). The difference should not be read as regime
dependence; it is reported because a fixed-kernel assumption depends on it and
a reader is entitled to see it.

## What this means, stated plainly

The raw series shows an unmistakable episode: Certificados de Aforro grew 151
percent between June 2022 and May 2023, and subscriptions stopped within months
of the June 2023 terms change. That episode is real and visible without any
model.

What the frozen specification cannot do is attribute it structurally to the
competing-return spread. The relevant coefficients are precise in the corrected
monthly estimator, but precision does not separate household behaviour from
common time variation or accounting effects. Three reasons, none of which a
different specification would repair on its own:

1. **One episode.** The sample contains a single large widening event. A
   monthly regression cannot separate its timing from anything else moving at
   the same time.
2. **A proxy on the left of the spread.** The certificate's contractual
   remuneration rate is not published machine-readably, so a short-rate index
   stands in for it. Attenuation toward zero is the expected consequence, and
   its size is unknown.
3. **A stock-value outcome.** The dependent variable is the positive part of
   outstanding-value change over opening stock. It can move because of
   capitalised interest as well as principal flows, and net-outflow months do
   not reveal the gross subscription and redemption flows underneath.

## What survives

The scenario-minus-WAM result does not depend on any structural interpretation
of the retail coefficient. It needs the monthly average residual maturity
series and the composition split, both of which were acquired cleanly. That
remains the paper's headline, and it is unaffected by this identification
limit.

## What must not happen next

The specification is frozen. It must not be revised in search of significance.
Any variant explored from here is an in-sample variant, labelled as such and
reported alongside S1, and the count of specifications tried goes in the
manuscript.
