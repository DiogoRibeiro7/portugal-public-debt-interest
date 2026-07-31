# Blocking Calculation Trace

This document records the current calculation path before any repair work is
applied. It is a trace artifact only: no production code, tests, figures, or
tables are changed by this step.

## Scope

The trace follows nine paper-facing outputs from source inputs to generated
columns and LaTeX references:

1. Debt-dynamics decomposition figure.
2. Debt-stabilising primary balance.
3. Interest-growth differential.
4. Stock-flow adjustment.
5. Interest-burden change decomposition figure.
6. Static interest-rate shock table.
7. Refinancing shock-path figure.
8. Euro-area comparison table and rank statement.
9. Headline numerical statements generated for the paper.

## Source Data Path

Eurostat series are configured in `config/default.yaml` and fetched by
`src/pt_debt_interest/sources/eurostat.py`. The principal Portugal series are:

| Concept | Dataset | Filter | Output column |
| --- | --- | --- | --- |
| Interest payable, EUR | `gov_10a_main` | `unit=MIO_EUR`, `sector=S13`, `na_item=D41PAY`, `geo=PT` | `interest_mio_eur` |
| Interest payable, percent of GDP | `gov_10a_main` | `unit=PC_GDP`, `sector=S13`, `na_item=D41PAY`, `geo=PT` | `interest_pct_gdp_official` |
| Overall balance, percent of GDP | `gov_10a_main` | `unit=PC_GDP`, `sector=S13`, `na_item=B9`, `geo=PT` | `overall_balance_pct_gdp` |
| Government expenditure, EUR | `gov_10a_main` | `unit=MIO_EUR`, `sector=S13`, `na_item=TE`, `geo=PT` | `government_expenditure_mio_eur` |
| Government expenditure, percent of GDP | `gov_10a_main` | `unit=PC_GDP`, `sector=S13`, `na_item=TE`, `geo=PT` | `government_expenditure_pct_gdp_official` |
| Government revenue, EUR | `gov_10a_main` | `unit=MIO_EUR`, `sector=S13`, `na_item=TR`, `geo=PT` | `government_revenue_mio_eur` |
| Government revenue, percent of GDP | `gov_10a_main` | `unit=PC_GDP`, `sector=S13`, `na_item=TR`, `geo=PT` | `government_revenue_pct_gdp_official` |
| Gross debt, EUR | `gov_10dd_edpt1` | `unit=MIO_EUR`, `sector=S13`, `na_item=GD`, `geo=PT` | `debt_mio_eur` |
| Gross debt, percent of GDP | `gov_10dd_edpt1` | `unit=PC_GDP`, `sector=S13`, `na_item=GD`, `geo=PT` | `debt_pct_gdp_official` |
| Nominal GDP, EUR | `nama_10_gdp` | `unit=CP_MEUR`, `na_item=B1GQ`, `geo=PT` | `nominal_gdp_mio_eur` |
| Ten-year yield | `irt_lt_mcby_a` | `int_rt=MCBY`, `geo=PT` | `ten_year_yield_pct` |

The Portugal build path is:

`fetch_eurostat` -> `build_dataset` -> `calculate_metrics` ->
`build_interest_burden_decomposition` -> `save_processed` and
`save_interest_decomposition`.

The panel build path is:

`fetch_eurostat_panel` -> `build_panel_dataset` -> `build_panel_metrics` ->
panel CSV/table/reporting outputs.

## Output Trace Table

