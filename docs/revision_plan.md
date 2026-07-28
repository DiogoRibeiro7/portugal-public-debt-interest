# Revision plan

## Baseline audit

Audit date: 2026-07-28.

Repository state audited:

- Branch: `main`
- Commit: `8b7a943`
- Python: `3.13.5`
- Dependency manager declared: Poetry, with PEP 621 metadata also present in `pyproject.toml`
- Lock status: no tracked `poetry.lock` was found during the audit
- Install command required before tests: `python -m pip install -e ".[dev]"`
- Data retrieval mode reproduced: live Eurostat and AMECO downloads through `pt-debt all --config config/default.yaml`
- Network required for live reproduction: yes
- Cached raw data available locally: yes, under `data/raw/`, but raw/interim/processed artifacts are ignored by version control
- Current generated analytical table: 66 rows, 83 columns, 1960-2025
- Current comparator panel: 248 rows, 8 configured geographies, 1995-2025
- Current report build: `latexmk -pdf -interaction=nonstopmode -halt-on-error portugal_public_debt_interest_report.tex`

Baseline commands and results:

| Command | Result |
|---|---|
| `pytest` before editable install | Failed during collection: `ModuleNotFoundError: No module named 'pt_debt_interest'` |
| `python -m pip install -e ".[dev]"` | Passed |
| `pytest` after editable install | Passed: 133 tests, 4 warnings |
| `ruff check .` | Passed |
| `mypy src` | Passed |
| `pt-debt all --config config/default.yaml` | Passed: pipeline completed |
| `latexmk -pdf ...` in `paper/` | Passed: 20-page PDF |

Validation baseline:

- `reports/validation.json` passed all error-severity checks.
- Warning retained: `debt_ratio_reconciliation` fails for 1997 and 1998.
- Current PDF hash after rebuild: `0EADDB2920536BD31DA2DC8709EFC3F36685274CA3F66910D1DE952DD09F03D8`.

Important reproduction caveat: the revision request required reproduction from a clean environment. The available session was the existing working environment, so the audit recorded the install step needed to make tests import the package. A future final audit should use a fresh virtual environment or container.

## Repository map

| Responsibility | Current files |
|---|---|
| Project configuration | `config/default.yaml`, `src/pt_debt_interest/config.py` |
| CLI orchestration | `src/pt_debt_interest/cli.py` |
| Eurostat retrieval | `src/pt_debt_interest/sources/eurostat.py`, `src/pt_debt_interest/jsonstat.py`, `src/pt_debt_interest/pipeline.py` |
| AMECO retrieval | `src/pt_debt_interest/sources/ameco.py`, `src/pt_debt_interest/pipeline.py` |
| Source provenance joining | `src/pt_debt_interest/pipeline.py` |
| Annual table construction | `src/pt_debt_interest/pipeline.py`, `src/pt_debt_interest/metrics.py` |
| Fiscal-variable construction | `src/pt_debt_interest/metrics.py` |
| Interest-rate calculations | `src/pt_debt_interest/metrics.py`, `src/pt_debt_interest/panel.py`, `src/pt_debt_interest/scenarios.py` |
| Debt-dynamics calculations | `src/pt_debt_interest/metrics.py`, `src/pt_debt_interest/plotting.py` |
| Cross-country comparisons | `src/pt_debt_interest/panel.py`, `src/pt_debt_interest/pipeline.py`, `src/pt_debt_interest/plotting.py`, `src/pt_debt_interest/reporting.py` |
| Refinancing simulations | `src/pt_debt_interest/scenarios.py`, `src/pt_debt_interest/plotting.py` |
| Figures | `src/pt_debt_interest/plotting.py`, generated under `reports/figures/` |
| Markdown summary | `src/pt_debt_interest/reporting.py`, generated as `reports/summary.md` |
| LaTeX report | `paper/portugal_public_debt_interest_report.tex`, `paper/portugal_public_debt_interest_report.pdf` |
| Persistence | `src/pt_debt_interest/storage.py` |
| Validation | `src/pt_debt_interest/validation.py` |
| Tests | `tests/` |
| CI | `.github/workflows/ci.yml` |
| Documentation | `README.md`, `docs/*.md`, `CHANGELOG.md`, `IMPLEMENTATION_STATUS.md` |

## Dependency graph

