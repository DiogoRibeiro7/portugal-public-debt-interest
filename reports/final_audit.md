# Final Audit

## Verification Run

Date: 2026-07-28

Commands completed successfully:

- `pytest`: 145 passed, 5 warnings.
- `ruff check .`: passed.
- `mypy src`: passed.
- `pt-debt all --config config/default.yaml`: completed.
- `latexmk -pdf -interaction=nonstopmode -halt-on-error portugal_public_debt_interest_report.tex`: completed.

## Data Checks

- Annual analytical table: 31 rows, 1995-2025.
- Annual analytical columns: 114.
- Total government expenditure fields: present in euro millions, euros, official percent of GDP, calculated percent of GDP, and preferred percent of GDP.
- Total government revenue fields: present in euro millions, euros, official percent of GDP, calculated percent of GDP, and preferred percent of GDP.
- Generic implicit-rate output column: absent.
- Euro-area comparator panel: 682 rows, 22 geographies.
- Non-aggregate 2025 comparator countries: 20.
- Portugal 2025 interest-burden rank: 6.
- Validation result: passed.

## Methodological Corrections Verified

- Interest-rate concepts are separated into debt-dynamics and average-debt definitions.
- General-government total expenditure is included as both a nominal value and percent of GDP.
- General-government total revenue is included as both a nominal value and percent of GDP.
- Debt-dynamics contributions reconstruct observed debt-ratio changes within tolerance.
- Interest-burden changes are decomposed exactly into rate, average-debt-ratio, and interaction effects.
- Empty pre-1995 linked rows are excluded from the main analytical table.
- Comparator design uses the euro-area country universe, with aggregates excluded from country ranks.
- Refinancing scenarios now expose full-pass-through, cumulative repricing, remaining unrepriced share, and pass-through gap columns.
- Source provenance includes source database, source table or series, vintage, retrieval timestamp, and checksum fields where available.
- Reproducibility metadata records package version, Python version, platform, git revision, config hash, and project settings.
- The main paper no longer uses the previous level-correlation table as evidence.

## Remaining Warnings

- The validation report retains a warning for debt-ratio reconciliation in 1997 and 1998. This is a warning, not a failed check.
- The LaTeX build reports minor overfull/underfull box warnings. The PDF builds successfully.
- The current AMECO archive did not yield complete pre-1995 analytical rows under the configured selectors; the generated main table therefore begins in 1995.

## Exclusion Check

The protected folder was not staged or committed during this audit cycle.
