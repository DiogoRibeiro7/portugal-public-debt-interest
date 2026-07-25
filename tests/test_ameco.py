import zipfile
from pathlib import Path

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
