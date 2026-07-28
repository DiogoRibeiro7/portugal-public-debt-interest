# Data dictionary

| Column | Unit | Definition |
|---|---:|---|
| `year` | year | Calendar year |
| `geo` | category | Eurostat geography code in comparator panels |
| `geo_name` | category | Display name for comparator panels |
| `is_aggregate` | boolean | Marks euro-area or other aggregate rows in comparator panels |
| `aggregate_composition` | category | Aggregate code identifying the composition where applicable |
| `interest_mio_eur` | € million | General-government interest payable, `D41PAY` |
| `interest_pct_gdp_official` | % GDP | Official Eurostat ratio |
| `interest_pct_gdp_calculated` | % GDP | Interest in euros divided by current-price GDP |
| `interest_pct_gdp` | % GDP | Preferred ratio: official, with calculated fallback |
| `nominal_gdp_mio_eur` | € million | GDP at current market prices, `B1GQ` |
| `nominal_gdp_growth_pct` | % | Annual current-price GDP growth |
| `real_gdp_growth_pct` | % | Chain-linked volume change from previous year |
| `gdp_deflator_growth_pct` | % | Derived GDP deflator growth |
| `debt_mio_eur` | € million | Maastricht consolidated gross debt, `GD` |
| `debt_pct_gdp_official` | % GDP | Official Eurostat debt ratio |
| `debt_pct_gdp_calculated` | % GDP | Debt in euros divided by current-price GDP |
| `debt_pct_gdp` | % GDP | Preferred debt ratio |
| `effective_interest_rate_debt_dynamics_decimal` | ratio | Interest divided by previous-year debt; internal debt-dynamics rate |
| `effective_interest_rate_debt_dynamics_pct` | % | Display version of the debt-dynamics effective interest rate |
| `implicit_interest_rate_average_debt_decimal` | ratio | Interest divided by average of previous and current debt; internal average-cost rate |
| `implicit_interest_rate_average_debt_pct` | % | Display version of the average-stock implicit interest rate |
| `calculated_interest_burden_pct_gdp` | % GDP | Interest burden reconstructed from euro interest expenditure and nominal GDP for exact decomposition |
| `lag_calculated_interest_burden_pct_gdp` | % GDP | Previous observed value of the reconstructed interest burden |
| `calculated_interest_burden_change_pp` | percentage points | Annual change in the reconstructed interest burden |
| `average_debt_ratio_pct_gdp` | % GDP | Average of previous and current debt divided by current-price GDP |
| `lag_average_debt_ratio_pct_gdp` | % GDP | Previous observed value of the average-debt ratio |
| `average_debt_rate_decimal` | ratio | Average-debt implicit interest rate used in the interest-burden decomposition |
| `lag_average_debt_rate_decimal` | ratio | Previous observed value of the average-debt implicit interest rate |
| `rate_effect_pp` | percentage points | Exact contribution of the average-debt implicit-rate change to the interest-burden change |
| `average_debt_ratio_effect_pp` | percentage points | Exact contribution of the change in average debt relative to GDP |
| `interaction_effect_pp` | percentage points | Exact interaction between the rate change and the average-debt-ratio change |
| `reconstructed_interest_burden_change_pp` | percentage points | Sum of rate, average-debt-ratio, and interaction effects |
| `interest_burden_decomposition_residual_pp` | percentage points | Observed calculated interest-burden change minus reconstructed change |
| `interest_burden_rank` | rank | Per-year rank among non-aggregate comparator countries by interest burden |
| `average_debt_rate_rank` | rank | Per-year rank among non-aggregate comparator countries by average-debt implicit rate |
| `interest_growth_differential_pct` | percentage points | Implicit interest rate minus nominal GDP growth |
| `debt_stabilising_primary_balance_before_sfa_pct_gdp` | % GDP | Primary balance needed to stabilise debt absent stock-flow effects |
| `observed_debt_ratio_change_pp` | percentage points | Observed annual change in the debt-to-GDP ratio |
| `interest_growth_contribution_pp` | percentage points | Debt-ratio contribution from the effective interest rate and nominal GDP growth |
| `primary_balance_contribution_pp` | percentage points | Debt-ratio contribution of the primary balance, equal to the negative of the primary balance |
| `stock_flow_adjustment_pp` | percentage points | Residual in the discrete debt-dynamics equation |
| `reconstructed_debt_ratio_change_pp` | percentage points | Sum of debt-dynamics contribution terms |
| `debt_dynamics_reconciliation_error_pp` | percentage points | Observed minus reconstructed debt-ratio change |
| `overall_balance_pct_gdp` | % GDP | Net lending (+) or borrowing (-), `B9` |
| `primary_balance_pct_gdp` | % GDP | Overall balance plus interest expenditure |
| `ten_year_yield_pct` | % | EMU convergence-criterion long-term yield |
| `source` | category | Eurostat or AMECO |
| `source_vintage` | category | Source release or vintage identifier when available |
| `accounting_basis` | category | ESA2010 or linked historical basis |
| `observation_status` | category | observed or forecast |
| `retrieval_timestamp_utc` | timestamp | UTC retrieval timestamp when available |
| `source_checksum_sha256` | hash | SHA-256 checksum of raw source payloads, joined when a row uses multiple series |
| `source_flags` | category | Source observation flags or selected source codes |
| `basis_break` | boolean | Marks the first authoritative ESA 2010 main-series year |
| `regime` | category | Configured historical period |
