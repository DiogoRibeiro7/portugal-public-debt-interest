# Interest-rate definitions

The project uses two constructed interest-rate concepts. They answer different
questions and must not be used interchangeably.

| Machine-readable column | Report label | Symbol | Unit | Formula | Source columns | First valid observation | Permitted uses | Prohibited uses |
|---|---|---|---|---|---|---|---|---|
| `debt_dynamics_interest_rate` | Debt-dynamics interest rate | \(r_t^{DD}\) | decimal ratio | \(I_t / D_{t-1}\) | `interest_mio_eur`, lagged `debt_mio_eur` | First year after a same-basis lag exists | Discrete debt-dynamics identity, interest-growth differential, debt-stabilising primary balance, stock-flow adjustment | Average-cost interpretation, benchmark-yield chart, cross-country average-cost ranking |
| `debt_dynamics_interest_rate_pct` | Debt-dynamics interest rate | \(100r_t^{DD}\) | percent | `debt_dynamics_interest_rate * 100` | generated from decimal rate | Same as decimal rate | Report display only | Internal arithmetic |
| `average_debt_interest_rate` | Average-debt interest rate | \(r_t^{AVG}\) | decimal ratio | \(I_t / ((D_{t-1}+D_t)/2)\) | `interest_mio_eur`, lagged and current `debt_mio_eur` | First year after a same-basis lag exists | Average-cost description, benchmark-yield comparison, interest-burden factorisation | Debt-dynamics identity, debt-stabilising primary balance, stock-flow adjustment |
| `average_debt_interest_rate_pct` | Average-debt interest rate | \(100r_t^{AVG}\) | percent | `average_debt_interest_rate * 100` | generated from decimal rate | Same as decimal rate | Report display only | Internal arithmetic |

The first valid observation is missing when previous-year debt is unavailable
or when the lag would cross an accounting-basis boundary. The project does not
impute a lagged debt value across the AMECO-Eurostat boundary.

Neither constructed rate is an official average coupon on the Portuguese
debt-management portfolio. Both are national-accounts ratios built from
general-government interest payable and Maastricht gross debt.