| Output | Raw inputs | Transform function | Processed columns | Reporting function | LaTeX reference | Current formula |
| --- | --- | --- | --- | --- | --- | --- |
| Debt-dynamics decomposition figure | `interest_mio_eur`, `debt_mio_eur`, `debt_pct_gdp`, `nominal_gdp_growth_pct`, `primary_balance_pct_gdp` | `calculate_metrics`; `plot_debt_dynamics` | `effective_interest_rate_debt_dynamics_decimal`, `interest_growth_contribution_pp`, `primary_balance_contribution_pp`, `stock_flow_adjustment_pp`, `observed_debt_ratio_change_pp` | `plot_debt_dynamics` writes `07_debt_dynamics` | `paper/portugal_public_debt_interest_report.tex`, `fig:debt-dynamics`, `../reports/figures/07_debt_dynamics.pdf` | `((I_t / D_{t-1}) - g_t) / (1 + g_t) * d_{t-1} * 100`; primary balance contribution is `-primary_balance_pct_gdp`; SFA is residual to observed debt-ratio change. |
| Debt-stabilising primary balance | `interest_mio_eur`, lagged `debt_mio_eur`, lagged `debt_pct_gdp`, `nominal_gdp_growth_pct` | `calculate_metrics` | `debt_stabilising_primary_balance_before_sfa_pct_gdp` | Headline/table generation consumes processed CSV | `eq:stabilising-pb` in paper | `((I_t / D_{t-1}) - g_t) / (1 + g_t) * d_{t-1} * 100`. This is currently identical to `interest_growth_contribution_pp`. |
| Interest-growth differential | `interest_mio_eur`, lagged `debt_mio_eur`, `nominal_gdp_growth_pct` | `calculate_metrics` | `interest_growth_differential_pct` | Used in summaries and methodology outputs | Debt-dynamics discussion around `eq:debt-dynamics` | `(I_t / D_{t-1} - g_t) * 100`. |
| Stock-flow adjustment | `debt_pct_gdp`, lagged `debt_pct_gdp`, debt-dynamics contribution, primary balance contribution | `calculate_metrics` | `stock_flow_adjustment_pp`, `reconstructed_debt_ratio_change_pp`, `debt_dynamics_reconciliation_error_pp` | `plot_debt_dynamics` | `fig:debt-dynamics` | `Delta d_t - interest_growth_contribution_pp - primary_balance_contribution_pp`. |
| Interest-burden change decomposition figure | `interest_mio_eur`, `nominal_gdp_mio_eur`, `debt_mio_eur`, `implicit_interest_rate_average_debt_decimal` | `build_interest_burden_decomposition`; `plot_interest_burden_decomposition` | `calculated_interest_burden_pct_gdp`, `average_debt_ratio_pct_gdp`, `average_debt_rate_decimal`, `rate_effect_pp`, `average_debt_ratio_effect_pp`, `interaction_effect_pp`, `reconstructed_interest_burden_change_pp` | `plot_interest_burden_decomposition` writes `10_interest_burden_decomposition` | `fig:interest-burden-decomposition`, `../reports/figures/10_interest_burden_decomposition.pdf` | `burden = I_t / Y_t * 100`; `rate_effect = Delta r_t * avg_debt_ratio_{t-1} * 100`; `debt_ratio_effect = r_{t-1} * Delta avg_debt_ratio_t * 100`; `interaction = Delta r_t * Delta avg_debt_ratio_t * 100`. |
| Static interest-rate shock table | Latest observed `debt_pct_gdp`; configured shocks | `static_rate_shock_table`; `rate_shock_table` | `shock_bps`, `shock_rate_pp`, `additional_interest_pct_gdp_full_pass_through` | `rate_shock_table` writes a LaTeX table | Table generated under `reports/tables` and included where referenced | `debt_pct_gdp * shock_bps / 10000`. |
| Refinancing shock-path figure | Latest observed `interest_pct_gdp`, latest observed `debt_pct_gdp`, configured shocks and refinancing shares | `refinancing_pass_through`; `plot_refinancing_shock_paths` | `baseline_interest_pct_gdp`, `baseline_debt_pct_gdp`, `shock_bps`, `horizon_year`, `repriced_share_cumulative`, `additional_interest_pct_gdp`, `interest_pct_gdp_scenario` | `plot_refinancing_shock_paths` writes `09_refinancing_shock_paths` | `fig:refinancing`, `../reports/figures/09_refinancing_shock_paths.pdf` | `full_effect = debt_pct_gdp * shock_bps / 10000`; `additional = full_effect * cumulative_refinancing_share`; plotted value is `baseline_interest_pct_gdp + additional`. |
| Euro-area comparison table and rank statement | Panel interest, debt, GDP, rates, status, aggregate flag | `build_panel_metrics`; `write_european_comparison_table`; `write_headline_macros` | `interest_burden_rank`, `average_debt_rate_rank`, `observation_status`, `is_aggregate` | `write_european_comparison_table`; `write_headline_macros` | `../reports/tables/european_comparison_2025.tex`; `../reports/tables/paper_headlines.tex` | Countries only: `~aggregate_flag_mask(is_aggregate)`. Observed rows only. Rank is descending competition rank with `method="min"` for interest burden and average-debt rate. |
| Headline numerical statements | Processed Portugal CSV, panel metrics, generated decomposition/scenario outputs | `write_headline_macros`; table generators; plotting functions | Macro values in `paper_headlines.tex`; CSV values in `data/processed` and `reports` | LaTeX `\input{../reports/tables/paper_headlines.tex}` and generated tables | Paper preamble and relevant sections | Values are generated from latest observed rows. Some surrounding prose remains manually authored and can drift from generated values. |

