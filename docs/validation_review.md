# Validation review

## Confirmed finding

- Severity: high
- File and symbol: `src/pt_debt_interest.cli.all_command`
- Reproduction procedure: run the full pipeline after a previous successful AMECO fetch, then make the optional AMECO fetch fail while leaving `data/interim/ameco_linked.csv` in place.
- Risk: the build step could consume stale linked AMECO data after the optional source failed, making the processed dataset appear to include a fresh extension.
- Minimal correction: remove stale AMECO interim data when the optional fetch fails, and ignore AMECO interim data when AMECO is disabled.
- Regression test: `tests/test_pipeline.py::test_clear_ameco_interim_removes_stale_file`.

## Review notes

- `pytest`, `ruff check .`, and `mypy src` are expected to pass after the correction.
- Live source access was not required for this stale-data failure path.
