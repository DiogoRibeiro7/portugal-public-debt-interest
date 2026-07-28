# Reproducibility

## Dependency resolution

This project does not currently track a lock file. The supported resolver is the
PEP 621 dependency set declared in `pyproject.toml`, installed with:

```bash
python -m pip install -e ".[dev]"
```

Poetry may also be used as a frontend:

```bash
poetry install --with dev
```

When Poetry is used, `poetry.lock` is a local resolver artifact unless it is
created and intentionally committed in a future release. Until then, the
auditable dependency contract is the bounded version ranges in `pyproject.toml`,
the Python version matrix in `.github/workflows/ci.yml`, and the recorded
runtime metadata in `reports/reproducibility.json`.

## Analytical regeneration

The full live-data workflow is:

```bash
pt-debt all --config config/default.yaml
pt-debt fetch-panel --config config/default.yaml
pt-debt build-panel --config config/default.yaml
pt-debt plot --config config/default.yaml
pt-debt report --config config/default.yaml
pt-debt tables --config config/default.yaml
```

The live workflow requires network access to Eurostat and AMECO. Raw downloads
are timestamped and accompanied by checksums so processed outputs can be traced
back to source payloads.

## Report build

The publication PDF is compiled from `paper/portugal_public_debt_interest_report.tex`.
The paper imports generated figure PDFs and table fragments under `reports/`.

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error portugal_public_debt_interest_report.tex
```
