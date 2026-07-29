# Debt-dynamics methodology

The project uses the discrete accounting identity:

\[
d_t - d_{t-1}
  =
  \frac{r_t^{DD} - g_t}{1 + g_t} d_{t-1}
  - pb_t
  + sfa_t.
\]

Definitions:

- \(d_t\): end-of-year gross general-government debt ratio.
- \(r_t^{DD}\): interest payable divided by previous-year nominal debt.
- \(g_t\): nominal GDP growth as a decimal.
- \(pb_t\): primary balance as a share of GDP, with a surplus positive.
- \(sfa_t\): stock-flow adjustment or reconciliation residual.

Sign conventions:

- A positive primary surplus reduces the debt ratio.
- The charted primary-balance contribution is therefore `-pb_t`.
- A positive stock-flow adjustment raises the debt ratio after accounting for
  the interest-growth term and primary balance.

Internal calculations use decimal ratios. Reporting columns ending in `_pp` or
`_pct_gdp` are display-boundary percentage-point or percent-of-GDP values.

Previous-year debt is required because the identity applies the effective
interest cost during year \(t\) to the debt stock inherited from \(t-1\). The
average-debt rate is useful for descriptive average-cost analysis but
is not the rate in this identity.

The stock-flow adjustment is a residual. It should not be interpreted as a
policy instrument or structural estimate.

Worked example:

- \(d_{t-1}=1.00\)
- \(d_t=0.95\)
- \(r_t^{DD}=0.03\)
- \(g_t=0.05\)
- \(pb_t=0.02\)

Then:

\[
\frac{0.03-0.05}{1.05}\times 1.00=-0.0190476.
\]

The primary-balance contribution is \(-0.02\). The observed debt-ratio change
is \(-0.05\). The residual is:

\[
sfa_t=-0.05-(-0.0190476)-(-0.02)=-0.0109524.
\]

The reconstructed change is:

\[
-0.0190476 - 0.02 - 0.0109524 = -0.05.
\]

Limitations: the identity combines ESA interest payable with Maastricht gross
debt. This is appropriate for transparent fiscal accounting but is not a full
debt-management portfolio model.