## Symbol Inventory

| Symbol or column | Location | Current role |
| --- | --- | --- |
| `effective_interest_rate_debt_dynamics_decimal` | `src/pt_debt_interest/metrics.py` | Debt-dynamics rate, computed as `interest_mio_eur / debt_mio_eur.shift(1)`. |
| `effective_interest_rate_debt_dynamics_pct` | `src/pt_debt_interest/metrics.py`; `docs/data_dictionary.md` | Percent form of the debt-dynamics rate. |
| `implicit_interest_rate_average_debt_decimal` | `src/pt_debt_interest/metrics.py`; `src/pt_debt_interest/interest_decomposition.py` | Descriptive average-debt rate, computed as `interest_mio_eur / average_debt`. |
| `implicit_interest_rate_average_debt_pct` | `src/pt_debt_interest/metrics.py`; `src/pt_debt_interest/panel.py`; `src/pt_debt_interest/plotting.py`; `src/pt_debt_interest/latex_tables.py` | Percent form of average-debt rate; used in descriptive plots, panel ranking, and interest-burden decomposition. |
| `interest_growth_differential_pct` | `src/pt_debt_interest/metrics.py`; `docs/data_dictionary.md` | Debt-dynamics rate minus nominal GDP growth. Documentation currently describes this with imprecise rate language. |
| `debt_stabilising_primary_balance_before_sfa_pct_gdp` | `src/pt_debt_interest/metrics.py`; `docs/data_dictionary.md`; generated outputs | Primary balance required before stock-flow adjustment. |
| `interest_growth_contribution_pp` | `src/pt_debt_interest/metrics.py`; `src/pt_debt_interest/plotting.py` | Debt-ratio contribution of the interest-growth term. |
| `primary_balance_contribution_pp` | `src/pt_debt_interest/metrics.py`; `src/pt_debt_interest/plotting.py` | Contribution equal to negative primary balance. |
| `stock_flow_adjustment_pp` | `src/pt_debt_interest/metrics.py`; `src/pt_debt_interest/plotting.py`; docs | Residual needed to reconcile observed debt-ratio change. |
| `debt_dynamics_reconciliation_error_pp` | `src/pt_debt_interest/metrics.py`; validation docs/tests | Check that reconstructed debt-ratio change matches observed change. |
| `rate_effect_pp` | `src/pt_debt_interest/interest_decomposition.py`; `src/pt_debt_interest/plotting.py` | Effect of changes in the average-debt rate on interest burden. |
| `average_debt_ratio_effect_pp` | `src/pt_debt_interest/interest_decomposition.py`; `src/pt_debt_interest/plotting.py` | Effect of changes in the average debt-to-GDP denominator. |
| `interaction_effect_pp` | `src/pt_debt_interest/interest_decomposition.py`; `src/pt_debt_interest/plotting.py` | Cross term in current interest-burden decomposition. |
| `refinancing_pass_through` | `src/pt_debt_interest/scenarios.py`; `src/pt_debt_interest/plotting.py` | Deterministic pass-through arithmetic for gradual repricing. |
| `default_refinancing_shares` | `config/default.yaml` | Seven-year refinancing shares: `[0.12, 0.13, 0.14, 0.15, 0.16, 0.15, 0.15]`. |
| `static_rate_shocks_bps` | `config/default.yaml` | Static shock sizes: `[50, 100, 200]`. |
| `interest_burden_rank` | `src/pt_debt_interest/panel.py`; `src/pt_debt_interest/latex_tables.py` | Descending country rank by `interest_pct_gdp`, excluding aggregates in reporting. |
| `average_debt_rate_rank` | `src/pt_debt_interest/panel.py`; `src/pt_debt_interest/latex_tables.py` | Descending country rank by `implicit_interest_rate_average_debt_pct`, excluding aggregates in reporting. |
| `observation_status` | `src/pt_debt_interest/panel.py`; `src/pt_debt_interest/latex_tables.py`; `src/pt_debt_interest/plotting.py` | Filters generated paper outputs to observed rows. |
| `is_aggregate` | `src/pt_debt_interest/panel.py`; `src/pt_debt_interest/latex_tables.py`; `src/pt_debt_interest/plotting.py` | Excludes aggregates from country-ranking outputs. |

## Explicit Answers

