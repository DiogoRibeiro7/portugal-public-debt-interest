# Data dictionary

| Column | Unit | Definition |
|---|---:|---|
| `year` | year | Calendar year |
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
| `implicit_interest_rate_pct` | % | Interest divided by configured debt denominator |
| `overall_balance_pct_gdp` | % GDP | Net lending (+) or borrowing (-), `B9` |
| `primary_balance_pct_gdp` | % GDP | Overall balance plus interest expenditure |
| `ten_year_yield_pct` | % | EMU convergence-criterion long-term yield |
| `source` | category | Eurostat or AMECO |
| `source_vintage` | category | Source release or vintage identifier when available |
| `accounting_basis` | category | ESA2010 or linked historical basis |
| `observation_status` | category | observed or forecast |
| `retrieval_timestamp_utc` | timestamp | UTC retrieval timestamp when available |
| `source_flags` | category | Source observation flags or selected source codes |
| `basis_break` | boolean | Marks the first authoritative ESA 2010 main-series year |
| `regime` | category | Configured historical period |
