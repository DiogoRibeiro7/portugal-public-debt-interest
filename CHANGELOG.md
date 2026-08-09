# Changelog

## v0.6.2 - 2026-08-09

Revision-8 minor-review release.

### Changed

- Reframed the repricing paper's contribution against established Average Time
  to Re-fixing and ESDM refixing-risk practice, adding IMF, ESDM and BIS
  references.
- Corrected the Savings Certificate 2022--2023 headline to describe the EUR
  3,549 million value as the largest monthly increase in outstanding value, not
  an observed inflow.
- Relabelled kernel figures and generated plotting code to use pass-through
  exposure terminology where behavioural new-funding exposure enters the
  plotted object.
- Updated code comments and semantic tests to match the current descriptive,
  not behaviourally identified, retail-flow interpretation.
- Recorded the revision-8 clean source archive result in the final audit.

## v0.6.1 - 2026-08-09

Revision-7 cleanup release after the same-date ESDM and opening-stock kernel
fixes in v0.6.0.

### Corrected

- Removed remaining forecast-comparison wording from the repricing paper,
  simulation docstring, specification log, and final audit. The historical
  exercise is now described consistently as conditional historical validation.
- Added a direct interpretation of the official ESDM comparison: the scenario
  kernel is closer in the one-year window, while WAM is closer in the five-year
  cumulative window. The paper now treats that mixed pattern as evidence that
  weighted average maturity is not a sufficient statistic, not as a claim that
  the scenario kernel is uniformly superior.
- Updated release metadata and the Zenodo description so the reset-timing
  result matches the generated sensitivity table: reported reset-timing
  alternatives leave the one-year sign positive; weaker shock loading reverses
  it.

### Verification

- Regenerated the repricing manuscript artefacts.
- Rebuilt `paper/repricing/repricing_kernel.pdf`; the PDF is 15 pages and
  retains only one harmless underfull bibliography line.
- `pytest -q`, focused repricing tests, `ruff check src tests`, and `mypy src`
  passed in the author working tree before release.

## v0.6.0 - 2026-08-08

Fourth-round review. Five of six mandatory items on the repricing paper are
closed; the sixth is blocked on an input and is named below rather than
glossed. The burden paper's remaining asks are closed.

### Corrected

- **The behavioural coefficient was applied to the wrong variable.** It is
  estimated against the lagged competing-return spread, but the historical
  validation drove it with the gap between the ten-year benchmark and the
  cut-date effective rate: a response in repriced share per point of
  competing-return spread applied to something closer to a term premium. It is
  now driven by the realised competing-return spread, and where that variable
  is unavailable the behavioural track is left at zero rather than fed a
  stand-in.
- **The portfolio partition overlapped.** Retail and rate type cut across each
  other in this portfolio: Savings Certificates are retail *and* variable-rate,
  Series F indexed to three-month Euribor, while Treasury Certificates are
  retail and carry a guaranteed fixed schedule. The kernel subtracted the whole
  retail block from the fixed-rate track and simultaneously treated the whole
  non-fixed residual as a reset block, so Savings Certificates were removed
  from a track they were never on and counted on another. The opening stock is
  now partitioned into four mutually exclusive classes summing to one, each
  with its own repricing law, and the construction raises rather than clipping
  if the shares imply a negative class.

  The correction does not move the headline. At annual horizons the repriced
  share is unchanged, because the retail block received the same contractual
  profile either way. What changes is that it was reported in the behavioural
  column, which overstated behaviour and understated contractual repricing.
  Behaviour is now purely a flow, zero at the central case. Since the paper's
  shape-versus-behaviour split rests on that decomposition, the fix matters
  even though the total does not.

  One consequence is visible only once the classes separate: wholesale floating
  is 0.8 percent of the stock. Nearly all non-fixed debt is retail.

- **The retail outcome is no longer described as a lower bound on
  subscriptions.** The published series is outstanding value, which for Savings
  Certificates is subscription principal plus capitalised interest. Series F
  capitalises, so the accrual term is positive by construction and can create a
  positive change with no new household money; IGCP's 2024 accounts put the
  year's increase at EUR 684 million, of which 63 was subscription value and
  622 accrued interest. Because capitalisation tracks a Euribor-indexed
  formula, the outcome can move with rates through pure accounting, in the same
  direction as the behavioural channel under test. **This is disclosed, not
  removed:** the regression still runs on that series, and its coefficient is
  reported as descriptive rather than identified.

### Changed

