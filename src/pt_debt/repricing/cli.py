"""``pt-debt repricing`` command group.

Registered onto the existing CLI rather than forking it: one entry point, one
dependency set, two papers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
import yaml

from pt_debt_interest.exceptions import SourceError

from .acquire import ecb, igcp

app = typer.Typer(help="Repricing-kernel research commands.")

DEFAULT_CONFIG = Path("config/repricing.yaml")


def load_config(path: Path) -> dict[str, Any]:
    """Read the repricing configuration."""
    if not path.is_file():
        raise typer.BadParameter(f"repricing configuration not found: {path}")
    with path.open(encoding="utf-8") as handle:
        loaded: dict[str, Any] = yaml.safe_load(handle) or {}
    return loaded


@app.command("acquire")
def acquire_command(
    config: Path = DEFAULT_CONFIG,
    refresh: bool = typer.Option(
        False, help="Re-fetch from source instead of reusing the newest cached payload."
    ),
) -> None:
    """Acquire instrument-level and covariate inputs for the repricing work."""
    settings = load_config(config)
    raw_dir = Path(settings["paths"]["raw"])
    http = settings.get("http", {})
    timeout = float(http.get("timeout_seconds", 90))

    failures: list[str] = []

    try:
        stock = igcp.fetch_debt_stock(
            settings["igcp"]["debt_stock_monthly_url"],
            raw_dir,
            refresh=refresh,
            timeout_seconds=timeout,
        )
        typer.echo(
            f"igcp debt stock: {stock.fetch.path} "
            f"({stock.frame['series'].nunique()} series, {len(stock.frame)} rows)"
        )
    except SourceError as exc:
        failures.append(f"igcp debt stock: {exc}")

    try:
        indicators = igcp.fetch_debt_indicators(
            settings["igcp"]["debt_indicators_url"],
            raw_dir,
            refresh=refresh,
            timeout_seconds=timeout,
        )
        typer.echo(
            f"igcp debt indicators: {indicators.fetch.path} "
            f"({indicators.frame['series'].nunique()} series, "
            f"{len(indicators.frame)} rows)"
        )
    except SourceError as exc:
        failures.append(f"igcp debt indicators: {exc}")

    try:
        fetched = ecb.fetch_configured(
            settings["ecb"]["series"],
            raw_dir,
            refresh=refresh,
            timeout_seconds=timeout,
        )
        for name, series in fetched.items():
            typer.echo(f"ecb {name}: {len(series.frame)} observations")
    except SourceError as exc:
        failures.append(str(exc))

    if failures:
        typer.echo("")
        typer.echo("Acquisition incomplete. See docs/manual_ingest.md.")
        for failure in failures:
            typer.echo(f"  - {failure}")
        raise typer.Exit(code=1)
