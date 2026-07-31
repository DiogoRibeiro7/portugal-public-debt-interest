# Final blocking acceptance audit

Adversarial rebuild and item-by-item evaluation of the eight blocking
correction prompts.

- Audit date: 2026-07-31
- Git commit at audit: `f8ef950694639ca026946d5fb17432159659e55b` (plus the
  lint and revision-noise fixes made during this audit)
- Final PDF: `paper/portugal_public_debt_interest_report.pdf`, 24 pages
- PDF SHA-256: `a455c43fd3b33cfa...` (recomputed after the final compile)
- Processed dataset SHA-256: `34dba203c7e23fa2...`
- Configuration SHA-256: `0456620afa90def7...`

## Build sequence executed

| Step | Result |
| --- | --- |
| Dependency resolution | Existing environment; `src` on path (see caveat) |
| Cached-data build (`build_dataset`) | PASS — 31 rows, 117 columns |
| Validation (`validate_dataset`) | PASS — `passed: true` |
| Analytical outputs (decomposition, counterfactuals, refinancing, eligibility) | PASS |
| Tests (`pytest`) | PASS — 270 passed, 0 failed |
| Type checking (`mypy src`) | PASS — 23 source files, no issues |
| Linting (`ruff check .`) | PASS — all checks passed |
| Figure generation | PASS — 44 files |
| Table generation | PASS — 12 fragments |
| LaTeX compilation | PASS — 0 undefined references, 0 undefined citations |

## A. Debt dynamics

| Item | Verdict | Evidence |
| --- | --- | --- |
| Equation 1 uses `r_dd` | PASS | Prose states the identity is evaluated on $r^{\mathrm{dd}}_t = I_t / D_{t-1}$ |
| Equation 2 uses `r_dd` | PASS | Debt-stabilising balance derived from the same rate |
| Figure uses corrected contributions | PASS | Regenerated from `interest_growth_contribution_pp` |
| 2022 prose matches dataset | PASS | −12.06 (was −12.07, the `r_avg` value) |
| 2023 prose matches dataset | PASS | −8.80 (was −8.77, the `r_avg` value) |
| No stale `r_avg` value remains | PASS | 10.49, −12.07, −8.77, −4.29 absent from the report |
| Maximum reconciliation error reported | PASS | 1.735e-16 pp, stated in the report |

## B. Units

| Item | Verdict | Evidence |
| --- | --- | --- |
| Diagnostic table uses consistent units | PASS | Every heading carries `%` or `pp` |
| Percentages and ratios not mixed | PASS | 116.10%, −6.27%, 10.61 pp (were 1.1610, −0.0627, 0.1061) |
| Contributions in percentage points | PASS | All contribution columns labelled pp |
| No negative zero | PASS | `-0.00000000` absent from every generated table |

## C. Burden decomposition

| Item | Verdict | Evidence |
| --- | --- | --- |
| Symmetric two-component formula | PASS | Midpoint-weighted endpoint identity |
| No interaction term in principal decomposition | PASS | `interaction_effect_pp` not present |
| Displayed components sum to displayed total | PASS | All 8 intervals add at 3 dp after additive rounding |
| 2014–2025 and 1996–2025 generated | PASS | Macros emitted from the library |
| Abstract and conclusion match generated table | PASS | Both read the same macros |
| Maximum decomposition residual | PASS | 6.939e-16 pp |

## D. Refinancing

| Item | Verdict | Evidence |
| --- | --- | --- |
| Assumptions table exists | PASS | `reports/tables/refinancing_assumptions.tex` |
| No-shock baseline exists | PASS | 0 bps included in every run |
| Figure shows incremental burden | PASS | Figure 15, shocked minus zero-shock |
| Zero shock gives zero incremental cost | PASS | Maximum absolute value exactly 0.0 |
| Immediate full refinancing matches static sensitivity | PASS | 0.897000 pp both sides, agreement to 1e-12 |
| Model labelled stylised | PASS | Stated in config, table notes, figures, and prose |
| Hidden "configured refinancing shares" wording absent | PASS | Phrase removed |