- The central object is renamed a **composition-sensitive scenario kernel**.
  Its contractual profile, reset cycle and shock loading are imposed and its
  behavioural centre is zero, so "estimated kernel" claimed more than it
  delivered.
- The historical exercise is renamed **conditional historical validation**.
  Realised rate paths are fed in deliberately, and a forecast would not have
  them. Its ordering has now changed four times across four implementation
  corrections without the specification changing once, and the paper reports
  that instability rather than the current ordering.
- Stale conclusions purged. The specification log recorded S1 as a null with a
  placebo that does not load, the estimation report was titled "a well-measured
  null" above a table of significant coefficients, and the manuscript and two
  module docstrings agreed. All now state that several associations are
  precisely estimated while the behavioural interpretation is not identified.
- The audit records both test environments. "353 passed" was true of a
  populated tree and not of what a reviewer receives.

### Added

- `refixing_comparison`, which checks the imposed kernel shape against IGCP's
  published refixing profile. IGCP's risk framework monitors interest-rate
  refixing explicitly, and that profile is a closer comparator to this kernel
  than weighted average maturity.

### Refixing benchmark

The refixing comparison now uses a tracked official manual input:
`data/raw/manual/igcp_refixing_profile.csv`. The file records Portugal's
labelled ESDM one-year and five-year refixing-risk windows from IGCP's May 2026
investor presentation, reference date end-March 2026. The repricing manuscript
includes the generated comparison table and no longer treats the refixing
profile as absent.

### Verification

- `pytest`: 371 passed in a populated tree after the refixing benchmark fix; reviewer
  clean-checkout audit of the prior revision-6 archive reported 345 passed and
  19 skipped, with zero failures.
- `ruff check .`: passed. `mypy src`: passed, 35 modules.
- Burden paper 27 pages, repricing paper 15 pages, no undefined references.

## v0.5.2 - 2026-08-08

Support documentation only. No code, results or manuscript text change.

### Fixed

- **`reports/repricing/estimation.md` still printed the stacked-panel fit.**
  494 observations, R-squared 0.041, spread widening +0.0187 at p = 0.20, and
  the standing conclusion that no coefficient is distinguishable from zero. All
  superseded by the corrected monthly estimator in v0.5.0: 304 observations,
  R-squared 0.343, +0.0214 at p = 0.0004.
- **Its falsification section read the wrong way round.** It reported the
  placebo at p = 0.86 as reassurance. On the corrected estimator the fixed-rate
  share loads at p = 0.07 — a statistic no household observes gaining weight at
  the same time as the main coefficient became significant, which is the
  signature of common time variation the specification cannot separate from the
  spread. That is now the report's headline rather than a footnote, and it is
  the stated reason the coefficient is descriptive rather than identified.
- **`docs/specification_log.md` carried the original backtest table**, two
  generations out of date, alongside the claim that the kernel wins narrowly at
  two cuts. It now shows the current figures and records why they moved twice
  while the specification did not: both revisions were implementation defects,
  so "Total specifications estimated: one" still stands.

Regime stability and the two pre-registered predictions that turned on
precision are updated alongside.

### Verification

- `pytest`: 353 tests passed.
- `ruff check .`: passed. `mypy src`: passed, 35 modules.
- No prose file states a superseded figure except where explicitly describing
  what changed.

## v0.5.1 - 2026-08-08

Archive metadata only. No code, results or manuscript text change.

### Fixed

- **The archive description claimed an input the build does not use.** It
  advertised "AMECO-linked historical context"; the extension is configured but
  contributes no rows, the built dataset carries Eurostat as its only source
  family, and neither paper cites AMECO. Removed from `.zenodo.json` and
  `CITATION.cff`, with the sources each paper actually uses named instead.
- **The title described one paper when the archive holds two.** "Portugal
  Public-Debt Interest Burden" now reads "Portugal's Public-Debt Interest
  Burden and Repricing: Pipeline, Data and Two Papers".

### Changed

- The archive description now says what each paper establishes, rather than
  listing pipeline features. Someone landing on the Zenodo record from a
  citation can tell what the two studies claim without opening them.
- `notes` records the reproducibility regime on the archive record itself:
  live-source rather than frozen-source, what is guaranteed, and what is not.
  Previously that distinction existed only in the repository.
- Keywords extended from seven to fifteen so the repricing study is
  discoverable: weighted average maturity, interest-rate pass-through, debt
  repricing, sovereign debt maturity, retail government debt, euro area, debt
  management, reproducible research.
- `related_identifiers` links the record to the source repository.
- `CITATION.cff` carries the same title, abstract and keywords, so the
  reference-manager entry and the archive record no longer disagree.

