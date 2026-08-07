# Reproducibility

## Dependency resolution

This project tracks `poetry.lock`. The supported locked install is:

```bash
poetry install --with dev
```

If Poetry is not already installed, install the same major version used to write
the lock file and then install from the lock:

```bash
python -m pip install "poetry>=2.2,<3.0"
poetry install --with dev
```

For quick local work, `python -m pip install -e ".[dev]"` remains usable, but it
resolves within the bounded ranges in `pyproject.toml` and is not the locked
publication environment. The auditable dependency contract is the combination
of `pyproject.toml`, `poetry.lock`, the Python version matrix in
`.github/workflows/ci.yml`, and the recorded runtime metadata in
`reports/reproducibility.json`.

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