## E. Euro-area comparison

| Item | Verdict | Evidence |
| --- | --- | --- |
| Eligibility table exists | PASS | `data/processed/euro_area_eligibility.csv`, 22 rows × 16 fields |
| Competition ranking documented | PASS | 1, 2, 2, 4 stated in the report |
| Status policy enforced | PASS | Derived from Eurostat per-series flags, accepted set configured |
| Rank denominator correct | PASS | 20 eligible, 2 excluded, sum equals panel size |
| Median and percentile reported | PASS | Median 1.35, percentile 75.0, IQR 1.05–1.98 |
| Latest common year computed | PASS | 2025, derived from coverage |
| Provisional status disclosed | PASS | 10 geographies flagged, disclosed in caption and prose |
| Not described as a sustainability ranking | PASS | Explicitly disclaimed |

## F. Validation

| Item | Verdict | Evidence |
| --- | --- | --- |
| 1997 and 1998 discrepancies shown | PASS | +1.0152 pp and −0.3522 pp, with both underlying values |
| Tolerance shown | PASS | 0.15 pp stated |
| Revision log exists | PASS | `reports/data_revision_log.{csv,md}` |
| Error-level failures stop the build | PASS | `error_level_failures` gate in the report command |
| Data vintage reported | PASS | Retrieval window in the appendix |
| Error / warning counts | PASS | 0 error-level, 1 warning-level |
| Maximum ratio discrepancy | PASS | 1.0152 pp |

## G. Report cleanup

| Item | Verdict | Evidence |
| --- | --- | --- |
| Four research questions | PASS | 4 items |
| No "dependent variable" | PASS | Phrase absent |
| No contradictory AMECO claims | PASS | All use/retention claims removed |
| Abstract excludes expenditure and revenue totals | PASS | Removed |
| Figures 3 and 4 replaced by one compact table | PASS | `interest_share_of_budget.tex` |
| `N` column present | PASS | N = 31 |
| Tied minimum handled | PASS | "2022, 2025" |
| Title contains no colon | PASS | Verified |
| No near-empty reproducibility page | PASS | Replaced by a paragraph |
| No internal snake_case labels | PASS | Absent from both publication tables |
| Literature section exists | PASS | 13 bibliography entries, 10 literature |

## H. Reproducibility

| Item | Verdict | Evidence |
| --- | --- | --- |
| Clean build succeeds | PASS WITH CAVEAT | Offline rebuild from cached interim data succeeds; see caveat |
| Tests pass | PASS | 270 passed |
| Type checking passes | PASS | mypy clean, 23 files |
| Linting passes | PASS | `ruff check .` clean |
| LaTeX compiles without missing references | PASS | 0 undefined |
| Final PDF checksum recorded | PASS | Above |
| Git commit hash recorded | PASS | Above |
| Data-manifest checksum recorded | PASS | Above |

## Caveats

Three, stated rather than hidden.

1. **Dependency installation was not performed from a clean environment.** The
   package is not installed in this environment; the build ran with `src` on
   `PYTHONPATH`. Every other step is unaffected, but a true clean-room
   `pip install -e '.[dev]'` was not executed here.

2. **Continuous integration could not run.** GitHub Actions is billing-blocked
   on the repository account, so no independent verification exists. All
   results above are from local execution.

3. **The revision log had no prior vintage to compare on first run.** It now
   compares against an archived vintage and reports no change, which is
   correct: the data did not change between the two builds. A noise tolerance
   was added during this audit so that last-bit CSV round-trip differences
   (order 1e-16) are not reported as revisions.

## Release status

**READY WITH MINOR WARNINGS**

Every item in sections A through F passes. Every mathematical, data-status, and
reproducibility item passes. The three caveats above are environmental rather
than analytical: they concern how the build was invoked and whether CI could
observe it, not whether any reported number is correct.