### Verification

- `pytest`: 353 tests passed.
- `ruff check .`: passed. `mypy src`: passed, 35 modules.

## v0.5.0 - 2026-08-08

This release supersedes v0.4.0, whose release notes misstate two results.
v0.4.0 reported the backtest favouring the benchmark at every cut date and the
behavioural estimation as a null. Both were artefacts of defects fixed here.
Cite this release rather than v0.4.0.

### Corrected results

- **The behavioural estimation was run on a mis-ordered panel.** The repricing
  panel is sorted by instrument class then period, so every month of one class
  preceded every month of the other and calendar time jumped backwards at the
  boundary: a twelve-month bootstrap block could straddle a fifteen-year gap,
  and the Newey-West lag structure did not correspond to month-to-month
  dependence. Each class-month also carried equal weight regardless of the
  euros behind it. Estimation now runs on the two retail classes aggregated to
  one euro-weighted monthly series. The spread-widening term moves from +0.0187
  (se 0.0148, p = 0.20) on 494 stacked rows to **+0.0214 (se 0.0061,
  p < 0.001)** on 304 months, and R-squared from 0.041 to 0.343.
- **That is still not a finding.** The asymmetry the design turns on remains
  inside [-0.016, +0.046], and the placebo no longer passes cleanly: the
  fixed-rate share, which no household observes, now loads at **p = 0.07**
  against 0.86 before. That points to common time variation the specification
  cannot separate from the spread, so the coefficient is reported as
  descriptive rather than identified. The kernel's central behavioural effect
  stays at zero.
- **The backtest changed again.** The model labelled "estimated kernel" now
  receives the fitted response instead of zero; previously the model carrying
  the name of the estimate was not using it. It wins at the 2021 cut, **9.24
  against 9.81 basis points**, and loses at 2014 and 2018. That is the cut
  containing the tightening episode, the only place a behavioural channel has
  anything to do, and it rests on four annual observations.

### Added

- **Shock loading is a parameter, separate from reset timing.** The kernel put
  the whole non-fixed residual on a one-year, one-for-one reset track, bundling
  how often a coupon refreshes with how much of a shock it passes through. The
  kernel now reports a physical repriced share and a shock-weighted share,
  which coincide at unit loading; the default is unit loading, so no existing
  number moved. Varying loading alone moves the one-year difference from +6.60
  to -0.50 percentage points at half loading and -4.05 at quarter loading, so
  it is as first-order as timing. This sharpens the paper's argument: a
  published maturity statistic constrains neither, so it cannot pin down the
  sign of the one-year correction.

### Documentation

- **The reproducibility regime is stated rather than left to inference.** This
  repository provides live-source reproducibility. Guaranteed: determinism
  given fixed inputs, drift detection through a 30-artefact checksum baseline,
  per-payload provenance, and a recorded retrieval vintage per release. Not
  guaranteed: that a later run reproduces published figures to the last
  decimal, because the providers revise their series.

### Verification

- `pytest`: 353 tests passed.
- `ruff check .`: passed. `mypy src`: passed, 35 modules.
- Burden paper 27 pages, repricing paper 14 pages, no undefined references.

## v0.4.0 - 2026-08-07

A published result changed. Read the first section before citing the previous
release.

### Corrected results

- **The out-of-sample backtest now favours the benchmark at every cut date.**
  Mean absolute error, estimated kernel against the constant-hazard proxy:
  46.91 vs 43.24 at 2014, 13.79 vs 12.92 at 2018, 11.14 vs 9.81 at 2021. The
  previous release reported the kernel winning two of three cuts. That ranking
  was an artefact of three defects, all fixed here. The contribution of the
  repricing paper is unaffected: it is that weighted average maturity does not
  determine a unique repricing path, not that this kernel forecasts better.

### Fixed

- **The backtest silenced its own behavioural channel.** `build_kernel` derives
  the behavioural contribution from the shock, so building it at `shock_bps=0`
  zeroed that track whatever response was passed. The manuscript nevertheless
  discussed where "a behaviourally responsive kernel should have won". It was
  not testing one.
- **The backtest was not vintage-consistent.** Each year's yield was applied to
  the whole cumulative repriced share, so debt that repriced in year one was
  revalued at the year-two yield when scoring horizon two. Repricing is now
  accumulated by cohort, `r_h = (1-K_h) r_0 + sum_{j<=h} dK_j y_j`. The two
  formulations agree only on a flat yield path.
- **The backtest used the end-of-sample portfolio state at every cut**, so a
  2014 prediction was built from a 2026 portfolio. State is now reconstructed
  per cut and the observation it came from is recorded.
