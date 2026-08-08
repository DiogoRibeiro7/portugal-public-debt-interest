# Repricing study: design revision after acquisition

The acquisition step established that two inputs the original design depends on
are not obtainable: a dated contractual redemption schedule, and gross retail
subscriptions and redemptions. This note records what the available data can
and cannot support, and proposes a revised design.

It is written before any estimation, so that the specification is fixed on the
basis of what is identifiable rather than tuned toward a hypothesis.

---

## What the data says before any model is fitted

Certificados de Aforro, net monthly change, EUR million, 2001-02 to 2026-06
(305 observations, mean +96, sd +409).

The single largest movement in the sample is not a redemption episode. It is a
subscription episode, and it coincides exactly with the monetary tightening the
paper is about.

| Month | Stock (EUR m) | Net change |
| --- | --- | --- |
| 2022-06 | 12,943 | |
| 2022-10 | 16,020 | +1,409 |
| 2022-12 | 19,626 | +1,916 |
| 2023-03 | 28,642 | **+3,549** |
| 2023-05 | 32,550 | +2,226 |
| 2023-06 | 33,221 | +670 |
| 2023-08 | 33,868 | +258 |
| 2023-10 | 34,072 | +39 |
| 2023-11 | 34,064 | −8 |
| 2024-06 | 33,961 | −3 |

Two facts follow, and both matter more than anything a hazard regression would
have told us.

**1. The retail channel ran in the opposite direction to the hypothesis.** The
original claim was that a rate rise accelerates its own pass-through because
holders redeem on demand and reinvest at the new rate. In the one large
tightening episode in the sample, Portuguese households did the reverse: the
retail stock grew 151 percent between June 2022 and May 2023, from 12.9 to 32.6
billion euro. Correlation between net flow and the household deposit rate is
**−0.20** over the full sample and **−0.23** in the tightening window. The sign
is against the hypothesis, not merely insignificant.

The mechanism is not mysterious. The certificate's remuneration formula tracked
short rates, so when policy tightened the certificate out-competed bank
deposits rather than being out-competed by them. The competing-return spread
moved in the certificate's favour.

**2. There is a sharp, dateable policy break in June 2023.** Subscriptions stop
almost immediately: +3,549 in March, +670 in June, +39 by October, and the
stock is flat to slightly negative from November 2023 onward. A discrete change
in the terms offered on new subscriptions switched the channel off. That break
is a far cleaner identification lever than a smoothly estimated hazard.

---

## What is and is not identifiable

**Not identifiable, and to be dropped rather than fudged:**

- *The voluntary redemption hazard.* Net stock is subscriptions minus
  redemptions. A flat month is equally consistent with no activity and with
  large offsetting flows. No amount of specification care recovers the
  redemption margin from a net series.
- *Cause-specific and subdistribution hazards over competing exit types.* These
  require an event history the data cannot produce. Fine–Gray, Aalen–Johansen,
  and the cause-specific models were all premised on observing exits.
- *The contractual track read off a dated schedule.* Only summary maturity
  statistics exist.

**Identifiable, and arguably better identified than the original design:**

- *The positive stock-value margin.* The published stock is outstanding value,
  so positive monthly changes mix principal flows and capitalised interest.
  During Jun 2022-May 2023 the observed stock-value increase was large enough
  to identify a retail episode, but not to decompose that episode into gross
  subscriptions, redemptions, reissues and accrued interest.
- *State dependence of the repricing kernel.* This is the paper's central
  claim, and it survives intact. Money moving onto the current rate reprices
  the stock exactly as effectively whether it arrives by redemption and
  reissue or by new subscription. The channel is shock-responsive either way.
- *Asymmetry, reframed.* Not "do redemptions respond asymmetrically" but "does
  the retail repricing flow respond asymmetrically to spread widening versus
  narrowing". Testable on net flows, with the caveat that the sample contains
  one large widening episode and the estimate will be correspondingly fragile.
- *A policy-break natural experiment.* The June 2023 terms change is a discrete
  intervention with a large pre/post contrast, dateable to the month.
- *The WAM comparison result.* Untouched by any of this. It needs the average
  residual maturity series, which was acquired monthly for 2000-12 to 2026-06,
  and the composition split, which was also acquired.

---

## Proposed revised design

Three options, in descending order of what they claim.

### Option A — subscription-margin repricing with a policy break (recommended)

Replace the competing-risks frame with a repricing-flow model on the margin the
data actually observes.

- The kernel keeps its three-part structure: contractual, behavioural, reset.
  The contractual component is calibrated from the monthly average residual
  maturity series rather than read off a schedule, and that substitution is
  stated as a limitation rather than hidden.
- The behavioural component becomes a descriptive stock-value response
  estimated on positive outstanding-value change against the competing-return
  spread, with the June 2023 break entering as a dated policy intervention.
- The headline result remains the WAM comparison difference, decomposed into shape and
  behavioural components exactly as planned.
- The asymmetry section reports what the data supports: a strong, well-measured
  response in the widening direction, and honest silence about the narrowing
  direction, which the sample does not contain.

**What it claims:** the repricing kernel can be made sensitive to the rate path,
and the retail episode is visible in aggregate stock-value data. The behavioural
coefficient remains descriptive because the gross-flow and accounting
decomposition is missing.
**What it gives up:** the competing-risks machinery, the redemption hazard, and
the survival-analysis framing.

### Option B — WAM comparison only

Drop the behavioural component entirely. Quantify the difference in the
weighted-average-maturity approximation using the shape argument alone: a
memoryless hazard with the same mean maturity retires far less of the stock over
a decade than a realistic profile does.

**What it claims:** a methodological result about a standard proxy, with a
fiscal magnitude attached.
**What it gives up:** the entire behavioural contribution, which was the
paper's original point of novelty.

### Option C — proceed as designed, with the missing inputs manually ingested

Still available if the redemption profile and gross flows can be obtained from
IGCP directly. The manual-ingest specifications are written and the loaders are
specified; only the files are missing.

---

## Recommendation

**Option A.** The finding that the retail stock rose during tightening is not a
setback; it is the more interesting empirical episode, and it is firmly in the
data rather than in a model. A paper that says "the standard proxy is
incomplete, the retail episode is visible, and the behavioural coefficient is
descriptive rather than identified" is stronger than the original design would
have produced.

The original hypothesis should be stated in the paper and reported as
contradicted. That is a result, and burying it would be the one genuinely
indefensible choice here.
