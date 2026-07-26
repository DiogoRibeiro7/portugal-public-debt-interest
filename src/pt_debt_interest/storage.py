"""CSV and SQLite persistence."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from .config import Settings
from .exceptions import ValidationError


def _validate_annual_keys(frame: pd.DataFrame) -> None:
    if "year" not in frame.columns:
        raise ValidationError("processed dataset must include a year column")
    duplicate_years = (
        frame.loc[frame["year"].duplicated(keep=False), "year"].dropna().astype(int).tolist()
    )
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


def load_processed(settings: Settings, root: Path = Path(".")) -> pd.DataFrame:
    """Load the processed analytical dataset, preferring CSV."""
    processed_dir = root / settings.paths.processed
    csv_path = processed_dir / "portugal_debt_interest.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    sqlite_path = processed_dir / settings.storage.sqlite_filename
    if sqlite_path.exists():
        with sqlite3.connect(sqlite_path) as connection:
            return pd.read_sql_query(
                f'SELECT * FROM "{settings.storage.table_name}" ORDER BY year', connection
            )
    raise FileNotFoundError("processed dataset not found; run the build stage")
