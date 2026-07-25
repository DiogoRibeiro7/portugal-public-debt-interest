"""Command-line interface."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from .config import Settings, load_settings
from .pipeline import (
    build_dataset,
    clear_ameco_interim,
    fetch_ameco,
    fetch_eurostat,
    fetch_eurostat_panel,
)
from .plotting import generate_all_plots
from .reporting import generate_report
from .sources.ameco import AmecoArchiveClient
from .storage import load_processed
from .validation import validate_dataset

app = typer.Typer(no_args_is_help=True, help="Portugal public-debt interest analysis")
DEFAULT_CONFIG = Path("config/default.yaml")


def _settings(config: Path) -> Settings:
    settings = load_settings(config)
    settings.ensure_directories()
    return settings


@app.command("fetch-eurostat")
def fetch_eurostat_command(config: Path = DEFAULT_CONFIG) -> None:
    """Download and join the harmonised Eurostat series."""
    destination = fetch_eurostat(_settings(config))
    typer.echo(destination)


@app.command("fetch-ameco")
def fetch_ameco_command(config: Path = DEFAULT_CONFIG) -> None:
    """Download and extract the optional AMECO linked extension."""
    destination = fetch_ameco(_settings(config))
    typer.echo(destination or "AMECO disabled")


@app.command("fetch-panel")
def fetch_panel_command(config: Path = DEFAULT_CONFIG) -> None:
    """Download the configured Eurostat comparator panel."""
    destination = fetch_eurostat_panel(_settings(config))
    typer.echo(destination)


@app.command("discover-ameco")
def discover_ameco_command(
    archive: Path,
    patterns: list[str],
    config: Path = DEFAULT_CONFIG,
) -> None:
    """Search an AMECO archive for rows matching all text patterns."""
    settings = _settings(config)
    client = AmecoArchiveClient(settings.ameco.archive_url, settings.http, settings.paths.raw)
    matches = client.discover(archive, patterns)
    typer.echo(matches.to_csv(index=False))


@app.command("build")
def build_command(config: Path = DEFAULT_CONFIG) -> None:
    """Build and persist the annual analytical dataset."""
    frame = build_dataset(_settings(config))
    typer.echo(f"built {len(frame)} annual rows")


@app.command("validate")
def validate_command(config: Path = DEFAULT_CONFIG) -> None:
    """Run reconciliations and accounting-identity checks."""
    settings = _settings(config)
    frame = load_processed(settings)
    result = validate_dataset(
        frame,
        settings.project.main_start_year,
        settings.project.end_year,
        settings.analysis.ratio_tolerance_pp,
        settings.analysis.identity_tolerance_pp,
    )
    destination = settings.paths.reports / "validation.json"
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    typer.echo(destination)
    if not result["passed"]:
        raise typer.Exit(code=1)


@app.command("plot")
def plot_command(config: Path = DEFAULT_CONFIG) -> None:
    """Generate all available charts."""
    settings = _settings(config)
    frame = load_processed(settings)
    paths = generate_all_plots(frame, settings.paths.figures)
    for path in paths:
        typer.echo(path)


@app.command("report")
def report_command(config: Path = DEFAULT_CONFIG) -> None:
    """Generate the Markdown analytical summary."""
    settings = _settings(config)
    frame = load_processed(settings)
    destination = generate_report(
        frame,
        settings.paths.reports / "summary.md",
        settings.project.main_start_year,
        settings.analysis.static_rate_shocks_bps,
    )
    typer.echo(destination)


@app.command("all")
def all_command(config: Path = DEFAULT_CONFIG, include_ameco: bool = True) -> None:
    """Run acquisition, build, validation, charts, and report."""
    settings = _settings(config)
    fetch_eurostat(settings)
    if include_ameco and settings.ameco.enabled:
        try:
            fetch_ameco(settings)
        except Exception as exc:
            stale_path = clear_ameco_interim(settings)
            if stale_path is not None:
                typer.echo(f"Removed stale AMECO interim data: {stale_path}", err=True)
            typer.echo(f"AMECO extension skipped: {exc}", err=True)
    frame = build_dataset(settings)
    result = validate_dataset(
        frame,
        settings.project.main_start_year,
        settings.project.end_year,
        settings.analysis.ratio_tolerance_pp,
        settings.analysis.identity_tolerance_pp,
    )
    (settings.paths.reports / "validation.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    generate_all_plots(frame, settings.paths.figures)
    generate_report(
        frame,
        settings.paths.reports / "summary.md",
        settings.project.main_start_year,
        settings.analysis.static_rate_shocks_bps,
    )
    if not result["passed"]:
        raise typer.Exit(code=1)
    typer.echo("pipeline completed")


if __name__ == "__main__":
    app()
