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
| `government_expenditure_mio_eur` | € million | General-government total expenditure, Eurostat `TE` |
| `government_expenditure_pct_gdp_official` | % GDP | Official Eurostat total-expenditure ratio |
| `government_expenditure_pct_gdp_calculated` | % GDP | Total expenditure in euros divided by current-price GDP |
| `government_expenditure_pct_gdp` | % GDP | Preferred total-expenditure ratio: official, with calculated fallback |
| `government_expenditure_eur` | € | General-government total expenditure in euros |
| `government_revenue_mio_eur` | € million | General-government total revenue, Eurostat `TR` |
| `government_revenue_pct_gdp_official` | % GDP | Official Eurostat total-revenue ratio |
| `government_revenue_pct_gdp_calculated` | % GDP | Total revenue in euros divided by current-price GDP |
| `government_revenue_pct_gdp` | % GDP | Preferred total-revenue ratio: official, with calculated fallback |
| `government_revenue_eur` | € | General-government total revenue in euros |
| `nominal_gdp_mio_eur` | € million | GDP at current market prices, `B1GQ` |
| `nominal_gdp_growth_pct` | % | Annual current-price GDP growth |
| `real_gdp_growth_pct` | % | Chain-linked volume change from previous year |
| `gdp_deflator_growth_pct` | % | Derived GDP deflator growth |
| `debt_mio_eur` | € million | Maastricht consolidated gross debt, `GD` |
| `debt_pct_gdp_official` | % GDP | Official Eurostat debt ratio |
| `debt_pct_gdp_calculated` | % GDP | Debt in euros divided by current-price GDP |
| `debt_pct_gdp` | % GDP | Preferred debt ratio |
| `debt_dynamics_interest_rate` | ratio | Interest divided by previous-year debt; internal debt-dynamics rate |
| `debt_dynamics_interest_rate_pct` | % | Display version of the debt-dynamics interest rate |
| `average_debt_interest_rate` | ratio | Interest divided by average of previous and current debt; internal average-cost rate |
| `average_debt_interest_rate_pct` | % | Display version of the average-debt interest rate |
| `reconstructed_interest_burden` | ratio | Interest burden reconstructed from euro interest expenditure and nominal GDP for exact decomposition |
| `reconstructed_interest_burden_pct_gdp` | % GDP | Display version of the reconstructed interest burden |
| `official_interest_burden_pct_gdp` | % GDP | Official rounded burden used for endpoint comparison |
| `average_debt_ratio_pct_gdp` | % GDP | Average of previous and current debt divided by current-price GDP |
| `average_debt_rate` | ratio | Average-debt interest rate used in the endpoint interest-burden decomposition |
| `average_debt_rate_pct` | % | Display version of the average-debt interest rate used in decomposition |
| `start_year` | year | First endpoint in an interest-burden decomposition interval |
| `end_year` | year | Second endpoint in an interest-burden decomposition interval |
| `total_change_pp` | percentage points | Endpoint change in reconstructed interest burden |
| `rate_effect_pp` | percentage points | Symmetric endpoint contribution of the average financing-cost change |
| `debt_exposure_effect_pp` | percentage points | Symmetric endpoint contribution of the average debt-exposure change |
| `decomposition_reconciliation_error_pp` | percentage points | Total endpoint change minus the two decomposition components |
| `dominant_effect` | category | Larger absolute contribution in the endpoint decomposition |
| `interest_burden_rank` | rank | Per-year rank among non-aggregate comparator countries by interest burden |
| `average_debt_rate_rank` | rank | Per-year rank among non-aggregate comparator countries by average-debt interest rate |
| `interest_growth_differential` | ratio | Debt-dynamics interest rate minus nominal GDP growth |
| `interest_growth_differential_pct` | percentage points | Debt-dynamics interest rate minus nominal GDP growth |
| `debt_stabilising_primary_balance_before_sfa` | ratio | Primary balance needed to stabilise debt absent stock-flow effects |
| `debt_stabilising_primary_balance_before_sfa_pct_gdp` | % GDP | Primary balance needed to stabilise debt absent stock-flow effects |
| `observed_debt_ratio_change` | ratio | Observed annual change in the debt-to-GDP ratio |
| `observed_debt_ratio_change_pp` | percentage points | Observed annual change in the debt-to-GDP ratio |
| `interest_growth_contribution` | ratio | Debt-ratio contribution from the debt-dynamics interest rate and nominal GDP growth |
| `interest_growth_contribution_pp` | percentage points | Debt-ratio contribution from the debt-dynamics interest rate and nominal GDP growth |
| `primary_balance_contribution` | ratio | Debt-ratio contribution of the primary balance, equal to the negative of the primary balance |
| `primary_balance_contribution_pp` | percentage points | Debt-ratio contribution of the primary balance, equal to the negative of the primary balance |
| `stock_flow_adjustment` | ratio | Residual in the discrete debt-dynamics equation |
| `stock_flow_adjustment_pp` | percentage points | Residual in the discrete debt-dynamics equation |
| `reconstructed_debt_ratio_change` | ratio | Sum of debt-dynamics contribution terms |
| `reconstructed_debt_ratio_change_pp` | percentage points | Sum of debt-dynamics contribution terms |
| `debt_dynamics_reconciliation_error` | ratio | Observed minus reconstructed debt-ratio change |
| `debt_dynamics_reconciliation_error_pp` | percentage points | Observed minus reconstructed debt-ratio change |
| `overall_balance_pct_gdp` | % GDP | Net lending (+) or borrowing (-), `B9` |
| `primary_balance_pct_gdp` | % GDP | Overall balance plus interest expenditure |
| `ten_year_yield_pct` | % | EMU convergence-criterion long-term yield |
| `source` | category | Eurostat or AMECO |
| `source_database` | category | Source database or institutional data system |
| `source_table_or_series` | category | Joined source table, series, raw file, or archive identifiers used by the row |
| `source_vintage` | category | Source release or vintage identifier when available |
| `accounting_basis` | category | ESA2010 or linked historical basis |
| `observation_status` | category | observed or forecast |
| `retrieval_timestamp_utc` | timestamp | UTC retrieval timestamp when available |
| `source_checksum_sha256` | hash | SHA-256 checksum of raw source payloads, joined when a row uses multiple series |
| `source_flags` | category | Source observation flags or selected source codes |
| `basis_break` | boolean | Marks the first authoritative ESA 2010 main-series year |
| `is_harmonised_main_sample` | boolean | Marks rows in the authoritative ESA 2010 analysis sample |
| `is_historical_extension` | boolean | Marks linked pre-main-sample observations retained only for historical context |
| `regime` | category | Configured historical period |
