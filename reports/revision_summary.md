# Revision Summary

## Completed Work

- Added a methodological revision plan and committed it.
- Added general-government total expenditure in both nominal and GDP-ratio terms.
- Added general-government total revenue in both nominal and GDP-ratio terms.
- Replaced the ambiguous implicit-rate treatment with explicit rate definitions.
- Corrected debt-dynamics accounting to use interest divided by previous-year debt.
- Added exact interest-burden decomposition outputs, tests, figure generation, and documentation.
- Enforced completeness rules for any linked historical extension.
- Expanded the comparator panel to the euro-area country universe plus aggregate context.
- Rebuilt the refinancing scenario outputs to expose assumptions and reconciliation fields.
- Expanded source provenance and added source-coverage diagnostics.
- Removed the correlation table from the paper and replaced it with accounting-based interpretation.
- Flattened the main paper structure into standard article sections.
- Updated the paper's euro-area comparison table and added the exact decomposition figure.
- Added reproducibility metadata and strengthened CI with `pip check`.
- Replaced manually typed analytical paper tables with generated LaTeX fragments.
- Replaced recurring manually typed headline values with generated LaTeX macros.
- Added citation metadata for software reuse.
- Documented the supported dependency resolver and live regeneration workflow.
- Added a committed Poetry lockfile and switched CI to install from it.
- Added provisional-year robustness for the 2025 headline results.
- Clarified that euro-area average-debt-rate comparisons are descriptive rather
  than directly comparable funding-cost rankings.
- Archived the obsolete July blocking audit and refreshed the root final audit
  with the current verification run.

## Current Outputs

- Final PDF: `paper/portugal_public_debt_interest_report.pdf`.
- LaTeX source: `paper/portugal_public_debt_interest_report.tex`.
- Annual table: generated locally at `data/processed/portugal_debt_interest.csv`.
- SQLite database: generated locally at `data/processed/portugal_debt_interest.sqlite`.
- Comparator panel: generated locally at `data/processed/eurostat_panel_metrics.csv`.
- Validation report: generated locally at `reports/validation.json`.
- Source coverage: generated locally at `reports/source_coverage.csv`.
- Reproducibility metadata: generated locally at `reports/reproducibility.json`.
- Figures: `reports/figures/` as PNG, SVG, and PDF files.
- LaTeX table fragments: `reports/tables/`.
- Headline macro fragment: `reports/tables/paper_headlines.tex`.
- Citation metadata: `CITATION.cff`.
- Reproducibility guide: `docs/reproducibility.md`.

## Final State

The repository passes tests, linting, typing, table generation, and LaTeX
compilation in the current environment. The main empirical sample is now clearly
the harmonised Eurostat ESA 2010 period, 1995-2025, with no incomplete pre-1995
rows represented as observations. Substantive raw, interim, and processed data
files are regenerated locally and remain outside the committed source archive.
