# Methodology

## Unit of analysis

One row represents one calendar year. The principal population is Portugal's general-government sector, ESA institutional sector `S13`.

## Main outcome

\[
\text{Interest burden}_t =
\frac{\text{Interest payable}_t}{\text{Nominal GDP}_t}\times 100.
\]

The authoritative numerator is Eurostat item `D41PAY`, general-government interest payable. The project retains both the official Eurostat percentage-of-GDP series and a ratio reconstructed from million-euro interest and GDP values.

## Effective interest rate

The default estimate is:

\[
r_t^{\text{implicit}} =
\frac{I_t}{(D_{t-1}+D_t)/2}\times 100.
\]

The average-debt denominator is intended to reduce distortion when the year-end debt stock changes sharply. A previous-year-debt definition is supported through configuration. The definition must be reported with every result.

## Primary balance

When interest expenditure is represented as a positive expense:

\[
\text{Primary balance}_t =
\text{Overall balance}_t + \text{Interest burden}_t.
\]

## Nominal and real growth

Nominal GDP growth is calculated from current-price GDP. Real GDP growth is read from Eurostat's chain-linked volume percentage-change series. The approximate GDP-deflator growth rate is derived multiplicatively:

\[
1+\pi_t^{GDP} = \frac{1+g_t^{nominal}}{1+g_t^{real}}.
\]

## Debt dynamics

Debt dynamics are reported using a discrete approximation:

\[
\Delta d_t =
\frac{r_t-g_t}{1+g_t}d_{t-1}
-pb_t+sfa_t.
\]

Ratios are used internally and percentage-point outputs are written to the processed dataset. The stock-flow adjustment is calculated as the residual required to reconcile observed debt-ratio changes with the interest-growth term and primary balance.

## Exact interest-burden decomposition

Changes in the interest burden are decomposed as an accounting identity, not as a statistical model. The decomposed burden is reconstructed from euro interest expenditure and nominal GDP to avoid rounding differences in published percentage ratios. With \(r_t\) denoting interest expenditure divided by average debt and \(\bar{b}_t\) denoting average debt divided by GDP, the exact change is:

\[
\Delta(r_t\bar{b}_t) =
\Delta r_t \bar{b}_{t-1}
+ r_{t-1}\Delta \bar{b}_t
+ \Delta r_t \Delta \bar{b}_t.
\]

The three terms are written as `rate_effect_pp`, `average_debt_ratio_effect_pp`, and `interaction_effect_pp`. Their sum must equal `calculated_interest_burden_change_pp` within numerical tolerance.

## Historical extension

The main ESA 2010 series begins in 1995. Earlier AMECO observations are permitted only as a linked extension. Rows preserve:

- `source = AMECO`;
- `accounting_basis = linked_ESA2010_ESA95_ESA79`;
- an explicit observed/forecast status.

The extension cannot overwrite a Eurostat observation.

## Forecast handling

AMECO forecasts are retained separately. Historical descriptive statistics, break tests, and trend estimates exclude forecasts by default.

## Rate-shock interpretation

The static full-pass-through effect is:

\[
\Delta(i/Y) = (D/Y)\Delta r.
\]

This is a long-run arithmetic sensitivity, not an immediate annual forecast. A refinancing model applies the shock only to the configured share of debt repriced in each future year.

## Comparison design

Cross-country comparisons use the same Eurostat datasets, sector, transaction, and units. Country-specific cash-accounting sources cannot be mixed into the harmonised panel without a separate reconciliation layer.
