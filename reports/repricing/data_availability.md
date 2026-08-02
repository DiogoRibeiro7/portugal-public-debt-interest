# Repricing data availability

What was actually acquired, at what frequency, over what span — and what was
not. Generated coverage figures come from the cached payloads under
`data/raw/repricing/`; every payload has a provenance sidecar recording its
source URL, retrieval timestamp, size, and SHA-256.

Acquire with `pt-debt repricing acquire --config config/repricing.yaml`.

---

## Tier 1 — the stock and its composition

### Obtained, machine-readable

Source: IGCP historical-series workbooks, monthly.

| Series | Span | Observations |
| --- | --- | --- |
| Total State direct debt | 2001-01 .. 2026-06 | 306 |
| Fixed-rate Treasury bonds (OT) | 2001-01 .. 2026-06 | 306 |
| **Savings certificates (Certificados de Aforro)** | 2001-01 .. 2026-06 | 306 |
| **Treasury certificates (Certificados do Tesouro)** | 2010-07 .. 2026-06 | 192 |
| Cash-collateral accounts | 2011-03 .. 2026-06 | 184 |
| Share of fixed-rate debt (%) | 2000-12 .. 2026-06 | 307 |
| Share of euro-denominated debt (%) | 2000-12 .. 2026-06 | 307 |
| **Average residual maturity (years)** | 2000-12 .. 2026-06 | 307 |
| Modified duration | 2000-12 .. 2026-06 | 307 |

Two things here are better than expected. The retail split is available
monthly for a quarter century, which is what makes the behavioural channel
observable at all. And average residual maturity is monthly, not annual, so the
weighted-average-maturity benchmark the paper critiques can be reconstructed at
the same frequency as everything else rather than interpolated.

The share of fixed-rate debt gives the floating and inflation-linked residual,
which the framework carries on the separate reset track.

### Not obtained

| Item | Status |
| --- | --- |
| **Dated contractual redemption schedule** | **Not obtained.** Published as a chart in PDF, not as a table. |
| **Gross retail subscriptions and redemptions** | **Not obtained.** Only net outstanding stock is published. |
| Retail remuneration rates and penalty rules by series | Not obtained programmatically. |
| Per-ISIN detail (issue date, maturity, coupon, coupon type) | Not published as a machine-readable table. |
| BT (Bilhetes do Tesouro) stock, separately | Not in these workbooks. |
| EFSF/ESM tranche-level amortisation and early repayments | Only aggregate programme-loan stock. |

Each has a manual-ingest specification in `docs/manual_ingest.md` with the
exact source, expected filename, and expected schema.

---

## Tier 2 — covariates driving the behavioural hazard

Source: ECB Data Portal REST API, SDMX-JSON. All fetched successfully.

| Series | Observations |
| --- | --- |
| Deposit facility rate (policy) | 10,074 |
| PT household deposit rate, outstanding amounts | 318 |
| PT household deposit rate, new business | 318 |
| PT household deposit rate, overnight | 282 |
| Euro-area yield curve, 10-year | 5,598 |
| Euro-area yield curve, 2-year | 5,598 |

The household deposit rate is the principal competing return for a retail
certificate holder and is the key covariate of the paper. Overnight deposits
were added as the closest substitute for an on-demand redeemable certificate.

### Not yet wired

- Portuguese sovereign yield curve at several maturities. The burden pipeline
  already pulls the ten-year from Eurostat; additional maturities are available
  and not yet configured.
- Portuguese HICP. Available from Eurostat, an existing dependency.
- Euribor. Available from the ECB; not yet configured.

---

## Tier 3 — context

Household financial accounts (deposits and debt-securities holdings) from Banco
de Portugal BPstat: **not assessed.** BPstat's programmatic interface has not
been evaluated.

---

## Parser robustness

The IGCP workbooks change header format part-way through: real Excel dates to
2020-10, then abbreviated month labels mixing Portuguese and English
(`Nov/20`, `Dez/20`, `Fev/21`). A first implementation that trusted pandas date
inference silently dropped every period from 2020-11 onward and produced a
coverage table that looked plausible and was wrong by six years.

The parser now maps both representations explicitly and **raises** on any
unrecognised period label rather than dropping it, so a future format change
halts the build instead of shortening the series. Regression tests cover the
mixed header, the footnote rows that repeat series names without carrying
numbers, and the missing-series case.
