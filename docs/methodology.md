# Methodology

## Unit of analysis

One row represents one calendar year. The principal population is Portugal's general-government sector, ESA institutional sector `S13`.

## Main outcome

\[
\text{Interest burden}_t =
\frac{\text{Interest payable}_t}{\text{Nominal GDP}_t}\times 100.
\]

The authoritative numerator is Eurostat item `D41PAY`, general-government interest payable. The project retains both the official Eurostat percentage-of-GDP series and a ratio reconstructed from million-euro interest and GDP values.

## Interest-rate definitions

The descriptive average-debt rate is:

\[
r_t^{AVG} =
\frac{I_t}{(D_{t-1}+D_t)/2}.
\]

The debt-dynamics rate is:

\[
r_t^{DD} =
\frac{I_t}{D_{t-1}}.
\]

Both rates are decimal ratios internally. Percentage conversion occurs only in reporting outputs. The average-debt denominator is intended to reduce distortion when the year-end debt stock changes sharply in descriptive average-cost analysis. The debt-dynamics denominator is previous-year debt because the discrete debt-ratio identity is written from \(D_{t-1}\) to \(D_t\).

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
\frac{r_t^{DD}-g_t}{1+g_t}d_{t-1}
-pb_t+sfa_t.
\]

Ratios are used internally and percentage-point outputs are written to the processed dataset. The stock-flow adjustment is calculated as the residual required to reconcile observed debt-ratio changes with the interest-growth term and primary balance.

## Exact interest-burden decomposition

Changes in the interest burden are decomposed as an accounting identity, not as a statistical model. The decomposed burden is reconstructed from euro interest expenditure and nominal GDP to avoid rounding differences in published percentage ratios. With \(r_t^{AVG}\) denoting interest expenditure divided by average debt and \(\bar{d}_t\) denoting average debt divided by GDP, endpoint changes use the symmetric exact two-component decomposition:

\[
b_1^R-b_0^R =
\frac{\bar{d}_1+\bar{d}_0}{2}
(r_1^{AVG}-r_0^{AVG})
+\frac{r_1^{AVG}+r_0^{AVG}}{2}
(\bar{d}_1-\bar{d}_0).
\]

The two terms are written as `rate_effect_pp` and `debt_exposure_effect_pp`. Their sum must equal `total_change_pp` within numerical tolerance. No separate interaction term is used in the principal decomposition.

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

The dynamic scenario table reports the annual refinancing share, cumulative repriced share, remaining unrepriced share, full-pass-through burden, realised incremental burden at each horizon, and the remaining gap to full pass-through. A zero-basis-point shock must produce zero incremental burden, and a refinancing schedule that sums to one must reconcile to the static full-pass-through result at the final horizon.

## Comparison design

Cross-country comparisons use the same Eurostat datasets, sector, transaction, and units. Country-specific cash-accounting sources cannot be mixed into the harmonised panel without a separate reconciliation layer.
