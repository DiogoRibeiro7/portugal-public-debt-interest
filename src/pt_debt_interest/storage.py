"""CSV and SQLite persistence."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from .config import Settings
from .exceptions import ValidationError


def _validate_annual_keys(frame: pd.DataFrame) -> None:
    if "year" not in frame.columns:
        raise ValidationError("processed dataset must include a year column")
    if frame["year"].isna().any():
        raise ValidationError("processed dataset year values must not be missing")
    try:
        numeric_years = pd.to_numeric(frame["year"], errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValidationError("processed dataset year values must be numeric") from exc
    if ((~np.isfinite(numeric_years)) | numeric_years.mod(1).ne(0)).any():
        raise ValidationError("processed dataset year values must be whole numbers")
    years = numeric_years.astype(int)
    duplicate_years = years.loc[years.duplicated(keep=False)].tolist()
    if duplicate_years:
        raise ValidationError(f"processed dataset contains duplicate years: {duplicate_years}")


def save_processed(
    frame: pd.DataFrame,
    settings: Settings,
    root: Path = Path("."),
) -> dict[str, Path]:
    """Save the analytical table using the configured backend."""
    _validate_annual_keys(frame)
    processed_dir = root / settings.paths.processed
    processed_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}

    if settings.storage.backend in {"csv", "both"}:
        csv_path = processed_dir / "portugal_debt_interest.csv"
        frame.to_csv(csv_path, index=False)
        outputs["csv"] = csv_path

    if settings.storage.backend in {"sqlite", "both"}:
        sqlite_path = processed_dir / settings.storage.sqlite_filename
        with sqlite3.connect(sqlite_path) as connection:
            frame.to_sql(
                settings.storage.table_name,
                connection,
                if_exists="replace",
                index=False,
            )
            table_name = settings.storage.table_name
            connection.execute(
                f'CREATE UNIQUE INDEX IF NOT EXISTS idx_year ON "{table_name}" (year)'
            )
        outputs["sqlite"] = sqlite_path

    return outputs


def save_interest_decomposition(
    frame: pd.DataFrame,
    settings: Settings,
    root: Path = Path("."),
) -> dict[str, Path]:
    """Save the exact interest-burden decomposition beside processed data."""
    processed_dir = root / settings.paths.processed
    processed_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}

    if settings.storage.backend in {"csv", "both"}:
        csv_path = processed_dir / "interest_burden_decomposition.csv"
        frame.to_csv(csv_path, index=False)
        outputs["csv"] = csv_path

    if settings.storage.backend in {"sqlite", "both"}:
        sqlite_path = processed_dir / settings.storage.sqlite_filename
        with sqlite3.connect(sqlite_path) as connection:
            frame.to_sql(
                "interest_burden_decomposition",
                connection,
                if_exists="replace",
                index=False,
            )
            connection.execute(
                'CREATE UNIQUE INDEX IF NOT EXISTS idx_interest_burden_interval '
                'ON "interest_burden_decomposition" (start_year, end_year)'
            )
        outputs["sqlite"] = sqlite_path

    return outputs


def save_interest_counterfactuals(
    frame: pd.DataFrame,
    settings: Settings,
    root: Path = Path("."),
) -> dict[str, Path]:
    """Save interest-burden counterfactuals beside processed data."""
    processed_dir = root / settings.paths.processed
    processed_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}

    if settings.storage.backend in {"csv", "both"}:
        csv_path = processed_dir / "interest_burden_counterfactuals.csv"
        frame.to_csv(csv_path, index=False)
        outputs["csv"] = csv_path

    if settings.storage.backend in {"sqlite", "both"}:
        sqlite_path = processed_dir / settings.storage.sqlite_filename
        with sqlite3.connect(sqlite_path) as connection:
            frame.to_sql(
                "interest_burden_counterfactuals",
                connection,
                if_exists="replace",
                index=False,
            )
            connection.execute(
                'CREATE UNIQUE INDEX IF NOT EXISTS idx_interest_counterfactual '
                'ON "interest_burden_counterfactuals" (year, counterfactual)'
            )
        outputs["sqlite"] = sqlite_path

    return outputs


def save_refinancing_outputs(
    assumptions: pd.DataFrame,
    results: pd.DataFrame,
    settings: Settings,
    root: Path = Path("."),
) -> dict[str, Path]:
    """Save the stylised refinancing assumptions and simulation results.

    The assumptions travel with the results deliberately: a pass-through number
    is meaningless without the repricing profile that produced it.
    """
    processed_dir = root / settings.paths.processed
    processed_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}

    if settings.storage.backend in {"csv", "both"}:
        assumptions_path = processed_dir / "refinancing_assumptions.csv"
        results_path = processed_dir / "refinancing_results.csv"
        assumptions.to_csv(assumptions_path, index=False)
        results.to_csv(results_path, index=False)
        outputs["assumptions_csv"] = assumptions_path
        outputs["results_csv"] = results_path

    if settings.storage.backend in {"sqlite", "both"}:
        sqlite_path = processed_dir / settings.storage.sqlite_filename
        with sqlite3.connect(sqlite_path) as connection:
            assumptions.to_sql(
                "refinancing_assumptions",
                connection,
                if_exists="replace",
                index=False,
            )
            results.to_sql(
                "refinancing_results",
                connection,
                if_exists="replace",
                index=False,
            )
            connection.execute(
                'CREATE UNIQUE INDEX IF NOT EXISTS idx_refinancing_results '
                'ON "refinancing_results" (scenario, shock_bps, horizon_year)'
            )
        outputs["sqlite"] = sqlite_path

    return outputs


def save_euro_area_eligibility(
    frame: pd.DataFrame,
    settings: Settings,
    root: Path = Path("."),
) -> dict[str, Path]:
    """Save the euro-area eligibility and exclusion record."""
    processed_dir = root / settings.paths.processed
    processed_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}

    if settings.storage.backend in {"csv", "both"}:
        csv_path = processed_dir / "euro_area_eligibility.csv"
        frame.to_csv(csv_path, index=False)
        outputs["csv"] = csv_path

    if settings.storage.backend in {"sqlite", "both"}:
        sqlite_path = processed_dir / settings.storage.sqlite_filename
        with sqlite3.connect(sqlite_path) as connection:
            frame.to_sql(
                "euro_area_eligibility",
                connection,
                if_exists="replace",
                index=False,
            )
        outputs["sqlite"] = sqlite_path

    return outputs


def load_processed(settings: Settings, root: Path = Path(".")) -> pd.DataFrame:
    """Load the processed analytical dataset, preferring CSV."""
    processed_dir = root / settings.paths.processed
    csv_path = processed_dir / "portugal_debt_interest.csv"
    if csv_path.exists():
        frame = pd.read_csv(csv_path)
        _validate_annual_keys(frame)
        return frame
    sqlite_path = processed_dir / settings.storage.sqlite_filename
    if sqlite_path.exists():
        with sqlite3.connect(sqlite_path) as connection:
            frame = pd.read_sql_query(
                f'SELECT * FROM "{settings.storage.table_name}" ORDER BY year', connection
            )
        _validate_annual_keys(frame)
        return frame
    raise FileNotFoundError("processed dataset not found; run the build stage")
