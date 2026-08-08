# The repricing kernel and the WAM proxy

Portfolio state at 2026-06: average residual maturity 7.52 years, fixed-rate
share 85.8 percent, and retail share of stock 15.4 percent.

The benchmark is the companion burden paper's discrete annual constant-hazard
assumption, calibrated so expected repricing time equals published weighted
average maturity.

## Scenario-minus-WAM differences at +100 bps

| Horizon | WAM-implied share | Scenario share | Difference | Shape | Behaviour |
| --- | --- | --- | --- | --- | --- |
| 1 year | 13.30% | 19.89% | +6.60 pp | +6.60 | 0.00 |
| 3 years | 34.83% | 31.31% | -3.52 pp | -3.52 | 0.00 |
| 5 years | 51.01% | 42.72% | -8.29 pp | -8.29 | 0.00 |
| 10 years | 76.00% | 71.25% | -4.75 pp | -4.75 | 0.00 |

The sign is not stable across horizons. Under the central zero-behaviour case,
the WAM proxy understates one-year repricing but overstates the share repriced
at the longer reported horizons. The result is therefore not that WAM is always
too slow. It is that WAM alone does not identify the timing path once reset
instruments and a stylised contractual profile are separated.

## Mechanisms

The one-year shape term reflects fast reset exposure that a pure maturity
hazard cannot see. The longer-horizon negative terms come from the other side
of the same modelling choice: once the reset component has already moved, the
linear contractual profile can sit below the memoryless WAM tail.

The behavioural central effect is set to zero because the retail stock-value
association is not identified as a household response. Behavioural upside is
retained as a sensitivity band, not as the central result.

## Fiscal translation

At a 100 basis-point shock, the current central one-year bias translates to
about 0.059 percent of GDP, or EUR 181 million, using the paper's fiscal scaling
convention. This is a scale sensitivity, not an identified forecast, and it
inherits the mismatch between IGCP State direct debt composition and Maastricht
general-government debt used in the burden denominator.

## Supported claim

Weighted average maturity does not uniquely determine pass-through speed.
Composition and reset assumptions can move both the magnitude and sign of the
short-horizon difference, while the available aggregate retail data do not
identify a precise behavioural correction.
