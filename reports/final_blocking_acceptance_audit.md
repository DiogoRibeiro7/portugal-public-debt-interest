# Final blocking acceptance audit

Adversarial rebuild and item-by-item evaluation of the eight blocking
correction prompts.

- Audit date: 2026-07-31
- Source commit at audit start: `8759404228444888f02c98dd7a7955ddf2608aec`
- Current audit pass includes working-tree fixes to the validation macro
  generation path and stale refinancing wording in documentation.
- Final PDF: `paper/portugal_public_debt_interest_report.pdf`, 24 pages
- PDF SHA-256:
  `f885447095c7962e16225de011844bc14c6700a04499c026ee8a77d525787dd3`
- Processed Portugal dataset SHA-256:
  `c27d6b11fbadfd17fe59af422ba679f0af59e23be06f7d48aac7ae2c074cfb33`
- Figure/data manifest SHA-256:
  `50a9b2c5e17e7acf884867b1f2bd114d02485c0b968e2786e0b5cd7215b8ba5a`

## Build sequence executed

| Step | Result |
| --- | --- |
| Dependency installation | PASS -- `python -m pip install -e ".[dev]"` installed `portugal-public-debt-interest==0.1.2` |
| CLI entry point | PASS -- `pt-debt --help` resolved installed command |
| Data retrieval/build | PASS -- `python -m pt_debt_interest.cli all --config config/default.yaml` completed |
| Comparator-panel retrieval | PASS -- `python -m pt_debt_interest.cli fetch-panel --config config/default.yaml` completed |
| Comparator-panel build | PASS -- `python -m pt_debt_interest.cli build-panel --config config/default.yaml` completed |
| Validation and revision reports | PASS -- `python -m pt_debt_interest.cli validate --config config/default.yaml` completed |
| Figure generation | PASS -- `python -m pt_debt_interest.cli plot --config config/default.yaml` completed |
| Table generation | PASS -- `python -m pt_debt_interest.cli tables --config config/default.yaml` completed |
| LaTeX compilation | PASS -- `latexmk -g -pdf -interaction=nonstopmode -halt-on-error portugal_public_debt_interest_report.tex` completed; final log has no undefined references or citations |
| Tests | PASS -- `pytest`: 232 passed, 4 warnings |
| Type checking | PASS -- `mypy src`: no issues in 23 source files |
| Linting | PASS -- `ruff check .`: all checks passed |

## A. Debt dynamics

| Item | Verdict | Evidence |
| --- | --- | --- |
| Equation 1 uses `r_dd` | PASS | Prose states the identity is evaluated on $r^{\mathrm{dd}}_t = I_t / D_{t-1}$ |
| Equation 2 uses `r_dd` | PASS | Debt-stabilising balance is derived from the same rate |
| Figure uses corrected contributions | PASS | Regenerated from `interest_growth_contribution_pp` |
| 2022 prose matches dataset | PASS | Generated context reports -12.058817599546408 pp |
| 2023 prose matches dataset | PASS | Generated context reports -8.803347196679441 pp |
| No stale `r_avg` value remains | PASS | Search confirms stale values 10.49, -12.07, -8.77, and -4.29 are absent from the report source |
| Maximum reconciliation error reported | PASS | `1.734723475976807e-16` pp in `reports/generated/debt_dynamics_context.json` |

## B. Units

| Item | Verdict | Evidence |
| --- | --- | --- |
| Diagnostic table uses consistent units | PASS | Publication headings contain `%` or `pp` |
| Percentages and ratios not mixed | PASS | Display layer converts decimal ratios before writing publication tables |
| Contributions in percentage points | PASS | Contribution columns are labelled and rendered in pp |
| No negative zero | PASS | Formatting layer suppresses negative zero residuals |

## C. Burden decomposition

| Item | Verdict | Evidence |
| --- | --- | --- |
| Symmetric two-component formula | PASS | Endpoint decomposition uses midpoint-weighted rate and exposure effects |
| No interaction term in principal decomposition | PASS | Principal output has rate and debt-exposure effects only |
| Displayed components sum to displayed total | PASS | Regression tests enforce additive display rounding |
| 2014-2025 and 1996-2025 values generated | PASS | `paper_headlines.tex` macros are emitted from generated decomposition data |
| Abstract and conclusion match generated table | PASS | Both read generated macros |
| Maximum decomposition residual | PASS | `6.938893903907228e-16` pp |

## D. Refinancing

