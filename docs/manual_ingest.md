# Manual ingest specification

Inputs the repricing work needs that could **not** be acquired programmatically.
Nothing here is interpolated, approximated, or substituted. The pipeline halts
with a message naming the gap rather than filling it.

Place manually obtained files in `data/raw/manual/` using the filenames below.
A validated loader reads them; a file with the wrong schema fails loudly.

---

## 1. Dated contractual redemption schedule (Tier 1, blocking)

**Why it matters.** This is the single most important missing input. The
repricing kernel's contractual component is supposed to be read directly off a
dated redemption profile, not estimated. Without it there is no deterministic
track, and the contractual/stochastic split that the whole design rests on
cannot be built from published data.

- **Source**: IGCP, *Investor Presentation* or *Annual Report*, redemption
  profile chart, and the Monthly Bulletin's maturity profile table.
- **Reference**: <https://www.igcp.pt/en/investidores/boletim-mensal>
- **What is needed**: for each future calendar year, the amount of medium- and
  long-term debt contractually maturing, by instrument class.
- **Expected file**: `data/raw/manual/igcp_redemption_profile.csv`
- **Expected schema**:

  | column | type | notes |
  | --- | --- | --- |
  | `as_of_date` | date | vintage of the profile |
  | `maturity_year` | int | calendar year of redemption |
  | `instrument_class` | str | `OT`, `BT`, `MTN`, `official_loan`, `other` |
  | `amount_mio_eur` | float | contractual redemption in that year |
  | `source_page` | str | document page or chart reference |

**Status**: not obtained. Published as a chart in PDF, not as a table.

---

## 2. Gross retail subscriptions and redemptions (Tier 1, blocking for the
   behavioural hazard)

**Why it matters.** The acquired IGCP series gives the **net outstanding stock**
of Certificados de Aforro and Certificados do Tesouro. A redemption hazard
cannot be identified from net stock: a flat stock is equally consistent with no
activity and with large subscriptions exactly offsetting large redemptions.
Estimating a voluntary-redemption hazard requires the gross redemption flow.

- **Source**: IGCP Monthly Bulletin, retail instruments section; or Banco de
  Portugal BPstat household financial accounts.
- **What is needed**: monthly gross subscriptions and monthly gross redemptions,
  per certificate series.
- **Expected file**: `data/raw/manual/igcp_retail_flows.csv`
- **Expected schema**:

  | column | type | notes |
  | --- | --- | --- |
  | `period` | date | month end |
  | `instrument` | str | `certificados_aforro`, `certificados_tesouro` |
  | `series_code` | str | e.g. `E`, `F` for Aforro series |
  | `gross_subscriptions_mio_eur` | float | |
  | `gross_redemptions_mio_eur` | float | |
  | `outstanding_mio_eur` | float | reconciles against the acquired stock |

**Status**: not obtained programmatically.

---

## 3. Retail remuneration rates and contractual rules by series (Tier 1)

**Why it matters.** The return spread facing a holder is the paper's key
covariate, and the lock-up and penalty structure is what the baseline duration
dependence should reproduce. Both are contractual and knowable; they must be
encoded exactly, not approximated.

- **Source**: IGCP retail product pages and the dated announcements of rate
  formula changes.
- **What is needed**: per series, the remuneration formula, the index it tracks,
  any cap, the lock-up period, the early-redemption penalty schedule, the
  subscription limits, and the dates on which each changed.
- **Expected file**: `data/raw/manual/igcp_retail_terms.csv`
- **Expected schema**: `series_code`, `valid_from`, `valid_to`,
  `rate_formula`, `index_reference`, `cap_pct`, `lockup_months`,
  `penalty_rule`, `holding_cap_eur`, `source_reference`.

**Status**: not obtained programmatically.

---

## 4. Per-ISIN instrument detail (Tier 1, desirable)

**Why it matters.** ISIN-level issue date, maturity, coupon, and coupon type
would allow the marketable-securities risk set to be built at instrument level
rather than at class level, which materially strengthens the unit of
observation.

- **Source**: IGCP securities pages; commercial terminals hold this in
  structured form.
- **Expected file**: `data/raw/manual/igcp_securities.csv`
- **Expected schema**: `isin`, `instrument_class`, `issue_date`,
  `maturity_date`, `coupon_pct`, `coupon_type`, `amount_outstanding_mio_eur`,
  `currency`.

**Status**: not obtained. Not published as a machine-readable table.

---

## 5. Official-sector loan amortisation (Tier 1)

**Why it matters.** EFSF and ESM early repayments are lumpy, discretionary, and
policy-driven. They are carried as a documented discrete event series, not as an
estimated hazard — there are far too few events for the latter.

- **Source**: IGCP Annual Report; EFSF and ESM published loan schedules.
- **Expected file**: `data/raw/manual/official_loan_events.csv`
- **Expected schema**: `lender`, `tranche_id`, `event_date`, `event_type`
  (`scheduled_amortisation` or `early_repayment`), `amount_mio_eur`,
  `source_reference`.

**Status**: aggregate programme-loan stock is available in the acquired IGCP
indicators; tranche-level detail is not.

---

## 6. Portuguese HICP and household financial accounts (Tier 2/3)

- **Source**: Eurostat `prc_hicp_midx` for prices; Banco de Portugal BPstat for
  household deposits and debt-securities holdings.
- **Status**: not yet wired. Eurostat is already a dependency of the burden
  pipeline and can be added without a new source family; BPstat requires
  assessment.

---

## 7. IGCP refixing profile (Tier 1, validation of the imposed shape)

**Why it matters.** The kernel's contractual and reset shapes are *imposed*: a
linear retirement profile at the published weighted average maturity, an annual
wholesale reset cycle, and a quarterly retail reset cycle. The ESDM refixing
risk windows provide an external benchmark against the debt manager's own view.

IGCP publishes that view in its investor presentation. Its risk framework
monitors interest-rate refixing explicitly, and the presentation reports ESDM
refixing-risk windows: the fraction of outstanding debt due to be refixed or
to mature within a stated horizon. That is the closest published object to the
kernel this paper constructs, and it is a stronger comparator than weighted
average maturity alone.

The current CSV records the two labelled Portugal values from the May 2026
presentation: the one-year window and the cumulative five-year window. It does
not provide a dated instrument-level schedule.

- **Source**: IGCP, *Investor Presentation*, May 2026, slide 32.
- **Reference**: <https://www.igcp.pt/sites/default/files/2026-05/IGCP_Investor_Presentation.pdf>
- **What is needed**: for each published window, the share of outstanding debt
  refixing or maturing within it, at a stated reference date.
- **Provided file**: `data/raw/manual/igcp_refixing_profile.csv`
- **Accepted sources**: labelled official bracket values, if published, or a
  genuine digitisation of the official refixing-profile chart. Do not infer
  values from the visual appearance of a chart without recording the
  digitisation source and method.
- **Expected schema**:

  | column | type | notes |
  | --- | --- | --- |
  | `reference_date` | date | reference date of the profile |
  | `bracket_lower_years` | float | inclusive lower edge of the bracket |
  | `bracket_upper_years` | float | upper edge of the cumulative window |
  | `share_of_portfolio` | float | fraction refixing within the window, 0--1 |
  | `source_title` | str | source document |
  | `source_url` | str | stable source URL |
  | `source_detail` | str | slide and chart detail |

**Status**: obtained for the two official ESDM windows. The comparison is
implemented in `refixing_comparison` in `src/pt_debt/repricing/kernel.py` and
is included in the generated manuscript tables. Gross retail subscriptions and
redemptions remain unavailable.
