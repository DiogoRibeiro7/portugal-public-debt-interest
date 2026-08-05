# Changelog

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
