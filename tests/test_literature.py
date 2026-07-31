"""Guards for the related-literature section and the bibliography.

The hard rule is that nothing may be fabricated. These tests cannot verify that
a work exists — that was done against publishers and issuing institutions when
the entries were written — but they do enforce completeness, mutual consistency
between citations and entries, and the absence of database entries masquerading
as literature.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PAPER = REPO_ROOT / "paper" / "portugal_public_debt_interest_report.tex"

#: Entries that are data sources, not literature. They may be cited, but they
#: do not count towards the literature requirement.
DATA_SOURCE_KEYS = frozenset({"esa2010", "eurostatgov", "igcp2024"})


def _paper() -> str:
    if not PAPER.is_file():
        pytest.skip("paper source is not present")
    return PAPER.read_text(encoding="utf-8")


def _bibliography(source: str) -> str:
    return source.split(r"\begin{thebibliography}")[1].split(r"\end{thebibliography}")[0]


def _entry_keys(source: str) -> list[str]:
    return re.findall(r"\\bibitem\{([^}]+)\}", _bibliography(source))


def _cited_keys(source: str) -> set[str]:
    body = source.split(r"\begin{thebibliography}")[0]
    keys: set[str] = set()
    for group in re.findall(r"\\cite\{([^}]+)\}", body):
        keys.update(key.strip() for key in group.split(","))
    return keys


def _literature_section(source: str) -> str:
    start = source.index(r"\section{Related Literature and Contribution}")
    end = source.index(r"\section{Discussion and Limitations}", start)
    return source[start:end]


def test_report_contains_a_related_literature_section() -> None:
    source = _paper()
    assert r"\section{Related Literature and Contribution}" in source


def test_bibliography_has_substantially_more_than_five_entries() -> None:
    keys = _entry_keys(_paper())
    assert len(keys) == len(set(keys)), "duplicate bibliography keys"

    literature = [key for key in keys if key not in DATA_SOURCE_KEYS]
    assert len(literature) > 5, (
        f"only {len(literature)} literature entries: {literature}"
    )


def test_no_database_only_bibliography_masquerading_as_literature() -> None:
    """Eurostat and AMECO database entries are sources, not literature."""
    section = _literature_section(_paper())
    for key in DATA_SOURCE_KEYS - {"igcp2024"}:
        assert f"\\cite{{{key}}}" not in section, (
            f"{key} is a database entry and must not be cited as literature"
        )
    # The retired AMECO entry must be gone entirely.
    assert "ameco" not in _entry_keys(_paper())


def test_every_reference_is_used_in_text() -> None:
    source = _paper()
    entries = set(_entry_keys(source))
    cited = _cited_keys(source)

    unused = entries - cited
    assert not unused, f"bibliography entries never cited: {sorted(unused)}"

    dangling = cited - entries
    assert not dangling, f"citations with no bibliography entry: {sorted(dangling)}"


def test_no_incomplete_citation() -> None:
    """Every entry needs an author or institution, a title, and a year."""
    bibliography = _bibliography(_paper())
    # The leading fragment is the thebibliography width argument, not an entry.
    blocks = bibliography.split(r"\bibitem")[1:]
    assert blocks

    for block in blocks:
        key = block.split("}")[0].lstrip("{")
        body = block.split("}", 1)[1]
        assert r"\emph{" in body, f"{key} has no italicised title or journal"
        assert len(body.strip()) > 40, f"{key} is too sparse to be a full citation"
        if key in DATA_SOURCE_KEYS - {"igcp2024"}:
            # Standing database references carry no single publication year.
            continue
        assert re.search(r"\(\d{4}\)", body), f"{key} has no year"


def test_no_fabricated_doi_format() -> None:
    """Any DOI present must be well formed; none may be invented free text."""
    bibliography = _bibliography(_paper())
    for doi in re.findall(r"\\doi\{([^}]+)\}", bibliography):
        assert doi.startswith("10."), f"malformed DOI: {doi}"
        assert "/" in doi, f"malformed DOI: {doi}"
        assert " " not in doi, f"DOI contains whitespace: {doi}"


def test_literature_section_covers_the_required_topics() -> None:
    section = _literature_section(_paper()).lower()
    for topic in (
        "debt-dynamics accounting",
        "interest-growth differential",
        "fiscal sustainability",
        "sovereign borrowing costs",
        "debt maturity and refinancing",
        "inflation and nominal growth",
        "stock-flow adjustments",
        "portuguese debt management",
    ):
        assert topic in section, f"the review does not cover {topic}"


def test_contribution_statement_is_explicit() -> None:
    section = _literature_section(_paper())
    assert "The contribution is measurement discipline" in section
    contribution = section.split("The contribution is measurement discipline")[1]
    for claim in (
        "auditable",
        "average financing cost",
        "decomposed exactly",
        "eligibility",
        "stylised",
    ):
        assert claim in contribution.lower(), (
            f"the contribution statement does not mention {claim}"
        )


def test_literature_section_length_is_within_target() -> None:
    section = _literature_section(_paper())
    text = re.sub(r"\\[a-zA-Z]+\**(\[[^\]]*\])?(\{[^}]*\})?", " ", section)
    words = [word for word in re.split(r"\s+", text) if word.strip(".,;:()$-")]
    assert 500 <= len(words) <= 1500, f"literature section is {len(words)} words"