- **The fan chart shifted its denominator origin**, reconstructing time-zero GDP
  and the debt ratio from a horizon-one central-growth row and then growing them
  again from there.

### Added

- **`pt-debt repricing all`.** The repricing artefacts were previously produced
  by scripts that were never committed, so a clean clone could rebuild the
  manuscript only from artefacts that happened to be in the tree. One command
  now runs estimation, bootstrap, kernels, fiscal translation, scenarios,
  cut-date backtests, and the manuscript inputs. Verified by deleting every
  artefact and regenerating; the estimation reproduces bit-identically.
- `tests/test_repricing_simulate.py`, which asserts the simulation and backtest
  equations rather than the existence of their output files. The suite was
  dense around parsing and empty here, which is why the defects above survived
  a large test count.
- A provisional-year robustness appendix, repricing uncertainty analysis, and a
  locked-dependency reproducibility path.

### Changed

Wording corrected wherever it outran the evidence: a ten-year benchmark is not
an issuance yield; a null placebo is no evidence of one contamination channel
rather than proof that identification is clean; the shape component is imposed
rather than identified; net-outflow months do enter the regression as zeros and
that zero is a bound, not an observation; the fan chart's band comes from chosen
distributions and is not a forecast interval; and reset timing is separated from
shock loading.

### Known limitations

The repricing panel is ordered by instrument class then period, so the HAC
estimator and the moving-block bootstrap run over a sequence in which calendar
time jumps backwards at the class boundary. The regression also carries no
class effects and weights each class-month equally. Both require changing the
estimand, and are not addressed in this release.

### Verification

- `pytest`: 344 tests passed.
- `ruff check .`: passed. `mypy src`: passed, 35 modules.
- Both manuscripts compile: burden paper 27 pages, repricing paper 14 pages,
  no undefined references.

## v0.3.2 - 2026-08-06

Second-round referee layout and membership fixes.

### Fixed

- Split the annual Portugal appendix into two portrait tables so all columns
  remain visible in the compiled PDF.
- Removed landscape wrappers from the annual and variable-definition
  appendices, keeping page numbers consistently positioned.
- Applied year-specific euro-area membership in the common-year helper and
  comparison plot path.

### Verification

- `pytest`: 318 tests passed.
- `ruff check .`: passed. `mypy src`: passed, 35 modules.
- The manuscript recompiles to a 26-page PDF with no rotated pages.

## v0.3.1 - 2026-08-05

Release-metadata and citation fixes. No analytical results change.

### Fixed

- **`.zenodo.json` was left at 0.2.0 by the v0.3.0 bump**, so the archived
  record would have been minted carrying the previous version number. The bump
  missed it because the search for version strings excluded JSON files — the
  one format that drives the archive.
- **Appendix F cited a version DOI that was three releases stale.** It named
  the v0.1.2 record as "the release DOI for the archived research object". A
  version DOI printed in a manuscript is stale as soon as the next release is
  cut, so the concept DOI is now the citation throughout: the manuscript, the
  README, and `CITATION.cff`, which previously carried no DOI at all despite
  being what GitHub and reference managers read.

### Added

- `tests/test_release_metadata.py`. Four files declare release identity and
  nothing compared them. The tests enumerate those files rather than grepping,
  so a new one has to be added deliberately instead of silently escaping the
  check, and they assert the versions and dates agree, the version is semver,
  the date is not in the future, the changelog has an entry for it, and
  `.zenodo.json` carries the fields Zenodo needs.
- A data-and-code availability statement in the repricing paper, which had
  none.

### Changed

- The repricing manuscript's drift guard no longer reads a DOI as a hand-typed
  result. `10.5281` matches a decimal; the verifier now strips `\doi`, `\url`,
  and `\texttt` before looking for literals.

### Verification

- `pytest`: 306 tests passed.
- `ruff check .`: passed. `mypy src`: passed, 35 modules.
- Both manuscripts recompile with no undefined references.

## v0.3.0 - 2026-08-05

Corrections to published numbers, and the second manuscript.

### Corrected results

- **Fixed a reversed claim in the euro-area rank fragility.** The paper said a
  lower Portuguese burden costs two ranks and a higher one costs none; the
  truth is the reverse. The cause was floating point, not the ranking
  convention: `1.9 - 0.3` evaluates to `1.5999999999999999` and lost a tie at
  1.6 that it should have joined. Perturbed values are now rounded to the
  precision Eurostat publishes before ranking. Table reads 6 / 6 / 4.
