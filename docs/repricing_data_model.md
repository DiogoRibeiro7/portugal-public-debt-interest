# Repricing panel: data model and limitations

Written before estimation, so the limitations are fixed in advance rather than
discovered in review. The design revision that produced this model is in
`docs/repricing_design_revision.md`.

## Unit of observation

**Instrument class by month.** Not individual holders, and not ISIN level.

Retail certificate data is published only as an aggregate outstanding stock, so
the finest available cell is a class-month. This is a real limitation and the
manuscript states it in the body, not in an appendix: an aggregate class-month
panel is not an individual-level model, and describing it as one would be a
misrepresentation.

Two classes are carried: `savings_certificates` (Certificados de Aforro,
2001-02 onward, 305 months) and `treasury_certificates` (Certificados do
Tesouro, 2010-08 onward, 191 months).

## Clock

**Calendar time only.** There is no duration clock.

The original design indexed hazards by time since subscription, because
lock-up and penalty structures are indexed to it. That clock belongs to a
survival model of redemptions. Since the redemption margin is not identified
from net stock, the hazard is gone and so is its clock. What remains is a flow
responding to contemporaneous conditions.

## Quantities

| Column | Meaning |
| --- | --- |
| `opening_outstanding_mio_eur` | Stock at the start of the month |
| `outstanding_mio_eur` | Stock at the end of the month |
| `net_flow_mio_eur` | Change over the month, subscriptions minus redemptions |
| `repriced_lower_bound_mio_eur` | `max(net_flow, 0)` |
| `net_outflow_mio_eur` | `max(-net_flow, 0)`, carried separately |
| `repriced_share` | Lower bound divided by opening stock |

### Why the lower bound is the estimable object

Money arriving on the prevailing rate reprices the stock whether it comes from
a new subscription or from a redemption and reissue. Only the net change is
observed. When net flow is positive, gross subscriptions are at least that
large, so the repriced amount is bounded below by an observable quantity.

The bound is one-sided and that asymmetry is deliberate. In a month of net
outflow the repriced amount is **not** bounded — subscriptions and redemptions
could both have been large — so those months are recorded as net outflow and
are not treated as zero repricing. Any estimate that used them as zeros would
be assuming exactly the thing the data cannot show.

## Covariates

| Column | Construction |
| --- | --- |
| `competing_return_spread_pp` | Short rate minus household deposit rate, lagged |
| `spread_widening_pp` | Positive part of the spread |
| `spread_narrowing_pp` | Negative part, entered separately |
| `post_policy_break` | Month after 2023-06 |
| `months_since_policy_break` | Signed distance from the break |
| `average_residual_term_years` | IGCP, monthly |
| `share_fixed_rate_pct` | IGCP, monthly; gives the reset-track residual |

**The spread is a proxy.** The certificate's own remuneration rate is not
published machine-readably, so a short-rate index stands in for the certificate
leg, on the grounds that the formula tracked short rates. Every result resting
on the spread inherits that caveat. The contractual rate is specified in
`docs/manual_ingest.md` as the input that would sharpen it.

Covariates are lagged one month, uniformly, so no estimate uses information a
household could not have observed at the decision point.

## The policy break

**2023-06.** Dated from the data rather than assumed: net flow falls from
+3,549 million in March 2023 to +670 in June, +39 by October, and turns
negative in November. A discrete change in the terms offered on new
subscriptions switched the channel off.

## Validation

Run by `pt-debt repricing build-panel`; output in
`reports/repricing/riskset_validation.md`.

- Unique class-month keys.
- Non-negative exposure.
- Accounting closure: opening plus net flow equals closing, exactly.
- Repriced share within `[0, 1]`.
- Reconciliation to the burden paper's debt stock, reported per year.

### On that reconciliation

IGCP State direct debt and the burden paper's Maastricht general-government
debt are **different concepts**, so they do not agree and are not expected to.
The gap moves from **+7.0 percent of Maastricht debt in 2001 to −14.6 percent
in 2025**: State direct debt now exceeds consolidated general-government debt,
which is consistent with intra-government holdings being netted out of the
Maastricht measure and growing over time.

The gap is reported per year rather than asserted away. A reader can see
whether it is stable; it is not, and that matters for anyone tempted to treat
the two papers' debt aggregates as interchangeable.
