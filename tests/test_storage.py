from pathlib import Path

import pandas as pd
import pytest

from pt_debt_interest.config import load_settings
from pt_debt_interest.exceptions import ValidationError
from pt_debt_interest.storage import save_processed


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