1. The debt-dynamics rate is actually used in the debt-dynamics formula. In
   `calculate_metrics`, `rate = output["effective_interest_rate_debt_dynamics_decimal"]`
   feeds `interest_growth_differential_pct`,
   `debt_stabilising_primary_balance_before_sfa_pct_gdp`, and
   `interest_growth_contribution_pp`.

2. The implementation uses `interest_mio_eur / previous_debt` for the
   debt-dynamics identity. The average-debt denominator is separately used for
   descriptive financing-cost measures and the interest-burden decomposition.

3. The debt-dynamics figure uses the same computed series as Equation 1. The
   paper reference is `fig:debt-dynamics`, backed by
   `reports/figures/07_debt_dynamics.pdf`. The plot consumes
   `interest_growth_contribution_pp`, `primary_balance_contribution_pp`,
   `stock_flow_adjustment_pp`, and `observed_debt_ratio_change_pp`.

4. The debt-stabilising primary balance uses the same rate and expression as
   the interest-growth contribution in the debt-dynamics figure. In current
   code, both are computed from `((rate - growth) / (1 + growth)) *
   debt_ratio_lag * 100`.

5. The interest-burden decomposition uses reconstructed unrounded annual
   interest burden, not the official rounded Eurostat percent-of-GDP series.
   It computes `interest_mio_eur / nominal_gdp_mio_eur * 100`. The current
   method includes a rate effect, average-debt-ratio effect, and interaction
   term.

6. The refinancing shock-path figure uses exact configured shares
   `[0.12, 0.13, 0.14, 0.15, 0.16, 0.15, 0.15]` and shocks `[50, 100, 200]`.
   The plotted value is the total scenario burden:
   `baseline_interest_pct_gdp + additional_interest_pct_gdp`, not only the
   incremental effect.

7. Ranking uses tied competition ranks. `panel.py` calls
   `rank(ascending=False, method="min")`, so tied countries receive the same
   rank and the next rank is skipped.

8. The 2025 country comparison filters to observed, non-aggregate country
   rows. `latex_tables.py` applies `observation_status == "observed"` and
   `~aggregate_flag_mask(is_aggregate)` before the European comparison table
   and headline rank macros are generated.

## Numerical Evidence

The current generated files give the following 2025 trace values:

| Evidence item | Current value |
| --- | ---: |
| Portugal interest payable, EUR million | 5964.5 |
| Portugal nominal GDP, EUR million | 306749.6 |
| Portugal debt, EUR million | 275062.8 |
| Interest burden, percent of GDP | 1.9 |
| Average-debt implicit rate, percent | 2.1849397955582113 |
| Debt-dynamics effective rate, percent | 2.2017195154408293 |
| Nominal GDP growth, percent | 5.8544579537262775 |
| Interest-growth differential, percentage points | -3.652738438285448 |
| Debt-stabilising primary balance before SFA, percent of GDP | -3.2264209801063632 |
| Interest-growth contribution, percentage points | -3.2264209801063632 |
| Primary-balance contribution, percentage points | -2.5999999999999996 |
| Stock-flow adjustment, percentage points | 2.0264209801063595 |
| Observed debt-ratio change, percentage points | -3.8000000000000034 |
| Interest-burden decomposition residual, percentage points | 1.8041124150158794e-16 |
| Portugal 2025 interest-burden rank | 6 |
| Portugal 2025 average-debt-rate rank | 8 |
| 100 bp refinancing path, year 7, cumulative repriced share | 1.0 |
| 100 bp refinancing path, year 7, additional interest percent of GDP | 0.897 |
| 100 bp refinancing path, year 7, total scenario interest percent of GDP | 2.7969999999999997 |

## Manual Embedding Risk

The main analytical tables and headline values are generated and included
through LaTeX `\input` calls. The major figures are manually referenced with
fixed filenames, but those files are generated outputs. The remaining risk is
manual narrative prose around the generated values: those sentences can drift
from the generated CSV, macro, or figure values unless later repairs force the
claims to be generated or verified against the data.

## Remaining Blockers

1. Documentation terminology still needs tightening where debt-dynamics
   measures are described with average-rate language.
2. The interest-burden decomposition method currently exposes an interaction
   component in the main figure; the repair sequence later needs to decide
   whether that belongs in the figure or only in a validation artifact.
3. Refinancing-path prose exposes the stylised cohort assumptions in the paper,
   including the annual repricing shares and source status.
4. The generated-output boundary is not fully enforced for all narrative
   numerical claims in the paper.
5. No tests were added in this trace-only step.