- **Fixed euro-area membership being evaluated at the year of writing.** The
  2014 cross-section ranked twenty countries against a euro area that had
  eighteen members, admitting Lithuania and Croatia six and nine years early,
  while the paper claimed in two places that membership is evaluated at the
  comparison year. Adoption years are now explicit. Portugal's 2014 rank, the
  median, and the gap are unchanged; the eligible count is not.
- Fixed a dead repository URL in the archiving appendix. It and both Zenodo
  DOIs are verified to resolve.

### Added

- The repricing-kernel manuscript, `paper/repricing/`. Finds that the
  weighted-average-maturity proxy understates one-year repricing by 10.90
  percentage points of the stock, driven by composition rather than behaviour.
  The behavioural estimation is a null and the backtest is negative; both are
  reported in the body.
- `pt-debt repricing paper`, which generates every number the repricing
  manuscript quotes and fails if a literal is typed into the body.
- The burden paper now carries the repricing study's corrections to its own
  assumptions, and discloses that the refinancing scenarios bracket the hazard
  rate but not its functional form.

### Reproducibility

- **Both manuscripts now build from a clean clone.** The burden paper
  referenced nine figures and the repository tracked none of them. Figure
  output is now byte-reproducible — matplotlib's creation timestamp and random
  SVG salt are suppressed — so the PDFs are tracked rather than ignored.
- The regression baseline covers 30 artefacts, up from 16, including every
  figure. Figures are globbed rather than listed, so a new one cannot sit
  outside the guard.
- Fixed the baseline being platform-dependent. With no `.gitattributes` and
  `core.autocrlf` enabled, checksums only matched on the machine that wrote
  them. Line endings are pinned and normalised before hashing.

### Review

- Applied the second-round referee report: functional-form disclosure, a
  glossary citation replaced with sources that perform the decomposition, a
  DOI for Campos et al., subtitle, abstract rank movement, figure placement,
  and a regime-dated reading of the long-run financing-cost effect.
- Author affiliation set to School of Media Arts and Design, Polytechnic of
  Porto.

### Verification

- `pytest`: 299 tests passed.
- `ruff check .`: passed. `mypy src`: passed, 35 modules.
- Both manuscripts compiled from a fresh clone with no pipeline run: burden
  paper 28 pages, repricing paper 5 pages, no undefined references.

## v0.2.0 - 2026-08-02

Recorded retrospectively; this release was tagged without a changelog entry.

- Added the repricing-kernel research package, `pt_debt.repricing`, as a second
  research output sharing one measurement layer. Instrument-level acquisition
  from IGCP and the ECB Data Portal, a subscription-margin panel, a frozen
  specification, the kernel and its bias decomposition, and pass-through
  simulation with an out-of-sample backtest.
- Revised the design after acquisition established that a dated redemption
  schedule and gross retail flows are not obtainable, and recorded the
  revision rather than fitting around it.
- Added `tests/test_burden_paper_regression.py`, the contract that lets the
  second paper import the measurement layer without altering the first
  paper's outputs.
- Applied the first-round blocking corrections to the burden manuscript.

## v0.1.2 - 2026-07-31

- Cut a follow-up Zenodo-backed patch release.

## v0.1.1 - 2026-07-31

- Added Zenodo metadata for GitHub release archiving.
- Added ORCID and contact metadata to the citation file.
- Updated the manuscript author block with affiliations, ORCID number, and corresponding-author email.

## v0.1.0 - 2026-07-28

- Built the Portugal public-debt interest burden pipeline with Eurostat and AMECO ingestion.
- Added annual metrics, reconciliation checks, scenario calculations, comparator-panel outputs, plots, and Markdown reporting.
- Added CSV and SQLite persistence with validation on write and read.
- Hardened source parsing, configuration validation, annual-key handling, scenario inputs, report inputs, and comparator-panel flags.
- Added local fixture-based tests, linting, type checking, and GitHub Actions CI configuration.
- Added government expenditure and revenue measures in euros and as percentages of GDP.
- Added generated LaTeX table fragments, headline macros, vector figure outputs, and citation metadata.

### Verification

- `pytest`: 147 tests passed.
- `ruff check .`: passed.
- `mypy src`: passed.
- Live configured pipeline completed with `python -m pt_debt_interest.cli all --config config/default.yaml`.
- LaTeX table generation and report compilation completed.

## Known external blocker

Still current as of v0.3.0, and it applies to every release above.

- GitHub Actions cannot start: the GitHub account billing/spending limit blocks
  runner execution. Every check reported in this changelog was run locally, not
  by CI.
