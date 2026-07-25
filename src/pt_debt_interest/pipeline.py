"""End-to-end data assembly pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import Settings
from .metrics import calculate_metrics
from .sources.ameco import AmecoArchiveClient
from .sources.eurostat import EurostatClient
from .storage import save_processed


def fetch_eurostat(settings: Settings, root: Path = Path(".")) -> Path:
    """Fetch all configured Eurostat series and save the joined source table."""
    raw_dir = root / settings.paths.raw
    interim_dir = root / settings.paths.interim
    interim_dir.mkdir(parents=True, exist_ok=True)
    client = EurostatClient(settings.eurostat.base_url, settings.http, raw_dir)
    frame = client.fetch_all(
        settings.eurostat.series,
        settings.project.main_start_year,
        settings.project.end_year,
    )
    frame["source"] = "Eurostat"
    frame["accounting_basis"] = "ESA2010"
    frame["observation_status"] = "observed"
    destination = interim_dir / "eurostat_main.csv"
    frame.to_csv(destination, index=False)
    return destination


def fetch_ameco(settings: Settings, root: Path = Path(".")) -> Path | None:
    """Fetch and extract the optional linked AMECO extension."""
    if not settings.ameco.enabled:
        return None
    raw_dir = root / settings.paths.raw
    interim_dir = root / settings.paths.interim
    interim_dir.mkdir(parents=True, exist_ok=True)
    client = AmecoArchiveClient(settings.ameco.archive_url, settings.http, raw_dir)
    archive = client.download()
    frame = client.extract(
        archive,
        settings.project.ameco_geo,
        settings.ameco.selectors,
        settings.project.extended_start_year,
        settings.project.end_year + 2,
        settings.ameco.forecast_cutoff_year,
    )
    destination = interim_dir / "ameco_linked.csv"
    frame.to_csv(destination, index=False)
    return destination


def _build_ameco_pre1995(ameco: pd.DataFrame, main_start_year: int) -> pd.DataFrame:
    """Map AMECO columns to the analytical schema for pre-main-series years only."""
    extension = ameco.loc[ameco["year"] < main_start_year].copy()
    if extension.empty:
        return extension
    if "interest_bn_eur_ameco" in extension.columns:
        extension["interest_mio_eur"] = extension["interest_bn_eur_ameco"] * 1_000.0
    extension["interest_pct_gdp_official"] = extension.get("interest_pct_gdp_ameco")
    extension["debt_pct_gdp_official"] = extension.get("debt_pct_gdp_ameco")
    extension["overall_balance_pct_gdp"] = extension.get("overall_balance_pct_gdp_ameco")
    if {"interest_mio_eur", "interest_pct_gdp_official"}.issubset(extension.columns):
        extension["nominal_gdp_mio_eur"] = (
            extension["interest_mio_eur"] / extension["interest_pct_gdp_official"] * 100.0
        )
    if {"nominal_gdp_mio_eur", "debt_pct_gdp_official"}.issubset(extension.columns):
        extension["debt_mio_eur"] = (
            extension["nominal_gdp_mio_eur"] * extension["debt_pct_gdp_official"] / 100.0
        )
    extension["source"] = "AMECO"
    extension["accounting_basis"] = extension.get(
        "accounting_basis_ameco", "linked_ESA2010_ESA95_ESA79"
    )
    extension["observation_status"] = extension.get("observation_status_ameco", "observed")
    return extension


def build_dataset(settings: Settings, root: Path = Path(".")) -> pd.DataFrame:
    """Build the final annual table from available interim source files."""
    interim_dir = root / settings.paths.interim
    eurostat_path = interim_dir / "eurostat_main.csv"
    if not eurostat_path.exists():
        raise FileNotFoundError("Eurostat interim table not found; run fetch-eurostat")
    eurostat = pd.read_csv(eurostat_path)

    frames = [eurostat]
    ameco_path = interim_dir / "ameco_linked.csv"
    if ameco_path.exists():
        extension = _build_ameco_pre1995(
            pd.read_csv(ameco_path), settings.project.main_start_year
        )
        if not extension.empty:
            frames.insert(0, extension)

    combined = pd.concat(frames, ignore_index=True, sort=False)
    boundaries = [boundary.model_dump() for boundary in settings.analysis.regime_boundaries]
    analytical = calculate_metrics(
        combined,
        denominator=settings.analysis.implicit_rate_denominator,
        regime_boundaries=boundaries,
    )
    save_processed(analytical, settings, root)
    return analytical
