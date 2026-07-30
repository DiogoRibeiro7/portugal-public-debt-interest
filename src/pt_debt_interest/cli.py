"""Command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import typer

from .config import Settings, load_settings
from .eligibility import build_eligibility_table
from .latex_tables import generate_latex_tables
from .pipeline import (
    build_dataset,
    build_eurostat_panel,
    clear_ameco_interim,
    fetch_ameco,
    fetch_eurostat,
    fetch_eurostat_panel,
)
from .plotting import generate_all_plots
from .refinancing import (
    build_refinancing_assumptions,
    build_refinancing_results,
    load_refinancing_scenarios,
)
from .reporting import generate_report
from .sources.ameco import AmecoArchiveClient
from .storage import (
    load_processed,
    save_euro_area_eligibility,
    save_refinancing_outputs,
)
from .validation import validate_dataset

app = typer.Typer(no_args_is_help=True, help="Portugal public-debt interest analysis")
DEFAULT_CONFIG = Path("config/default.yaml")


def _settings(config: Path) -> Settings:
    settings = load_settings(config)
    settings.ensure_directories()
    return settings


def _load_optional_panel_metrics(settings: Settings) -> pd.DataFrame | None:
    panel_path = settings.paths.processed / "eurostat_panel_metrics.csv"
    if not panel_path.exists():
        return None
    return pd.read_csv(panel_path)


def _existing_figure_paths(settings: Settings) -> list[Path]:
    if not settings.paths.figures.exists():
        return []
    return sorted(
        path
        for path in settings.paths.figures.iterdir()
        if path.suffix.lower() in {".png", ".svg", ".pdf"}
    )


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


@app.command("build-panel")
def build_panel_command(config: Path = DEFAULT_CONFIG) -> None:
    """Build processed comparator-panel metrics and missingness diagnostics."""
    outputs = build_eurostat_panel(_settings(config))
    for path in outputs.values():
        typer.echo(path)


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
    _, results, main_scenario = _refinancing()
    paths = generate_all_plots(
        frame,
        settings.paths.figures,
        panel_frame=_load_optional_panel_metrics(settings),
        shocks_bps=settings.analysis.static_rate_shocks_bps,
        refinancing_shares=settings.analysis.default_refinancing_shares,
        refinancing_results=results,
        refinancing_main_scenario=main_scenario,
    )
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
        panel_frame=_load_optional_panel_metrics(settings),
        figure_paths=_existing_figure_paths(settings),
    )
    typer.echo(destination)



REFINANCING_CONFIG = Path("config/refinancing_scenarios.yaml")


def _refinancing(config_path: Path = REFINANCING_CONFIG) -> tuple[Any, Any, str]:
    """Load the scenarios and run the stylised cohort simulation."""
    import yaml

    scenarios = load_refinancing_scenarios(config_path)
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    shocks = tuple(int(value) for value in raw.get("shocks_bps", [0, 50, 100, 200]))
    main_scenario = str(raw.get("main_scenario", "central"))
    return (
        build_refinancing_assumptions(scenarios, shocks),
        build_refinancing_results(scenarios, shocks),
        main_scenario,
    )


@app.command("tables")
def tables_command(config: Path = DEFAULT_CONFIG) -> None:
    """Generate LaTeX tables from processed analytical data."""
    settings = _settings(config)
    frame = load_processed(settings)
    assumptions, results, main_scenario = _refinancing()
    save_refinancing_outputs(assumptions, results, settings)
    panel = _load_optional_panel_metrics(settings)
    if panel is not None and not panel.empty:
        latest = int(pd.to_numeric(panel["year"], errors="coerce").max())
        save_euro_area_eligibility(
            build_eligibility_table(
                panel,
                latest,
                accepted_statuses=tuple(settings.analysis.accepted_observation_statuses),
            ),
            settings,
        )
    paths = generate_latex_tables(
        frame,
        settings.paths.reports / "tables",
        settings.project.main_start_year,
        settings.analysis.static_rate_shocks_bps,
        panel_frame=_load_optional_panel_metrics(settings),
        refinancing_assumptions=assumptions,
        refinancing_main_scenario=main_scenario,
    )
    for path in paths:
        typer.echo(path)


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
    figure_paths = generate_all_plots(
        frame,
        settings.paths.figures,
        panel_frame=_load_optional_panel_metrics(settings),
        shocks_bps=settings.analysis.static_rate_shocks_bps,
        refinancing_shares=settings.analysis.default_refinancing_shares,
    )
    generate_report(
        frame,
        settings.paths.reports / "summary.md",
        settings.project.main_start_year,
        settings.analysis.static_rate_shocks_bps,
        panel_frame=_load_optional_panel_metrics(settings),
        figure_paths=figure_paths,
    )
    generate_latex_tables(
        frame,
        settings.paths.reports / "tables",
        settings.project.main_start_year,
        settings.analysis.static_rate_shocks_bps,
        panel_frame=_load_optional_panel_metrics(settings),
    )
    if not result["passed"]:
        raise typer.Exit(code=1)
    typer.echo("pipeline completed")


if __name__ == "__main__":
    app()
