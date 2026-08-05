"""The burden paper's outputs must not change.

Two research outputs now share one repository and one measurement layer. This
test is the contract between them: work on the repricing paper may import from
``pt_debt_interest`` but may not alter what it produces.

The baseline is a committed checksum manifest. Regenerate it deliberately, with
``python -m tests.test_burden_paper_regression --update``, only when the burden
paper's outputs are *intended* to change — and review the diff when you do.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE = REPO_ROOT / "tests" / "baselines" / "burden_paper_outputs.json"

#: Generated artefacts that define the burden paper.
#:
#: Figures used to be excluded because matplotlib embedded a creation
#: timestamp and randomised SVG element ids, so identical plots differed
#: byte-for-byte between runs. Both are now suppressed in ``plotting._save``,
#: the figures are reproducible, and every tracked figure PDF is checksummed
#: alongside the tables -- see :func:`_figure_paths`.
TRACKED = (
    "reports/tables/paper_headlines.tex",
    "reports/tables/summary_statistics.tex",
    "reports/tables/regime_averages.tex",
    "reports/tables/recent_dynamics.tex",
    "reports/tables/debt_dynamics_diagnostic_2020_2025.tex",
    "reports/tables/interest_burden_decomposition_endpoints.tex",
    "reports/tables/interest_burden_counterfactuals.tex",
    "reports/tables/static_sensitivities.tex",
    "reports/tables/annual_portugal_table.tex",
    "reports/tables/european_comparison_2025.tex",
    # The rank-change and fragility tables were outside this baseline while
    # both carried published errors -- a membership list evaluated at the
    # wrong year, and a tie lost to floating-point representation. They are
    # tracked now.
    "reports/tables/european_rank_change.tex",
    "reports/tables/european_rank_sensitivity_2025.tex",
    "reports/tables/refinancing_assumptions.tex",
    "reports/tables/interest_share_of_budget.tex",
    "reports/generated/debt_dynamics_context.json",
    "paper/portugal_public_debt_interest_report.tex",
)


#: Suffixes git may newline-convert. Binary artefacts are hashed as-is.
_TEXT_SUFFIXES = frozenset({".tex", ".json", ".csv", ".md"})


def _normalised(path: Path) -> bytes:
    """Return the file's bytes, with LF line endings for text artefacts.

    Hashing raw bytes made the baseline platform-dependent: with
    ``core.autocrlf`` set, the same commit checks out as CRLF on Windows and
    LF elsewhere, so the guard failed on a fresh clone for a reason unrelated
    to the analysis. ``.gitattributes`` now pins LF in the repository; this
    keeps the test honest regardless. Binary artefacts -- the figure PDFs --
    are never newline-converted and must be hashed untouched.
    """
    raw = path.read_bytes()
    if path.suffix.lower() not in _TEXT_SUFFIXES:
        return raw
    return raw.replace(b"\r\n", b"\n")


def _figure_paths() -> tuple[str, ...]:
    """Every committed figure PDF, in sorted order.

    Globbed rather than listed so a new figure joins the baseline the moment
    it is generated, instead of silently sitting outside it -- which is how
    the two rank tables came to carry published errors unguarded.
    """
    figures = REPO_ROOT / "reports" / "figures"
    if not figures.is_dir():
        return ()
    return tuple(
        sorted(path.relative_to(REPO_ROOT).as_posix() for path in figures.glob("*.pdf"))
    )


def _checksums() -> dict[str, str]:
    recorded: dict[str, str] = {}
    for relative in (*TRACKED, *_figure_paths()):
        path = REPO_ROOT / relative
        if path.is_file():
            recorded[relative] = hashlib.sha256(_normalised(path)).hexdigest()
    return recorded


def _write_baseline() -> Path:
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(json.dumps(_checksums(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return BASELINE


def test_burden_paper_outputs_are_unchanged() -> None:
    """Fail on any drift in the burden paper's generated artefacts."""
    if not BASELINE.is_file():
        pytest.skip(
            "no baseline recorded; run `python -m tests.test_burden_paper_regression --update`"
        )
    expected: dict[str, str] = json.loads(BASELINE.read_text(encoding="utf-8"))
    actual = _checksums()

    missing = sorted(set(expected) - set(actual))
    assert not missing, f"burden paper artefacts disappeared: {missing}"

    drifted = sorted(name for name, digest in expected.items() if actual.get(name) != digest)
    assert not drifted, (
        "the burden paper's outputs changed. If that was intended, regenerate "
        "the baseline deliberately and review the diff. Drifted: " + ", ".join(drifted)
    )


def test_baseline_covers_the_paper_and_its_tables() -> None:
    if not BASELINE.is_file():
        pytest.skip("no baseline recorded")
    expected = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert "paper/portugal_public_debt_interest_report.tex" in expected
    assert any(name.startswith("reports/tables/") for name in expected)


def test_repricing_package_does_not_import_into_the_burden_pipeline() -> None:
    """The burden paper must not depend on the repricing package.

    The CLI registers the repricing command group, which is a one-way edge. No
    module the burden pipeline actually uses may import ``pt_debt``.
    """
    package = REPO_ROOT / "src" / "pt_debt_interest"
    offenders = []
    for module in package.rglob("*.py"):
        if module.name == "cli.py":
            continue  # the deliberate, guarded registration point
        text = module.read_text(encoding="utf-8")
        if "pt_debt.repricing" in text or "from pt_debt " in text:
            offenders.append(module.relative_to(REPO_ROOT).as_posix())
    assert not offenders, f"burden pipeline imports repricing code: {offenders}"


if __name__ == "__main__":
    if "--update" in sys.argv:
        print(f"baseline written: {_write_baseline()}")
    else:
        print("pass --update to regenerate the baseline")