```text
Eurostat gov_10a_main
  -> data/raw/eurostat_interest_*.json
  -> data/interim/eurostat_main.csv
  -> interest_mio_eur, interest_pct_gdp_official, overall_balance_pct_gdp

Eurostat gov_10dd_edpt1
  -> data/raw/eurostat_debt_*.json
  -> data/interim/eurostat_main.csv
  -> debt_mio_eur, debt_pct_gdp_official

Eurostat nama_10_gdp
  -> data/raw/eurostat_nominal_gdp_*.json, data/raw/eurostat_real_gdp_growth_*.json
  -> data/interim/eurostat_main.csv
  -> nominal_gdp_mio_eur, real_gdp_growth_pct

Eurostat irt_lt_mcby_a
  -> data/raw/eurostat_ten_year_yield_*.json
  -> data/interim/eurostat_main.csv
  -> ten_year_yield_pct

AMECO all-CSV archive
  -> data/raw/ameco_csv_*.zip
  -> data/interim/ameco_linked.csv
  -> linked pre-1995 interest, debt, balance, AMECO implicit rate

data/interim/eurostat_main.csv + data/interim/ameco_linked.csv
  -> src/pt_debt_interest/pipeline.py
  -> src/pt_debt_interest/metrics.py
  -> data/processed/portugal_debt_interest.csv
  -> data/processed/portugal_debt_interest.sqlite

Configured comparator geographies
  -> data/interim/eurostat_panel.csv
  -> src/pt_debt_interest/panel.py
  -> data/processed/eurostat_panel_metrics.csv
  -> reports/eurostat_panel_missingness.csv

data/processed/portugal_debt_interest.csv
  -> src/pt_debt_interest/validation.py
  -> reports/validation.json
  -> src/pt_debt_interest/plotting.py
  -> reports/figures/01-07, 09
  -> src/pt_debt_interest/reporting.py
  -> reports/summary.md
  -> paper/portugal_public_debt_interest_report.tex
  -> paper/portugal_public_debt_interest_report.pdf

data/processed/eurostat_panel_metrics.csv
  -> reports/figures/08_european_comparison.*
  -> reports/summary.md
  -> European comparison section in LaTeX report
```

## Methodological defects

1. **Ambiguous implicit-rate column.** The earlier implementation calculated both previous-debt and average-debt rates but also wrote the selected configured value into a generic rate column. With the default average-debt denominator, debt-dynamics outputs used the average-debt rate even though the discrete identity requires interest divided by previous-period debt.

Current formulas:

```text
implicit_interest_rate_previous_debt_pct = I_t / D_{t-1} * 100
implicit_interest_rate_average_debt_pct = I_t / ((D_{t-1} + D_t) / 2) * 100
generic_effective_rate = selected configured rate
interest_growth_differential = generic_effective_rate - nominal_gdp_growth
former_stabilising_primary_balance =
  ((generic_effective_rate - g_t) / (1 + g_t)) * d_{t-1}
former_stock_flow_adjustment =
  observed_debt_change - automatic_debt_dynamics + primary_balance_pct_gdp
```

Replacement formulas:

```text
effective_interest_rate_debt_dynamics_decimal = I_t / D_{t-1}
implicit_interest_rate_average_debt_decimal = I_t / ((D_{t-1} + D_t) / 2)
interest_growth_contribution =
  ((effective_interest_rate_debt_dynamics_decimal - nominal_gdp_growth_decimal)
   / (1 + nominal_gdp_growth_decimal)) * d_{t-1}
primary_balance_contribution = -primary_balance_decimal
stock_flow_adjustment =
  observed_debt_ratio_change
  - interest_growth_contribution
  - primary_balance_contribution
reconstructed_debt_ratio_change =
  interest_growth_contribution + primary_balance_contribution + stock_flow_adjustment
```

2. **Debt-dynamics outputs are incomplete.** The project does not expose observed debt-ratio change, primary-balance contribution with correct decomposition sign, reconstructed change, or reconciliation error.

3. **No exact interest-burden decomposition.** The report narrates debt exposure and rate effects but does not decompose changes in `b_t = I_t / Y_t` into exact average-rate and average-debt-exposure contributions.

4. **1960-1994 extension is under-analysed.** The paper and data include a 1960-2025 table, but the report mainly analyses 1995-2025. The linked AMECO accounting basis is documented but not visually separated in a dedicated historical chart.

5. **Comparator selection is arbitrary.** `config/default.yaml` lists Portugal, Spain, Italy, Greece, Ireland, EA20, Germany, and the Netherlands. Rankings are therefore rankings within a hand-selected panel, not the euro-area distribution.

6. **Refinancing assumptions are insufficiently documented.** Default shares are in configuration but no maturity-source evidence or sensitivity table accompanies them.

