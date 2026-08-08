# Pass-through simulation and conditional historical validation

Simulation under a scenario kernel whose behavioural component is treated as a
sensitivity. Not a forecast.

## The headline: the scenario kernel is not a forecast winner

Mean absolute error on the realised effective rate, basis points. The realised
series is imported from the burden paper, not recomputed. Realised issuance
yields are fed in, so kernel error is isolated from yield-path error.

| Cut | Scenario kernel | WAM benchmark | Immediate full | Random walk |
| --- | --- | --- | --- | --- |
| 2014 | **40.35** | 43.24 | 95.09 | 120.75 |
| 2018 | **12.50** | 12.92 | 119.67 | 63.62 |
| 2021 | 10.08 | **9.81** | 81.05 | 24.52 |

The scenario kernel wins at 2014 by 2.9 bps and at 2018 by 0.4 bps, and loses
at 2021 by 0.3 bps. Against error levels of 10 to 43 bps these differences are
noise.

Stated plainly: the scenario kernel does not outperform the
weighted-average-maturity benchmark in any useful predictive sense. The paper's
central contribution is a measurement decomposition, not a forecasting claim.

The primary cut is 2021, which puts the entire tightening episode out of
sample. That is where a behaviourally responsive kernel should have won most
clearly, and it loses by 0.3 basis points.

What the kernel does beat, decisively, is immediate full pass-through (81 bps
at the 2021 cut) and a random walk (24.5 bps). Both are straw men. Beating them
establishes that gradual repricing is real, which was never in dispute.

## Why this is still a result

The negative finding is informative because of *where* it leaves the
contribution. The WAM benchmark is hard to beat on a four-year horizon because
both kernels are anchored to the same published maturity and fed the same
realised yields. What differs between them is shape, and shape matters most in
the first year — which a four-observation backtest barely sees.

So the comparison result in `reports/repricing/kernel.md` and this null are
consistent: the standard proxy differs materially from the composition-sensitive
kernel at short horizons, but the sign is not stable across the reported
horizons and the difference is too small relative to effective-rate volatility
to show up as predictive gain over four annual observations.

## An artefact that must not be reported as a finding

The simulated half-lives differ by direction:

| Shock | Half-life |
| --- | --- |
| +50, +100, +200 bps | 2 years |
| −50, −100, −200 bps | 3 years |

This asymmetry is mechanical, not estimated. The behavioural track clips its
response at zero, so a rate fall cannot produce a negative behavioural
contribution. The clip is a modelling choice, and it manufactures exactly the
asymmetry the original design predicted.

The estimated asymmetry was a null with a 95 percent interval of
[−0.020, +0.044]. Any asymmetry in these paths is an artefact of the clip and is
reported here only so that it is not mistaken for evidence.

## Nominal growth as a denominator sensitivity

The burden paper holds GDP and the debt ratio fixed for ten years to isolate
refinancing arithmetic. Growth paths are explicit here so the size of that
denominator convention is visible.

At +100 bps, horizon five years:

| Growth path | Incremental burden, % of GDP |
| --- | --- |
| Zero growth (the burden paper's assumption) | 0.475 |
| Low, 2 percent | 0.431 |
| Central, 4 percent | 0.391 |

The central nominal-growth path reduces the measured shock effect by about 18
percent at five years. This follows from the assumed denominator path and should
be read as a scenario sensitivity, not as an estimated correction.

The euro interest amount is invariant to the growth path by construction: with
the debt stock fixed in euro, nominal growth changes the denominator but not the
interest bill. Only the ratio moves. That is arithmetic, not a finding, and it
is why the cumulative euro column is identical across paths.

## What to take from this section

1. The scenario kernel does not beat the standard benchmark in any meaningful
   predictive sense.
2. The standard proxy and the composition-sensitive kernel differ most at short
   horizons where this backtest has least power.
3. The apparent asymmetry in half-lives is a modelling artefact.
4. Replacing fixed GDP with an illustrative central growth path cuts the
   five-year burden ratio by 18 percent mechanically through the denominator.
