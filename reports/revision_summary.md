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

## Current Outputs

- Final PDF: `paper/portugal_public_debt_interest_report.pdf`.
- LaTeX source: `paper/portugal_public_debt_interest_report.tex`.
- Annual table: `data/processed/portugal_debt_interest.csv`.
- SQLite database: `data/processed/portugal_debt_interest.sqlite`.
- Comparator panel: `data/processed/eurostat_panel_metrics.csv`.
- Validation report: `reports/validation.json`.
- Source coverage: `reports/source_coverage.csv`.
- Reproducibility metadata: `reports/reproducibility.json`.
- Figures: `reports/figures/` as PNG, SVG, and PDF files.
- LaTeX table fragments: `reports/tables/`.
- Headline macro fragment: `reports/tables/paper_headlines.tex`.
- Citation metadata: `CITATION.cff`.
- Reproducibility guide: `docs/reproducibility.md`.

## Final State

The repository passes tests, linting, typing, full pipeline generation, and LaTeX compilation. The main empirical sample is now clearly the harmonised Eurostat ESA 2010 period, 1995-2025, with no incomplete pre-1995 rows represented as observations.
