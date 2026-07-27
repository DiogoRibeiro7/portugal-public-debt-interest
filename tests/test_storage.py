import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from pt_debt_interest.config import load_settings
from pt_debt_interest.exceptions import ValidationError
from pt_debt_interest.storage import load_processed, save_processed


def test_save_processed_rejects_duplicate_years_before_writing(tmp_path: Path) -> None:
    settings = load_settings("config/default.yaml")
    frame = pd.DataFrame({"year": [2024, 2024], "value": [1.0, 2.0]})

    with pytest.raises(ValidationError, match="duplicate years"):
        save_processed(frame, settings, tmp_path)

    assert not (tmp_path / settings.paths.processed / "portugal_debt_interest.csv").exists()
    assert not (
        tmp_path / settings.paths.processed / settings.storage.sqlite_filename
    ).exists()


def test_save_processed_requires_year_column(tmp_path: Path) -> None:
    settings = load_settings("config/default.yaml")
    frame = pd.DataFrame({"value": [1.0]})

    with pytest.raises(ValidationError, match="year column"):
        save_processed(frame, settings, tmp_path)


def test_save_processed_rejects_missing_years_before_writing(tmp_path: Path) -> None:
    settings = load_settings("config/default.yaml")
    frame = pd.DataFrame({"year": [2024, None], "value": [1.0, 2.0]})

    with pytest.raises(ValidationError, match="must not be missing"):
        save_processed(frame, settings, tmp_path)

    assert not (tmp_path / settings.paths.processed / "portugal_debt_interest.csv").exists()
    assert not (
        tmp_path / settings.paths.processed / settings.storage.sqlite_filename
    ).exists()


def test_save_processed_rejects_non_numeric_years_before_writing(
    tmp_path: Path,
) -> None:
    settings = load_settings("config/default.yaml")
    frame = pd.DataFrame({"year": [2024, "not-a-year"], "value": [1.0, 2.0]})

    with pytest.raises(ValidationError, match="year values must be numeric"):
        save_processed(frame, settings, tmp_path)

    assert not (tmp_path / settings.paths.processed / "portugal_debt_interest.csv").exists()
    assert not (
        tmp_path / settings.paths.processed / settings.storage.sqlite_filename
    ).exists()


def test_save_processed_rejects_fractional_years_before_writing(
    tmp_path: Path,
) -> None:
    settings = load_settings("config/default.yaml")
    frame = pd.DataFrame({"year": [2024, 2024.5], "value": [1.0, 2.0]})

    with pytest.raises(ValidationError, match="year values must be whole numbers"):
        save_processed(frame, settings, tmp_path)

    assert not (tmp_path / settings.paths.processed / "portugal_debt_interest.csv").exists()
    assert not (
        tmp_path / settings.paths.processed / settings.storage.sqlite_filename
    ).exists()


def test_load_processed_rejects_duplicate_csv_years(tmp_path: Path) -> None:
    settings = load_settings("config/default.yaml")
    processed_dir = tmp_path / settings.paths.processed
    processed_dir.mkdir(parents=True)
    pd.DataFrame({"year": [2024, 2024], "value": [1.0, 2.0]}).to_csv(
        processed_dir / "portugal_debt_interest.csv",
        index=False,
    )

    with pytest.raises(ValidationError, match="duplicate years"):
        load_processed(settings, tmp_path)


def test_load_processed_rejects_missing_sqlite_years(tmp_path: Path) -> None:
    settings = load_settings("config/default.yaml")
    processed_dir = tmp_path / settings.paths.processed
    processed_dir.mkdir(parents=True)
    sqlite_path = processed_dir / settings.storage.sqlite_filename
    with sqlite3.connect(sqlite_path) as connection:
        pd.DataFrame({"year": [2024, None], "value": [1.0, 2.0]}).to_sql(
            settings.storage.table_name,
            connection,
            if_exists="replace",
            index=False,
        )

    with pytest.raises(ValidationError, match="must not be missing"):
        load_processed(settings, tmp_path)
