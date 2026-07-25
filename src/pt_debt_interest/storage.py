"""CSV and SQLite persistence."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from .config import Settings


def save_processed(frame: pd.DataFrame, settings: Settings, root: Path = Path(".")) -> dict[str, Path]:
    """Save the analytical table using the configured backend."""
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
            connection.execute(
                f'CREATE UNIQUE INDEX IF NOT EXISTS idx_year ON "{settings.storage.table_name}" (year)'
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
