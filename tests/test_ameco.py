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


def test_ameco_archive_extract_rejects_selector_with_only_missing_values(
    tmp_path: Path,
) -> None:
    source = pd.read_csv("tests/fixtures/ameco/UYIG.csv")
    source.loc[source["CODE"].eq("PRT.1.0.319.0.UYIG"), ["1960", "1961", "1962"]] = ""
    missing_csv = tmp_path / "missing_values.csv"
    source.to_csv(missing_csv, index=False)
    archive_path = tmp_path / "ameco.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.write(missing_csv, arcname="missing_values.csv")

    client = AmecoArchiveClient("https://example.invalid", HttpSection(), tmp_path)
    selectors = {
        "interest": AmecoSelector(
            variable_code="UYIG",
            unit_code=319,
            output_name="interest_pct_gdp_ameco",
        )
    }

    with pytest.raises(SourceError, match="only missing values"):
        client.extract(archive_path, "PRT", selectors, 1960, 1962, 2025)


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


def test_ameco_archive_extract_rejects_non_finite_unit_code(tmp_path: Path) -> None:
    source = pd.read_csv("tests/fixtures/ameco/UYIG.csv")
    source.loc[
        source["CODE"].eq("PRT.1.0.319.0.UYIG"),
        "CODE",
    ] = "PRT.1.0.inf.0.UYIG"
    malformed_csv = tmp_path / "non_finite_unit.csv"
    source.to_csv(malformed_csv, index=False)
    archive_path = tmp_path / "ameco.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.write(malformed_csv, arcname="fractional_unit.csv")

    client = AmecoArchiveClient("https://example.invalid", HttpSection(), tmp_path)
    selectors = {
        "interest": AmecoSelector(
            variable_code="UYIG",
            unit_code=319,
            output_name="interest_pct_gdp_ameco",
        )
    }

    with pytest.raises(SourceError, match="none of the configured"):
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


def test_ameco_code_parser_rejects_non_finite_unit_code() -> None:
    assert AmecoArchiveClient._parse_code("PRT.1.0.inf.0.UYIG") is None


def test_ameco_code_parser_rejects_extra_segments() -> None:
    assert AmecoArchiveClient._parse_code("PRT.1.0.319.5.0.UYIG") is None
