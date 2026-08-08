"""Every file that declares a version must declare the same one.

A release bump touched pyproject.toml and CITATION.cff but not .zenodo.json,
so the archive would have been minted carrying the previous version number.
Nothing failed: each file was internally valid and no test compared them.
These tests are that comparison, and they enumerate the files rather than
grepping for a pattern, so a new metadata file has to be added here
deliberately instead of being silently skipped.
"""

from __future__ import annotations

import json
import re
import tomllib
from datetime import date
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
CITATION = REPO_ROOT / "CITATION.cff"
ZENODO = REPO_ROOT / ".zenodo.json"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
LOCKFILE = REPO_ROOT / "poetry.lock"
REPRODUCIBILITY = REPO_ROOT / "docs" / "reproducibility.md"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
REPORTS = REPO_ROOT / "reports"
FINAL_AUDIT = REPORTS / "final_audit.md"

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _pyproject_versions() -> dict[str, str]:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    found = {}
    if "project" in data and "version" in data["project"]:
        found["pyproject[project]"] = data["project"]["version"]
    poetry = data.get("tool", {}).get("poetry", {})
    if "version" in poetry:
        found["pyproject[tool.poetry]"] = poetry["version"]
    return found


def _declared_versions() -> dict[str, str]:
    versions = _pyproject_versions()
    versions["CITATION.cff"] = yaml.safe_load(CITATION.read_text(encoding="utf-8"))[
        "version"
    ]
    versions[".zenodo.json"] = json.loads(ZENODO.read_text(encoding="utf-8"))["version"]
    return versions


def _declared_dates() -> dict[str, str]:
    return {
        "CITATION.cff": str(
            yaml.safe_load(CITATION.read_text(encoding="utf-8"))["date-released"]
        ),
        ".zenodo.json": json.loads(ZENODO.read_text(encoding="utf-8"))[
            "publication_date"
        ],
    }


def test_every_metadata_file_exists() -> None:
    """If one is renamed or removed, fail loudly rather than skip it."""
    for path in (PYPROJECT, CITATION, ZENODO, CHANGELOG, LOCKFILE):
        assert path.is_file(), f"release metadata missing: {path.name}"


def test_all_declared_versions_agree() -> None:
    versions = _declared_versions()
    distinct = set(versions.values())
    assert len(distinct) == 1, f"version declarations disagree: {versions}"


def test_the_version_is_semver() -> None:
    for source, version in _declared_versions().items():
        assert SEMVER.match(version), f"{source} is not semver: {version!r}"


def test_release_dates_agree() -> None:
    dates = _declared_dates()
    assert len(set(dates.values())) == 1, f"release dates disagree: {dates}"


def test_release_date_is_parseable_and_not_in_the_future() -> None:
    for source, value in _declared_dates().items():
        try:
            parsed = date.fromisoformat(value)
        except ValueError:  # pragma: no cover - guarded by the assert
            pytest.fail(f"{source} date is not ISO-8601: {value!r}")
        assert parsed <= date.today(), f"{source} is dated in the future: {value}"


def test_the_changelog_records_this_version() -> None:
    """A release with no changelog entry is how v0.2.0 shipped undocumented."""
    version = next(iter(set(_declared_versions().values())))
    headings = re.findall(r"^## v(\d+\.\d+\.\d+)", CHANGELOG.read_text(encoding="utf-8"), re.M)
    assert version in headings, (
        f"CHANGELOG.md has no entry for v{version}; found {headings}"
    )


def test_zenodo_metadata_is_complete() -> None:
    """Fields Zenodo needs to mint a correctly labelled record."""
    data = json.loads(ZENODO.read_text(encoding="utf-8"))
    for field in ("title", "creators", "version", "publication_date", "license", "upload_type"):
        assert data.get(field), f".zenodo.json is missing {field}"
    assert data["creators"], ".zenodo.json declares no creators"


def test_final_audit_matches_current_release_metadata() -> None:
    """The root final audit must not carry stale release numbers."""
    version = next(iter(set(_declared_versions().values())))
    content = FINAL_AUDIT.read_text(encoding="utf-8")
    assert f"package version {version}" in content
    for obsolete in ("147 passed", "232 passed", "0.1.2", "24 pages", "348 passed"):
        assert obsolete not in content


def test_final_audit_records_the_clean_checkout_skip_count() -> None:
    content = FINAL_AUDIT.read_text(encoding="utf-8")
    assert "345 passed, 19 skipped" in content
    assert "348 passed, 16 skipped" not in content


def test_obsolete_final_audit_is_archived() -> None:
    assert not (REPORTS / "final_blocking_acceptance_audit.md").exists()
    assert (REPORTS / "archive" / "final_blocking_acceptance_audit_2026-07-31.md").is_file()


def test_dependency_lockfile_is_the_documented_install_path() -> None:
    lock = LOCKFILE.read_text(encoding="utf-8")
    assert "lock-version" in lock

    guide = REPRODUCIBILITY.read_text(encoding="utf-8")
    assert "poetry install --with dev" in guide
    assert "does not currently track a lock file" not in guide

    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "poetry.lock" in workflow
    assert "poetry install --with dev" in workflow
