"""IGCP acquisition: debt stock by instrument and debt indicators.

IGCP publishes two machine-readable historical series as Excel workbooks. They
are the backbone of the repricing risk set:

``debt_stock_monthly``
    State direct debt, monthly, split into fixed-rate Treasury bonds, savings
    certificates, and Treasury certificates. The retail split is what makes
    this paper possible at all.

``debt_indicators``
    Monthly share of fixed-rate debt, average residual maturity including and
    excluding programme loans, and modified duration.

What these workbooks do **not** contain is documented in
``docs/manual_ingest.md``: there is no per-ISIN detail, no dated redemption
schedule, and no gross retail subscription or redemption flow. Only net
outstanding stock. That limitation is structural and is reported rather than
worked around.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

import pandas as pd

from pt_debt_interest.exceptions import SourceError

from .provenance import FetchResult, fetch_with_provenance

#: Row labels are bilingual and stable across vintages; match on the English
#: fragment so a Portuguese wording change does not silently drop a series.
STOCK_SERIES: Final[dict[str, str]] = {
    "total_debt_mio_eur": "Total debt",
    "fixed_rate_bonds_mio_eur": "Fixed rate Treasury bonds",
    "savings_certificates_mio_eur": "Saving Certificates",
    "treasury_certificates_mio_eur": "Treasury Certificates",
    "cash_collateral_mio_eur": "Cash-collateral",
}

INDICATOR_SERIES: Final[dict[str, str]] = {
    "share_euro_debt_pct": "Percentage of EURO debt",
    "share_fixed_rate_pct": "Percentage of fixed rate",
    "average_residual_term_years": "Average residual term (years)",
    "modified_duration": "Modified duration",
}


@dataclass(frozen=True)
class IgcpWorkbook:
    """A downloaded IGCP workbook and the tidy frame parsed from it."""

    name: str
    fetch: FetchResult
    frame: pd.DataFrame


def _locate_date_row(raw: pd.DataFrame) -> int:
    """Find the row carrying the period headers.

    Located by content, because the workbooks put the header at different rows
    across vintages. Two traps are avoided deliberately. Cells are counted only
    when they are already datetimes, since a row of euro amounts will happily
    coerce to dates and would otherwise be mistaken for the header. And the
    richest such row wins rather than the first, because these workbooks carry
    a short partial header above the full one.
    """
    best_row = -1
    best_count = 0
    for index in range(min(12, raw.shape[0])):
        values = raw.iloc[index, 1:]
        count = sum(_parse_period(value) is not None for value in values)
        if count > best_count:
            best_row, best_count = index, count

    if best_count < 24:
        raise SourceError(
            "IGCP workbook layout has changed: no row of period headers was "
            "found in the first twelve rows"
        )
    return best_row


#: The workbooks switch part-way through from real Excel dates to abbreviated
#: month labels, and the abbreviations mix Portuguese and English. Both are
#: mapped explicitly rather than left to date inference, which silently drops
#: every Portuguese month and would truncate the series at 2020.
_MONTH_ABBREVIATIONS: Final[dict[str, int]] = {
    "jan": 1,
    "fev": 2,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "apr": 4,
    "mai": 5,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "aug": 8,
    "set": 9,
    "sep": 9,
    "out": 10,
    "oct": 10,
    "nov": 11,
    "dez": 12,
    "dec": 12,
}


def _parse_period(value: object) -> pd.Timestamp | None:
    """Parse one period header, in either representation."""
    if isinstance(value, datetime | pd.Timestamp):
        return pd.Timestamp(value) + pd.offsets.MonthEnd(0)
    text = str(value).strip()
    if "/" not in text:
        return None
    month_text, _, year_text = text.partition("/")
    month = _MONTH_ABBREVIATIONS.get(month_text.strip().lower()[:3])
    if month is None or not year_text.strip().isdigit():
        return None
    year = int(year_text.strip())
    year += 2000 if year < 100 else 0
    return pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)


def _parse_periods(header: pd.Series, source: str) -> pd.Series:
    """Parse the whole period header, failing loudly on an unknown format."""
    parsed = [_parse_period(value) for value in header]
    present = [value for value in header if pd.notna(value)]
    recognised = sum(1 for value in parsed if value is not None)
    if present and recognised < len(present):
        unknown = sorted(
            {
                str(raw_value)
                for raw_value, converted in zip(header, parsed, strict=True)
                if pd.notna(raw_value) and converted is None
            }
        )[:5]
        raise SourceError(
            f"IGCP {source}: {len(present) - recognised} period headers were not "
            f"recognised, so the layout has changed. Examples: {unknown}"
        )
    return pd.Series(parsed, dtype="datetime64[ns]")


def _tidy(raw: pd.DataFrame, wanted: dict[str, str], source: str) -> pd.DataFrame:
    """Reshape a wide IGCP sheet into a tidy period/series frame."""
    date_row = _locate_date_row(raw)
    periods = _parse_periods(raw.iloc[date_row, 1:], source)

    records: list[pd.DataFrame] = []
    missing: list[str] = []
    for column, fragment in wanted.items():
        # Footnotes repeat the series wording, so a label match alone is not
        # enough: the row must also carry numbers.
        matches = [
            index
            for index in range(raw.shape[0])
            if fragment.lower() in str(raw.iloc[index, 0]).lower()
            and pd.to_numeric(raw.iloc[index, 1:], errors="coerce").notna().any()
        ]
        if not matches:
            missing.append(f"{column} ({fragment!r})")
            continue
        values = pd.to_numeric(raw.iloc[matches[0], 1:], errors="coerce")
        records.append(
            pd.DataFrame(
                {
                    "period": periods.to_numpy(),
                    "series": column,
                    "value": values.to_numpy(),
                }
            )
        )

    if missing:
        raise SourceError(
            f"IGCP {source}: expected series not found, which means the layout "
            f"changed between vintages: {', '.join(missing)}"
        )

    tidy = pd.concat(records, ignore_index=True)
    tidy = tidy.dropna(subset=["period"])
    return tidy.sort_values(["series", "period"]).reset_index(drop=True)


def fetch_debt_stock(
    url: str,
    raw_dir: Path,
    *,
    refresh: bool = False,
    timeout_seconds: float = 90.0,
) -> IgcpWorkbook:
    """Fetch and parse the monthly State direct debt stock by instrument."""
    result = fetch_with_provenance(
        "igcp_debt_stock_monthly",
        url,
        raw_dir,
        suffix=".xlsx",
        refresh=refresh,
        timeout_seconds=timeout_seconds,
        extra_manifest={"publisher": "IGCP", "tier": 1},
    )
    raw = pd.read_excel(result.path, sheet_name=0, header=None)
    return IgcpWorkbook(
        name="debt_stock_monthly",
        fetch=result,
        frame=_tidy(raw, STOCK_SERIES, "debt stock"),
    )


def fetch_debt_indicators(
    url: str,
    raw_dir: Path,
    *,
    refresh: bool = False,
    timeout_seconds: float = 90.0,
) -> IgcpWorkbook:
    """Fetch and parse the monthly debt indicators, including residual maturity."""
    result = fetch_with_provenance(
        "igcp_debt_indicators",
        url,
        raw_dir,
        suffix=".xlsx",
        refresh=refresh,
        timeout_seconds=timeout_seconds,
        extra_manifest={"publisher": "IGCP", "tier": 1},
    )
    raw = pd.read_excel(result.path, sheet_name=0, header=None)
    return IgcpWorkbook(
        name="debt_indicators",
        fetch=result,
        frame=_tidy(raw, INDICATOR_SERIES, "debt indicators"),
    )
