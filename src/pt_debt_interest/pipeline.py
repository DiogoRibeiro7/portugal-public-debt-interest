"""End-to-end data assembly pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import Settings
from .metrics import calculate_metrics
from .panel import geography_metadata, series_specs_for_geo, validate_country_year_panel
from .sources.ameco import AmecoArchiveClient
from .sources.eurostat import EurostatClient
from .storage import save_processed

CANONICAL_PROVENANCE_COLUMNS = [
    "source",
    "source_vintage",
    "accounting_basis",
    "observation_status",
    "retrieval_timestamp_utc",
    "source_flags",
    "basis_break",
]


def _join_row_values(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    """Join unique non-null row values from selected columns."""
    values: list[str] = []
    for _, row in frame.loc[:, columns].iterrows():
        unique = sorted(
            {
                str(value)
                for value in row.tolist()
                if pd.notna(value) and str(value) != ""
            }
        )
        values.append(";".join(unique))
    return pd.Series(values, index=frame.index, dtype="string")


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
    frame["source_vintage"] = pd.NA
    frame["accounting_basis"] = "ESA2010"
    frame["observation_status"] = "observed"
    frame["retrieval_timestamp_utc"] = pd.NA
    status_columns = [column for column in frame.columns if column.endswith("_status")]
    if status_columns:
        frame["source_flags"] = _join_row_values(frame.astype("string"), status_columns)
    else:
        frame["source_flags"] = pd.NA
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


def fetch_eurostat_panel(settings: Settings, root: Path = Path(".")) -> Path:
    """Fetch configured Eurostat series for all comparator geographies."""
    raw_dir = root / settings.paths.raw
    interim_dir = root / settings.paths.interim
    interim_dir.mkdir(parents=True, exist_ok=True)
    client = EurostatClient(settings.eurostat.base_url, settings.http, raw_dir)
    pieces: list[pd.DataFrame] = []
    for geo in settings.project.comparison_geographies:
        frame = client.fetch_all(
            series_specs_for_geo(settings.eurostat.series, geo),
            settings.project.main_start_year,
            settings.project.end_year,
        )
        metadata = geography_metadata(geo)
        for column, value in metadata.items():
            frame[column] = pd.Series([value] * len(frame), index=frame.index)
        frame["source"] = "Eurostat"
        frame["accounting_basis"] = "ESA2010"
        frame["observation_status"] = "observed"
        pieces.append(frame)
    panel = pd.concat(pieces, ignore_index=True, sort=False)
    validate_country_year_panel(panel)
    destination = interim_dir / "eurostat_panel.csv"
    panel.to_csv(destination, index=False)
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
    extension["source_vintage"] = pd.NA
    extension["accounting_basis"] = extension.get(
        "accounting_basis_ameco", "linked_ESA2010_ESA95_ESA79"
    )
    extension["observation_status"] = extension.get("observation_status_ameco", "observed")
    extension["retrieval_timestamp_utc"] = pd.NA
    code_columns = [column for column in extension.columns if column.endswith("_series_code")]
    if code_columns:
        extension["source_flags"] = _join_row_values(extension.astype("string"), code_columns)
    else:
        extension["source_flags"] = pd.NA
    return extension


def _canonicalise_annual_table(frame: pd.DataFrame, main_start_year: int) -> pd.DataFrame:
    """Apply canonical annual-table ordering and provenance defaults."""
    canonical = frame.copy()
    for column in CANONICAL_PROVENANCE_COLUMNS:
        if column not in canonical.columns:
            canonical[column] = pd.NA
    canonical["basis_break"] = canonical["year"].astype(int).eq(main_start_year)
    canonical = canonical.sort_values(["year", "source"]).reset_index(drop=True)
    return canonical


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

    combined = _canonicalise_annual_table(
        pd.concat(frames, ignore_index=True, sort=False),
        settings.project.main_start_year,
    )
    boundaries = [boundary.model_dump() for boundary in settings.analysis.regime_boundaries]
    analytical = calculate_metrics(
        combined,
        denominator=settings.analysis.implicit_rate_denominator,
        regime_boundaries=boundaries,
    )
    save_processed(analytical, settings, root)
    return analytical