| Item | Verdict | Evidence |
| --- | --- | --- |
| Assumptions table exists | PASS | `reports/tables/refinancing_assumptions.tex` |
| No-shock baseline exists | PASS | 0 bps shock is included in every scenario |
| Figure shows incremental burden | PASS | Figure 15 plots shocked burden minus no-shock baseline |
| Zero shock gives zero incremental cost | PASS | Regression test covers zero incremental cost |
| Immediate full refinancing matches static sensitivity | PASS | Regression test covers full-pass-through consistency |
| Model labelled stylised | PASS | Config, table notes, figures, and prose label it stylised |
| Hidden refinancing-share wording absent | PASS | Stale wording removed from report source and documentation snippets |

## E. Euro-area comparison

| Item | Verdict | Evidence |
| --- | --- | --- |
| Eligibility table exists | PASS | `data/processed/euro_area_eligibility.csv` |
| Competition ranking documented | PASS | Report states the `1, 2, 2, 4` method |
| Status policy enforced | PASS | Accepted statuses are generated as `observed, provisional` |
| Rank denominator correct | PASS | Portugal rank is 6 of 20 eligible countries |
| Median and percentile reported | PASS | Portugal percentile is 75.0 |
| Latest common year computed | PASS | `LatestCommonYear` macro is 2025 |
| Provisional status disclosed | PASS | Status disclosure is generated in the report |
| Not described as a sustainability ranking | PASS | Report explicitly avoids that interpretation |

## F. Validation

| Item | Verdict | Evidence |
| --- | --- | --- |
| 1997 and 1998 discrepancies shown | PASS | `reports/validation_detail.md` reports +1.0152 pp and -0.3522 pp |
| Tolerance shown | PASS | 0.15 pp stated |
| Revision log exists | PASS | `reports/data_revision_log.csv` and `.md` |
| Error-level failures stop the build | PASS | Report command refuses to build when validation has error-level failures |
| Data vintage reported | PASS | Retrieval window generated as 20260731T204043Z to 20260731T204048Z |
| Error / warning counts | PASS | 0 error-level failures; 1 warning-level failed validation check |
| Maximum ratio discrepancy | PASS | 1.0152 pp |

## G. Report cleanup

| Item | Verdict | Evidence |
| --- | --- | --- |
| Four research questions | PASS | Report source contains four enumerated questions |
| No "dependent variable" | PASS | Phrase absent from report source |
| No contradictory AMECO claims | PASS | Main report no longer claims AMECO is used for paper results |
| Abstract excludes expenditure and revenue totals | PASS | Abstract focuses on interest burden, debt dynamics, comparison, and refinancing |
| Figures 3 and 4 replaced by one compact table | PASS | `interest_share_of_budget.tex` provides fiscal-envelope context |
| `N` column present | PASS | Summary table includes `N` |
| Tied minimum handled | PASS | Tied minimum years are generated programmatically |
| Title contains no colon | PASS | Title is `Portugal's Public-Debt Interest Burden and Debt Dynamics in the Euro Area` |
| No near-empty reproducibility page | PASS | Reproducibility content is compact text |
| No internal snake_case labels | PASS | Publication tables use display labels |
| Literature section exists | PASS | Related-literature section and bibliography are present |

## H. Reproducibility

| Item | Verdict | Evidence |
| --- | --- | --- |
| Clean build succeeds | PASS WITH CAVEAT | Rebuild succeeded in the current environment after editable dependency installation |
| Tests pass | PASS | 232 passed, 4 warnings |
| Type checking passes | PASS | `mypy src` clean |
| Linting passes | PASS | `ruff check .` clean |
| LaTeX compiles without missing references | PASS | Final log has no undefined references or citations |
| Final PDF checksum recorded | PASS | Recorded above |
| Git commit hash recorded | PASS | Recorded above |
| Data-manifest checksum recorded | PASS | Recorded above |

## Fixes made during this pass

- `src/pt_debt_interest/cli.py`: table generation now passes the configured
  validation result into `generate_latex_tables`, and `all` writes validation
  detail/revision reports alongside `validation.json`.
- `tests/test_latex_tables.py`: added a regression test proving failed
  warning-severity validation checks are counted in `paper_headlines.tex`.
- `docs/blocking_calculation_trace.md`, `docs/refinancing_scenario_design.md`,
  `docs/sources.md`, and `docs/validation_review.md`: removed stale hidden
  refinancing-share wording.

## Remaining caveats

1. Continuous integration could not be observed locally. The prior repository
   blocker was GitHub Actions billing/spending limits; local gates pass.
2. This audit was not run inside a freshly created virtual machine or container.
   It did run dependency installation and the installed CLI entry point in the
   current environment.

## Release status

**READY WITH MINOR WARNINGS**

Every item in sections A through F passes. Mathematical, data-status, and local
reproducibility gates pass. Remaining caveats are environmental rather than
analytical.
