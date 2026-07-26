"""End-to-end data assembly pipeline."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from .config import EurostatSeriesSpec, Settings
from .exceptions import SourceError
from .metrics import calculate_metrics
from .panel import (
    PANEL_MISSINGNESS_COLUMNS,
    build_panel_metrics,
    geography_metadata,
    panel_missingness,
    series_specs_for_geo,
    validate_country_year_panel,
)
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


def _provenance_columns(frame: pd.DataFrame, suffix: str) -> list[str]:
    return [column for column in frame.columns if column.endswith(suffix)]


def _raw_timestamp_from_name(path: Path) -> str:
    parts = path.stem.split("_")
    if len(parts) < 3:
        return path.stem
    return parts[-1]


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _add_eurostat_row_provenance(frame: pd.DataFrame) -> pd.DataFrame:
    """Add row-level provenance from per-series raw metadata columns."""
    output = frame.copy()
    timestamp_columns = _provenance_columns(output, "_retrieval_timestamp_utc")
    checksum_columns = _provenance_columns(output, "_source_sha256")
    raw_file_columns = _provenance_columns(output, "_raw_file")
    output["retrieval_timestamp_utc"] = (
        _join_row_values(output.astype("string"), timestamp_columns)
        if timestamp_columns
        else pd.NA
    )
    output["source_vintage"] = (
        _join_row_values(output.astype("string"), raw_file_columns)
        if raw_file_columns
        else pd.NA
    )
    if checksum_columns:
        output["source_checksum_sha256"] = _join_row_values(
            output.astype("string"),
            checksum_columns,
        )
    return output


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
    frame = _add_eurostat_row_provenance(frame)
    frame["source"] = "Eurostat"
    frame["accounting_basis"] = "ESA2010"
    frame["observation_status"] = "observed"
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
    frame["retrieval_timestamp_utc"] = _raw_timestamp_from_name(archive)
    frame["source_vintage"] = archive.name
    frame["source_checksum_sha256"] = _file_sha256(archive)
    destination = interim_dir / "ameco_linked.csv"
    frame.to_csv(destination, index=False)
    return destination


def ameco_interim_path(settings: Settings, root: Path = Path(".")) -> Path:
    """Return the configured AMECO interim output path."""
    return root / settings.paths.interim / "ameco_linked.csv"


def clear_ameco_interim(settings: Settings, root: Path = Path(".")) -> Path | None:
    """Remove stale optional AMECO interim data if it exists."""
    path = ameco_interim_path(settings, root)
    if path.exists():
        path.unlink()
        return path
    return None


def fetch_eurostat_panel(settings: Settings, root: Path = Path(".")) -> Path:
    """Fetch configured Eurostat series for all comparator geographies."""
    raw_dir = root / settings.paths.raw
    interim_dir = root / settings.paths.interim
    interim_dir.mkdir(parents=True, exist_ok=True)
    client = EurostatClient(settings.eurostat.base_url, settings.http, raw_dir)
    pieces: list[pd.DataFrame] = []
    for geo in settings.project.comparison_geographies:
        frame = _fetch_available_panel_series(
            client,
            series_specs_for_geo(settings.eurostat.series, geo),
            settings.project.main_start_year,
            settings.project.end_year,
        )
        metadata = geography_metadata(geo)
        for column, value in metadata.items():
            if isinstance(value, bool):
                frame[column] = pd.Series([value] * len(frame), index=frame.index, dtype="boolean")
            else:
                frame[column] = pd.Series([value] * len(frame), index=frame.index, dtype="string")
        frame = _add_eurostat_row_provenance(frame)
        frame["source"] = "Eurostat"
        frame["accounting_basis"] = "ESA2010"
        frame["observation_status"] = "observed"
        pieces.append(frame)
    panel = _concat_preserving_columns(pieces)
    validate_country_year_panel(panel)
    destination = interim_dir / "eurostat_panel.csv"
    panel.to_csv(destination, index=False)
    return destination


def build_eurostat_panel(settings: Settings, root: Path = Path(".")) -> dict[str, Path]:
    """Build processed comparator-panel metrics and missingness diagnostics."""
    interim_path = root / settings.paths.interim / "eurostat_panel.csv"
    if not interim_path.exists():
        raise FileNotFoundError("Eurostat panel table not found; run fetch-panel")
    processed_dir = root / settings.paths.processed
    reports_dir = root / settings.paths.reports
    processed_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    raw_panel = pd.read_csv(interim_path)
    boundaries = [boundary.model_dump() for boundary in settings.analysis.regime_boundaries]
    metrics = build_panel_metrics(
        raw_panel,
        denominator=settings.analysis.implicit_rate_denominator,
        regime_boundaries=boundaries,
    )
    validate_country_year_panel(metrics)
    metrics_path = processed_dir / "eurostat_panel_metrics.csv"
    missingness_path = reports_dir / "eurostat_panel_missingness.csv"
    metrics.to_csv(metrics_path, index=False)
    panel_missingness(metrics, PANEL_MISSINGNESS_COLUMNS).to_csv(
        missingness_path,
        index=False,
    )
    return {"metrics": metrics_path, "missingness": missingness_path}


def _concat_preserving_columns(pieces: list[pd.DataFrame]) -> pd.DataFrame:
    """Concatenate frames without all-null-column dtype warnings."""
    expected_columns = list(dict.fromkeys(column for piece in pieces for column in piece.columns))
    prepared: list[pd.DataFrame] = []
    for piece in pieces:
        all_null_columns = [
            column for column in piece.columns if bool(piece[column].isna().all())
        ]
        prepared.append(piece.drop(columns=all_null_columns))
    combined = pd.concat(prepared, ignore_index=True, sort=False)
    for column in expected_columns:
        if column not in combined.columns:
            combined[column] = pd.NA
    return combined.loc[:, expected_columns]


def _fetch_available_panel_series(
    client: EurostatClient,
    series: dict[str, EurostatSeriesSpec],
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """Fetch comparator series, preserving missing optional series as null columns."""
    merged: pd.DataFrame | None = None
    missing: list[tuple[str, str]] = []
    for name, spec in series.items():
        try:
            current = client.fetch_series(name, spec, start_year, end_year)
        except SourceError as exc:
            missing.append((name, str(exc)))
            continue
        merged = current if merged is None else merged.merge(current, on="year", how="outer")
    if merged is None:
        detail = "; ".join(f"{name}: {error}" for name, error in missing)
        raise SourceError(f"no comparator series could be fetched: {detail}")
    for name, error in missing:
        value_name = str(series[name].value_name)
        merged[value_name] = pd.Series(pd.NA, index=merged.index, dtype="Float64")
        merged[f"{value_name}_status"] = pd.Series(pd.NA, index=merged.index, dtype="string")
        merged[f"{value_name}_missing_reason"] = pd.Series(
            [error] * len(merged),
            index=merged.index,
            dtype="string",
        )
    return merged.sort_values("year").reset_index(drop=True)


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
    extension["source_vintage"] = extension.get("source_vintage", pd.NA)
    extension["accounting_basis"] = extension.get(
        "accounting_basis_ameco", "linked_ESA2010_ESA95_ESA79"
    )
    extension["observation_status"] = extension.get("observation_status_ameco", "observed")
    extension["retrieval_timestamp_utc"] = extension.get("retrieval_timestamp_utc", pd.NA)
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
    ameco_path = ameco_interim_path(settings, root)
    if settings.ameco.enabled and ameco_path.exists():
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
