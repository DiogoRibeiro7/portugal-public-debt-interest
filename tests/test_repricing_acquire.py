"""Guards for the repricing acquisition layer.

Two things are protected here. The parsers must not silently truncate a series
when a publisher changes a header format part-way through a workbook — that
failure cost the full 2020-2026 window on the first attempt and produced a
coverage report that looked plausible and was wrong. And the burden paper's
pipeline must be unaffected by anything in this package.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from pt_debt.repricing.acquire.igcp import (
    INDICATOR_SERIES,
    STOCK_SERIES,
    _locate_date_row,
    _parse_period,
    _parse_periods,
    _tidy,
)
from pt_debt.repricing.acquire.provenance import sha256_hex, utc_stamp
from pt_debt_interest.exceptions import SourceError

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "repricing"


def _synthetic_stock_sheet() -> pd.DataFrame:
    """A sheet in the real shape: a footnote, then a mixed-format header."""
    header: list[object] = [None]
    header += [datetime(2001, month, 1) for month in range(1, 13)]
    header += [f"{name}/21" for name in ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun")]
    header += [f"{name}/21" for name in ("Jul", "Ago", "Set", "Out", "Nov", "Dez")]

    width = len(header)
    values = list(range(1, width))

    rows = [
        ["Dívida Direta do Estado / State direct debt"] + [None] * (width - 1),
        header,
        ["Dívida total / Total debt", *values],
        ["   OT / Fixed rate Treasury bonds (PGB)", *values],
        ["   Certific. Aforro / Saving Certificates", *values],
        ["   Certific. Tesouro / Treasury Certificates", *values],
        ["   Contas margem / Cash-collateral", *values],
        # A footnote repeating the wording but carrying no numbers.
        ["(*) Total debt series break note"] + [None] * (width - 1),
    ]
    return pd.DataFrame(rows)


def test_parse_period_handles_both_representations() -> None:
    assert _parse_period(datetime(2020, 10, 1)) == pd.Timestamp("2020-10-31")
    # Portuguese and English abbreviations both resolve.
    assert _parse_period("Dez/20") == pd.Timestamp("2020-12-31")
    assert _parse_period("Dec/20") == pd.Timestamp("2020-12-31")
    assert _parse_period("Fev/21") == pd.Timestamp("2021-02-28")
    assert _parse_period("Feb/21") == pd.Timestamp("2021-02-28")
    assert _parse_period("Set/22") == pd.Timestamp("2022-09-30")
    assert _parse_period("not a period") is None


def test_unknown_period_format_fails_loudly() -> None:
    """A changed layout must halt, not silently shorten the series."""
    header = pd.Series([datetime(2001, 1, 1), "Jan/21", "quarter 3 2022"])
    with pytest.raises(SourceError, match="layout has changed"):
        _parse_periods(header, "test")


def test_mixed_header_does_not_truncate_the_series() -> None:
    sheet = _synthetic_stock_sheet()
    tidy = _tidy(sheet, STOCK_SERIES, "test")

    periods = tidy.loc[tidy["series"].eq("total_debt_mio_eur"), "period"]
    assert len(periods) == 24, "the string-formatted tail was dropped"
    assert periods.min() == pd.Timestamp("2001-01-31")
    assert periods.max() == pd.Timestamp("2021-12-31")


def test_footnote_rows_are_not_mistaken_for_data() -> None:
    """A footnote repeating a series name carries no numbers and must be skipped."""
    sheet = _synthetic_stock_sheet()
    tidy = _tidy(sheet, {"total_debt_mio_eur": "Total debt"}, "test")
    assert tidy["value"].notna().all()


def test_missing_series_fails_loudly() -> None:
    sheet = _synthetic_stock_sheet()
    with pytest.raises(SourceError, match="expected series not found"):
        _tidy(sheet, {"absent": "No Such Series"}, "test")


def test_header_row_located_by_content() -> None:
    assert _locate_date_row(_synthetic_stock_sheet()) == 1


def test_provenance_helpers() -> None:
    assert sha256_hex(b"") == ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
    stamp = utc_stamp()
    assert len(stamp) == 16 and stamp.endswith("Z")


@pytest.mark.parametrize("series", [STOCK_SERIES, INDICATOR_SERIES])
def test_series_maps_are_non_empty(series: dict[str, str]) -> None:
    assert series
    assert all(key and value for key, value in series.items())


def test_acquired_payloads_carry_provenance_sidecars() -> None:
    """Every cached payload must have a sidecar recording where it came from."""
    if not RAW_DIR.is_dir():
        pytest.skip("no repricing payloads have been acquired")
    payloads = [
        path
        for path in RAW_DIR.iterdir()
        if path.is_file() and not path.name.endswith(".manifest.json")
    ]
    if not payloads:
        pytest.skip("no repricing payloads have been acquired")

    for payload in payloads:
        manifest = payload.with_suffix(payload.suffix + ".manifest.json")
        assert manifest.is_file(), f"{payload.name} has no provenance sidecar"
        import json

        recorded = json.loads(manifest.read_text(encoding="utf-8"))
        for field in ("source_url", "retrieved_at_utc", "size_bytes", "sha256"):
            assert field in recorded, f"{manifest.name} lacks {field}"
        assert recorded["sha256"] == sha256_hex(payload.read_bytes()), (
            f"{payload.name} does not match its recorded checksum"
        )