7. **Correlation analysis is weak evidence.** The report contains a correlation table among persistent fiscal levels, mechanically related variables, and common-denominator ratios. This is not robust evidence for a short annual sample.

8. **Source-vintage and observation-status reporting is incomplete.** Row-level provenance exists, but headline report text and tables do not consistently mark provisional source flags or data vintages.

9. **Replication metadata is incomplete.** No tracked lock file, no generated replication metadata, no report commit hash, no dirty-tree status, and no PDF/source checksum appendix.

10. **Publication quality issues remain.** Figure generation now includes vector PDF output, mixed-axis charts have been replaced by stacked-panel figures, LaTeX layout warnings have been cleared, analytical tables are generated from processed data, and recurring paper headline values are generated as LaTeX macros.

## File-by-file implementation plan

### Stage 2: separate interest-rate definitions

- `src/pt_debt_interest/metrics.py`
  - Add decimal internal columns:
    - `effective_interest_rate_debt_dynamics_decimal`
    - `implicit_interest_rate_average_debt_decimal`
  - Add display-boundary percentage columns:
    - `effective_interest_rate_debt_dynamics_pct`
    - `implicit_interest_rate_average_debt_pct`
  - Remove the generic implicit-rate output from new outputs.
  - Preserve first-year missing values where lagged debt is unavailable.
- `docs/interest_rate_definitions.md`
  - Document use cases and prohibited uses.
- `docs/data_dictionary.md`
  - Replace old generic rate definition.
- `tests/test_metrics.py`, `tests/test_outputs.py`, `tests/test_panel.py`
  - Update expected columns and add synthetic hand checks.

### Stage 3: correct debt dynamics

- Add `src/pt_debt_interest/debt_dynamics.py`.
- Move debt-dynamics formulas out of `metrics.py`.
- Emit:
  - `observed_debt_ratio_change_pp`
  - `interest_growth_contribution_pp`
  - `primary_balance_contribution_pp`
  - `stock_flow_adjustment_pp`
  - `reconstructed_debt_ratio_change_pp`
  - `debt_dynamics_reconciliation_error_pp`
  - `debt_stabilising_primary_balance_before_sfa_pct_gdp`
- Add `docs/debt_dynamics_methodology.md`.
- Update validation to fail on reconciliation error above implementation tolerance.
- Update figure 7 and tests.

### Stage 4: exact interest-burden decomposition

- Add `src/pt_debt_interest/interest_decomposition.py`.
- Generate:
  - adjacent annual decompositions;
  - configured endpoint decompositions;
  - selected 2014/2025 counterfactuals.
- Add processed CSV and SQLite table:
  - `data/processed/interest_burden_decomposition.csv`
  - SQLite table `interest_burden_decomposition`
- Add figures:
  - decomposition contributions by interval;
  - observed/counterfactual burden comparison.
- Add report-context output with generated headline numbers.

### Stage 5: historical-extension scope decision

- Audit AMECO extension completeness and comparability.
- Create `docs/historical_extension_decision.md`.
- Choose:
  - Design A if extension is defensible as contextual history with clear accounting break; or
  - Design B if not defensible.
- Add validation for source-priority and forecast exclusion.
- Add historical-extension chart only if Design A is chosen.

### Stage 6: full eligible euro-area panel

- Replace `project.comparison_geographies` default with an explicit eligible euro-area list or a discoverable geo list with exclusions.
- Add country eligibility output:
  - `reports/euro_area_country_eligibility.csv`
- Add rank denominator, median, percentile, and group views.
- Update `src/pt_debt_interest/panel.py`, `pipeline.py`, plotting, reporting, tests.

### Stage 7: refinancing assumptions

- Add explicit scenario table output and sensitivity assumptions.
- Make zero-shock and full-pass-through reconciliation tests.
- Show incremental burden relative to baseline, not only scenario total.

### Stage 8: provenance and validation

- Add `source_database`, `source_table_or_series`, `is_harmonised_main_sample`, `is_historical_extension`, `basis_break_flag`.
- Add observation-status and provisional-flag reporting.
- Add validation checks for unit consistency, rate usage, decomposition reconciliation, and panel eligibility.

### Stage 9: correlation redesign

- Remove level-correlation table from the main report.
- Create `docs/correlation_analysis_decision.md`.
- Optional appendix diagnostics must use first differences, pairwise counts, and explicit warnings.

### Stage 10: report restructure

- Add a generated report-context JSON/YAML and load values into LaTeX generation.
- Add related-literature section with real bibliographic metadata.
- Avoid structural-model language.
- Ensure all headline numbers come from generated outputs.

### Stage 11: publication quality

