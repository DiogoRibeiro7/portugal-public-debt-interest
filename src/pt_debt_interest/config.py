"""Typed configuration loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class ProjectSection(BaseModel):
    """Project-level temporal and geographic settings."""

    country_name: str
    eurostat_geo: str
    ameco_geo: str
    main_start_year: int = 1995
    extended_start_year: int = 1960
    end_year: int
    comparison_geographies: list[str] = Field(default_factory=list)

    @field_validator("end_year")
    @classmethod
    def validate_end_year(cls, value: int) -> int:
        if value < 1995:
            raise ValueError("end_year must be at least 1995")
        return value


class PathsSection(BaseModel):
    """Project filesystem paths."""

    raw: Path
    interim: Path
    processed: Path
    figures: Path
    reports: Path


class StorageSection(BaseModel):
    """Processed-data storage settings."""

    backend: Literal["csv", "sqlite", "both"] = "csv"
    sqlite_filename: str = "portugal_debt_interest.sqlite"
    table_name: str = "annual_debt_interest"


class HttpSection(BaseModel):
    """HTTP client settings."""

    timeout_seconds: float = 60.0
    max_retries: int = 3
    backoff_seconds: float = 1.0


class EurostatSeriesSpec(BaseModel):
    """One Eurostat dataset query."""

    dataset: str
    filters: dict[str, str]
    value_name: str


class EurostatSection(BaseModel):
    """Eurostat source settings."""

    base_url: str
    series: dict[str, EurostatSeriesSpec]


class AmecoSelector(BaseModel):
    """Selector for one AMECO series embedded in the archive."""

    variable_code: str
    unit_code: int
    output_name: str


class AmecoSection(BaseModel):
    """AMECO linked-series settings."""

    enabled: bool = True
    archive_url: str
    forecast_cutoff_year: int
    selectors: dict[str, AmecoSelector]


class RegimeBoundary(BaseModel):
    """Economic-regime annotation."""

    start: int
    end: int
    label: str


class AnalysisSection(BaseModel):
    """Calculation and validation settings."""

    ratio_tolerance_pp: float = 0.15
    identity_tolerance_pp: float = 0.05
    implicit_rate_denominator: Literal["previous_debt", "average_debt"] = "average_debt"
    static_rate_shocks_bps: list[int] = Field(default_factory=lambda: [50, 100, 200])
    default_refinancing_shares: list[float] = Field(default_factory=list)
    observed_only_by_default: bool = True
    regime_boundaries: list[RegimeBoundary] = Field(default_factory=list)

    @field_validator("default_refinancing_shares")
    @classmethod
    def validate_refinancing_shares(cls, values: list[float]) -> list[float]:
        if any(value < 0 or value > 1 for value in values):
            raise ValueError("refinancing shares must lie between zero and one")
        if sum(values) > 1.0:
            raise ValueError("refinancing shares must not exceed the outstanding stock")
        return values

    @field_validator("regime_boundaries")
    @classmethod
    def validate_regime_boundaries(
        cls,
        values: list[RegimeBoundary],
    ) -> list[RegimeBoundary]:
        ordered = sorted(values, key=lambda boundary: (boundary.start, boundary.end))
        previous_end: int | None = None
        for boundary in ordered:
            if boundary.start > boundary.end:
                raise ValueError("regime boundary start must be before or equal to end")
            if previous_end is not None and boundary.start <= previous_end:
                raise ValueError("regime boundaries must not overlap")
            previous_end = boundary.end
        return values


class Settings(BaseModel):
    """Complete project configuration."""

    project: ProjectSection
    paths: PathsSection
    storage: StorageSection
    http: HttpSection
    eurostat: EurostatSection
    ameco: AmecoSection
    analysis: AnalysisSection

    def ensure_directories(self, root: Path = Path(".")) -> None:
        """Create configured directories relative to the repository root."""
        for path in (
            self.paths.raw,
            self.paths.interim,
            self.paths.processed,
            self.paths.figures,
            self.paths.reports,
        ):
            (root / path).mkdir(parents=True, exist_ok=True)


def load_settings(path: str | Path) -> Settings:
    """Load and validate a YAML configuration file."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise TypeError("configuration root must be a mapping")
    return Settings.model_validate(payload)
