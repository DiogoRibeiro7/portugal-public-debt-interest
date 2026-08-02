# Pass-through simulation and out-of-sample backtest

Simulation under an estimated kernel whose behavioural component is a measured
null. **Not a forecast.**

## The headline: the estimated kernel does not beat the standard benchmark

Mean absolute error on the realised effective rate, basis points. The realised
series is imported from the burden paper, not recomputed. Realised issuance
yields are fed in, so kernel error is isolated from yield-path error.

| Cut | Estimated kernel | WAM benchmark | Immediate full | Random walk |
| --- | --- | --- | --- | --- |
| 2014 | **52.44** | 55.69 | 95.09 | 120.75 |
| 2018 | 47.81 | **45.16** | 119.67 | 63.62 |
| 2021 | **14.24** | 14.66 | 81.05 | 24.52 |

The estimated kernel wins at 2014 by 3.3 bps and at 2021 by 0.4 bps, and
**loses at 2018** by 2.7 bps. Against error levels of 14 to 52 bps these
differences are noise.

**Stated plainly: the estimated kernel does not outperform the
weighted-average-maturity benchmark out of sample.** The paper's central
predictive claim is not supported.

The primary cut is 2021, which puts the entire tightening episode out of
sample. That is where a behaviourally responsive kernel should have won most
clearly, and it wins by 0.4 basis points.

What the kernel does beat, decisively, is immediate full pass-through (81 bps
at the 2021 cut) and a random walk (24.5 bps). Both are straw men. Beating them
establishes that gradual repricing is real, which was never in dispute.

## Why this is still a result

The negative finding is informative because of *where* it leaves the
contribution. The WAM benchmark is hard to beat on a four-year horizon because
both kernels are anchored to the same published maturity and fed the same
realised yields. What differs between them is shape, and shape matters most in
the first year — which a four-observation backtest barely sees.

So the bias result in `reports/repricing/kernel.md` and this null are
consistent: the standard proxy is biased at short horizons by roughly 10.9
percentage points of the stock, and that bias is too small relative to
effective-rate volatility to show up as predictive gain over four annual
observations.

## An artefact that must not be reported as a finding

The simulated half-lives differ by direction:

| Shock | Half-life |
| --- | --- |
| +50, +100, +200 bps | 2 years |
| −50, −100, −200 bps | 3 years |

**This asymmetry is mechanical, not estimated.** The behavioural track clips its
response at zero, so a rate fall cannot produce a negative behavioural
contribution. The clip is a modelling choice, and it manufactures exactly the
asymmetry the original design predicted.

The estimated asymmetry was a null with a 95 percent interval of
[−0.020, +0.044]. Any asymmetry in these paths is an artefact of the clip and is
reported here only so that it is not mistaken for evidence.

## Nominal growth: the burden paper's flaw, fixed

The burden paper holds GDP and the debt ratio fixed for ten years, contradicting
its own finding that the denominator did most of the work in 2022-2025. Growth
paths are explicit here.

At +100 bps, horizon five years:

| Growth path | Incremental burden, % of GDP |
| --- | --- |
| Zero growth (the burden paper's assumption) | 0.475 |
| Low, 2 percent | 0.431 |
| Central, 4 percent | 0.391 |

**Realistic nominal growth removes about 18 percent of the measured shock
effect at five years.** Holding GDP fixed overstates the burden impact by that
much, which is a material correction to the earlier paper's scenario section.

The euro interest amount is invariant to the growth path by construction: with
the debt stock fixed in euro, nominal growth changes the denominator but not the
interest bill. Only the ratio moves. That is arithmetic, not a finding, and it
is why the cumulative euro column is identical across paths.

## What to take from this section

1. The estimated kernel does not beat the standard benchmark out of sample.
2. The bias in the standard proxy is nonetheless real and measurable, and it is
   concentrated at short horizons where this backtest has least power.
3. The apparent asymmetry in half-lives is a modelling artefact.
4. Fixing the fixed-GDP assumption cuts the five-year shock effect by 18
   percent, which stands on its own as a correction to the companion paper.
