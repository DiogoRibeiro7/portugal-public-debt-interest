# Refinancing Scenario Design

The refinancing exercise is an arithmetic sensitivity analysis. It is not a forecast, does not estimate market reaction functions, and does not change debt, GDP, maturity, or primary balances endogenously.

For a shock \(\Delta r\) and debt ratio \(d\), the static full-pass-through burden is \(d\Delta r\). The dynamic path applies that burden only to the cumulative share of the debt stock assumed to refinance by each horizon.

The scenario output reports the full-pass-through burden, the cumulative repriced share, the realised incremental burden, and the gap still not passed through. These columns make the maturity-lag assumption auditable and ensure the dynamic path reconciles to the static sensitivity when the configured refinancing shares sum to one.
