# The repricing kernel and the bias in the standard proxy

Portfolio state at 2026-06: average residual maturity **7.52 years**,
fixed-rate share **0.858**, retail share of stock **0.154**.

The benchmark is the burden paper's assumption: one constant hazard over the
whole stock, calibrated so expected repricing time equals published weighted
average maturity.

## The bias, at +100 bps

| Horizon | WAM-implied | Estimated | **Total bias** | of which shape | of which behaviour |
| --- | --- | --- | --- | --- | --- |
| 1 year | 0.1245 | 0.2335 | **+10.90 pp** | +7.44 | +3.46 |
| 3 years | 0.3290 | 0.4168 | **+8.78 pp** | −1.59 | +10.37 |
| 5 years | 0.4857 | 0.5300 | **+4.43 pp** | −5.85 | +10.28 |
| 10 years | 0.7355 | 0.7641 | **+2.86 pp** | −2.30 | +5.16 |

**The sign is stable and it is positive at every horizon: the standard proxy
understates how much of the stock reprices.** The bias is largest at short
horizons, which is where a fiscal analyst is most likely to use it.

## Why, decomposed into two mechanisms

**Shape (+7.44 pp at one year).** A single constant hazard treats the stock as
homogeneous. It is not: **14.2 percent is floating-rate or inflation-linked and
reprices within a year regardless of maturity.** A maturity-calibrated hazard
cannot see that, because those instruments reprice *without exiting*. This is
the dominant mechanism at short horizons and it requires no behavioural
assumption at all.

The shape term changes sign at longer horizons (−1.59 at three years, −5.85 at
five). A memoryless hazard has a long right tail, and beyond the reset window
that tail retires more than a profile that has already retired its fast
component. **The shape effect is not monotone in the horizon**, which is worth
saying plainly: "the geometric kernel is too slow" is true early and false
later.

**Behaviour (+3.46 pp at one year, +10.37 at three).** The retail subscription
channel. The estimate underlying it is a **null**, so the band is wide and
open at the bottom:

| Horizon | Low | Central | High |
| --- | --- | --- | --- |
| 1 year | **0.00** | 3.46 | 9.21 |
| 3 years | **0.00** | 10.37 | 12.33 |
| 5 years | **0.00** | 10.28 | 10.28 |
| 10 years | **0.00** | 5.16 | 5.16 |

The lower bound is zero at every horizon because the estimated response is not
distinguishable from zero. Reporting a central path without this band would be
precisely the failure this paper criticises.

## Fiscal translation, +100 bps

| Horizon | Bias, % of GDP | Bias, EUR million |
| --- | --- | --- |
| 1 year | 0.098 | 300 |
| 3 years | 0.079 | 242 |
| 5 years | 0.040 | 122 |
| 10 years | 0.026 | 79 |

At a 2025 debt ratio of 89.7 percent of GDP and nominal GDP of 306.7 billion
euro. Undiscounted.

## What is solid and what is not

**Solid.** The shape component. It rests on the published fixed-rate share and
the published maturity, both acquired cleanly and monthly, and on the
arithmetic that floating debt reprices without exiting. No estimation enters
it. A referee can verify the one-year figure by hand.

**Not solid.** The behavioural component. Its band includes zero at every
horizon, and the honest reading is that the retail channel *may* contribute
nothing measurable. The central path should not be quoted without the band.

**Stylised, and stated as such.** No dated redemption schedule is published, so
the contractual track uses a linear retirement profile with the same mean. That
is a standard counterfactual shape, not IGCP's schedule, and the shape bias
inherits that assumption. `docs/manual_ingest.md` specifies the input that
would replace it.

## The paper's claim, as the evidence now supports it

The weighted-average-maturity proxy understates repricing, by 10.9 percentage
points of the stock at one year and 4.4 at five, worth about 300 million euro of
interest in the first year after a 100 basis-point shock. The mechanism is
mostly compositional rather than behavioural: a single hazard cannot represent a
stock that is 14 percent floating. The behavioural channel is visible in the raw
data but is not identifiable at the precision published sources allow.
