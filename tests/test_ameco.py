import zipfile
from pathlib import Path

import pandas as pd
import pytest

from pt_debt_interest.config import AmecoSelector, HttpSection
from pt_debt_interest.exceptions import SourceError
from pt_debt_interest.sources.ameco import AmecoArchiveClient


def test_ameco_archive_extract(tmp_path: Path) -> None:
    archive_path = tmp_path / "ameco.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.write("tests/fixtures/ameco/UYIG.csv", arcname="UYIG.csv")

    client = AmecoArchiveClient("https://example.invalid", HttpSection(), tmp_path)
    selectors = {
        "interest": AmecoSelector(
            variable_code="UYIG", unit_code=319, output_name="interest_pct_gdp_ameco"
        ),
        "debt": AmecoSelector(
            variable_code="UDGG", unit_code=319, output_name="debt_pct_gdp_ameco"
        ),
    }
    frame = client.extract(archive_path, "PRT", selectors, 1960, 2026, 2025)
    assert frame.loc[frame["year"] == 1994, "interest_pct_gdp_ameco"].iloc[0] == 5.1
    assert frame.loc[frame["year"] == 2026, "observation_status_ameco"].iloc[0] == "forecast"


def test_ameco_archive_extract_rejects_duplicate_outputs(tmp_path: Path) -> None:
    archive_path = tmp_path / "ameco.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.write("tests/fixtures/ameco/UYIG.csv", arcname="UYIG.csv")

    client = AmecoArchiveClient("https://example.invalid", HttpSection(), tmp_path)
    selectors = {
        "interest": AmecoSelector(
            variable_code="UYIG", unit_code=319, output_name="interest_pct_gdp_ameco"
        ),
        "duplicate": AmecoSelector(
            variable_code="UYIG", unit_code=99, output_name="interest_pct_gdp_ameco"
        ),
    }

    with pytest.raises(SourceError, match="duplicate AMECO output"):
        client.extract(archive_path, "PRT", selectors, 1960, 2026, 2025)


def test_ameco_archive_extract_rejects_missing_selector(tmp_path: Path) -> None:
    archive_path = tmp_path / "ameco.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.write("tests/fixtures/ameco/UYIG.csv", arcname="UYIG.csv")

    client = AmecoArchiveClient("https://example.invalid", HttpSection(), tmp_path)
    selectors = {
        "missing": AmecoSelector(
            variable_code="NOTFOUND", unit_code=319, output_name="missing_ameco"
        ),
    }

    with pytest.raises(SourceError, match="none of the configured"):
        client.extract(archive_path, "PRT", selectors, 1960, 2026, 2025)


def test_ameco_archive_extract_rejects_empty_requested_range(tmp_path: Path) -> None:
    archive_path = tmp_path / "ameco.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.write("tests/fixtures/ameco/UYIG.csv", arcname="UYIG.csv")

    client = AmecoArchiveClient("https://example.invalid", HttpSection(), tmp_path)
    selectors = {
        "interest": AmecoSelector(
            variable_code="UYIG",
            unit_code=319,
            output_name="interest_pct_gdp_ameco",
        )
    }

    with pytest.raises(SourceError, match="no observations"):
        client.extract(archive_path, "PRT", selectors, 1900, 1901, 2025)


def test_ameco_archive_extract_rejects_duplicate_selector_rows(tmp_path: Path) -> None:
    source = pd.read_csv("tests/fixtures/ameco/UYIG.csv")
    duplicated = pd.concat([source, source.iloc[[0]]], ignore_index=True)
    duplicate_csv = tmp_path / "duplicate_rows.csv"
    duplicated.to_csv(duplicate_csv, index=False)
    archive_path = tmp_path / "ameco.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.write(duplicate_csv, arcname="duplicate_rows.csv")

    client = AmecoArchiveClient("https://example.invalid", HttpSection(), tmp_path)
    selectors = {
        "interest": AmecoSelector(
            variable_code="UYIG",
            unit_code=319,
            output_name="interest_pct_gdp_ameco",
        )
    }

    with pytest.raises(SourceError, match="matched 2 rows"):
        client.extract(archive_path, "PRT", selectors, 1960, 2026, 2025)


def test_ameco_archive_extract_rejects_duplicate_selector_members(tmp_path: Path) -> None:
    archive_path = tmp_path / "ameco.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.write("tests/fixtures/ameco/UYIG.csv", arcname="UYIG_a.csv")
        archive.write("tests/fixtures/ameco/UYIG.csv", arcname="UYIG_b.csv")

    client = AmecoArchiveClient("https://example.invalid", HttpSection(), tmp_path)
    selectors = {
        "interest": AmecoSelector(
            variable_code="UYIG",
            unit_code=319,
            output_name="interest_pct_gdp_ameco",
        )
    }

    with pytest.raises(SourceError, match="matched multiple archive members"):
        client.extract(archive_path, "PRT", selectors, 1960, 2026, 2025)