- Export PDF vector figures for LaTeX and PNG previews.
- Replace mixed-axis charts with stacked-panel figures.
- Generate analytical LaTeX tables from data.
- Fix tied minima and maxima.
- Add `docs/publication_quality_checklist.md`.
- Compile without missing references, bibliography warnings, or overfull boxes.

### Stage 12: reproducibility metadata

Status note: citation metadata, README citation guidance, and resolver
documentation are now present. The remaining reproducibility item is any CI
expansion that requires cached analytical fixtures or LaTeX availability.

- Completed: clearly document the supported resolver in `docs/reproducibility.md`.
- Completed: add replication metadata generation:
  - project version;
  - Git commit;
  - dirty-tree status;
  - Python version;
  - OS;
  - lock/config/data/report checksums;
  - report build timestamp;
  - PDF checksum.
- Completed: add `CITATION.cff`.
- Completed: add changelog entry.
- Completed: update README.
- Extend CI to build cached analytical outputs and compile LaTeX where available.

### Stage 13: final audit

- Create:
  - `reports/final_audit.md`
  - `reports/revision_summary.md`
- Run all tests, validation, pipeline, figure/table generation, and LaTeX compilation.
- Do not mark ready if core methodological invariants fail.

## Test plan

Add or update tests covering:

1. Previous-debt and average-debt rate formulas on synthetic data.
2. Missing first-year lagged debt.
3. Rate denominator concepts differ when debt changes materially.
4. Decimal and percentage values cannot be silently mixed.
5. Debt dynamics reconstruct observed debt-ratio changes within tolerance.
6. Positive primary surplus reduces debt through `primary_balance_contribution = -pb_t`.
7. Near-minus-100-percent nominal growth is rejected.
8. Stock-flow adjustment is residual and can be large without failing validation.
9. Exact interest-burden decomposition adds exactly to reconstructed burden change.
10. Counterfactual burdens use unrounded level-derived values.
11. Historical extension cannot overlap Eurostat silently.
12. Forecast rows are excluded from observed summaries.
13. Full euro-area panel excludes aggregates from ranks and reports denominator.
14. Refinancing zero shock produces zero incremental burden.
15. Full pass-through reconciles with static sensitivity.
16. Removed correlation table is not referenced in generated text.
17. Generated LaTeX tables do not rely on manually typed headline numbers.
18. Report-context numbers are consistent across abstract, body, tables, and conclusion.

## Data migration plan

Existing processed files must be regenerated. The old processed CSV and SQLite schema contain a generic rate column and debt-dynamics columns based on the configured denominator. The revision should:

- remove or deprecate the generic rate column;
- add explicit decimal and percentage display columns for both rate concepts;
- add debt-dynamics contribution and reconciliation columns;
- add interest-burden decomposition outputs;
- add source-scope fields for harmonised sample versus historical extension;
- add panel eligibility outputs;
- add report-context and replication-metadata outputs.

Migration should be implemented as a full regeneration from raw/interim inputs, not an in-place edit of generated datasets.

## Expected breaking changes

- Column removal or deprecation: the generic implicit-rate column.
- New rate columns:
  - `effective_interest_rate_debt_dynamics_decimal`
  - `effective_interest_rate_debt_dynamics_pct`
  - `implicit_interest_rate_average_debt_decimal`
  - `implicit_interest_rate_average_debt_pct`
- Debt-dynamics column changes:
  - old stabilising-primary-balance and stock-flow-adjustment columns replaced or renamed with explicit contribution/reconciliation columns.
- Comparator panel expands from configured hand-picked geographies to eligible euro-area countries.
- SQLite schema gains additional tables and columns.
- Figure filenames may change or expand.
- LaTeX report should be generated from context/table files rather than manual tables.
- CI may gain LaTeX/report-generation jobs.

## Acceptance criteria for the full revision

- The debt-dynamics identity uses `I_t / D_{t-1}` and reconciles exactly within floating-point tolerance.
- The average-debt implicit rate is used only for average-cost descriptive analysis and interest-burden factorisation.
- The report contains an exact interest-burden decomposition with quantified contributions.
- The 1960-1994 scope is either clearly contextual with visible accounting break or removed from the principal scope.
- The European comparison uses all eligible euro-area countries or documents exclusions.
- Correlation among persistent fiscal levels is removed from the main evidentiary chain.
- All report headline numbers are generated from analytical outputs.
- The final PDF identifies code/data version and replication metadata.
- `pytest`, `ruff`, `mypy`, validation, pipeline, figure/table generation, and LaTeX compilation pass in a documented clean environment.
