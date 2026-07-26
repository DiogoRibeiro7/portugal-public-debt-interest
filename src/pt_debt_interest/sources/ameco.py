"""AMECO archive downloader and linked-series parser."""

from __future__ import annotations

import hashlib
import io
import json
import re
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pandas as pd

from ..config import AmecoSelector, HttpSection
from ..exceptions import SourceError

YEAR_RE = re.compile(r"^(19|20)\d{2}$")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _validate_selectors(selectors: dict[str, AmecoSelector]) -> None:
    output_names = [selector.output_name for selector in selectors.values()]
    duplicates = sorted({name for name in output_names if output_names.count(name) > 1})
    if duplicates:
        raise SourceError(f"duplicate AMECO output columns configured: {duplicates}")


def _matches_selector(
    item: tuple[str, int, str] | None,
    country_code: str,
    unit_code: int,
    variable_code: str,
) -> bool:
    return bool(
        item
        and item[0] == country_code
        and item[1] == unit_code
        and item[2] == variable_code
    )


class AmecoArchiveClient:
    """Read AMECO CSV archives without assuming one fixed file layout."""

    def __init__(self, archive_url: str, http: HttpSection, raw_dir: Path) -> None:
        self.archive_url = archive_url
        self.http = http
        self.raw_dir = raw_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def download(self) -> Path:
        """Download the current AMECO CSV archive and preserve the raw file."""
        headers = {"Accept": "application/zip"}
        last_error: Exception | None = None
        for attempt in range(self.http.max_retries):
            try:
                response = httpx.get(
                    self.archive_url,
                    headers=headers,
                    timeout=self.http.timeout_seconds,
                    follow_redirects=True,
                )
                response.raise_for_status()
                stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
                destination = self.raw_dir / f"ameco_csv_{stamp}.zip"
                destination.write_bytes(response.content)
                manifest = {
                    "source": "AMECO",
                    "url": str(response.url),
                    "retrieval_time_utc": stamp,
                    "http_status": response.status_code,
                    "payload_size_bytes": len(response.content),
                    "sha256": _sha256(response.content),
                    "raw_file": destination.name,
                }
                (self.raw_dir / f"ameco_csv_{stamp}.manifest.json").write_text(
                    json.dumps(manifest, indent=2),
                    encoding="utf-8",
                )
                return destination
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt + 1 < self.http.max_retries:
                    time.sleep(self.http.backoff_seconds * (2**attempt))
        raise SourceError(f"failed to download AMECO archive: {last_error}")

    @staticmethod
    def _read_csv_bytes(content: bytes) -> pd.DataFrame:
        """Read an AMECO CSV member using delimiter and encoding fallbacks."""
        errors: list[Exception] = []
        for encoding in ("utf-8-sig", "latin-1"):
            for separator in (None, ";", ",", "\t"):
                try:
                    frame = pd.read_csv(
                        io.BytesIO(content),
                        sep=separator,
                        engine="python",
                        encoding=encoding,
                    )
                    if frame.shape[1] >= 2:
                        return frame
                except Exception as exc:  # pandas emits several parser exception types
                    errors.append(exc)
        raise SourceError(f"could not parse AMECO CSV member: {errors[-1] if errors else ''}")

    @staticmethod
    def _series_code_column(frame: pd.DataFrame) -> str | None:
        """Find the column containing AMECO dotted series codes."""
        aliases = {"code", "series", "series_code", "series code"}
        for column in frame.columns:
            if str(column).strip().lower() in aliases:
                return str(column)
        for column in frame.columns:
            sample = frame[column].dropna().astype(str).head(20)
            if not sample.empty and sample.str.count(r"\.").median() >= 5:
                return str(column)
        return None

    @staticmethod
    def _parse_code(code: str) -> tuple[str, int, str] | None:
        """Extract country, unit, and variable from an AMECO series code."""
        parts = str(code).strip().split(".")
        if len(parts) < 6:
            return None
        country = parts[0]
        variable = parts[-1]
        try:
            unit_code = int(float(parts[-3]))
        except ValueError:
            return None
        return country, unit_code, variable

    def extract(
        self,
        archive_path: Path,
        country_code: str,
        selectors: dict[str, AmecoSelector],
        start_year: int,
        end_year: int,
        forecast_cutoff_year: int,
    ) -> pd.DataFrame:
        """Extract configured series from every compatible CSV member in an archive."""
        _validate_selectors(selectors)
        pieces: list[pd.DataFrame] = []
        found_outputs: set[str] = set()
        matched_locations: dict[str, str] = {}
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.namelist():
                if not member.lower().endswith(".csv"):
                    continue
                frame = self._read_csv_bytes(archive.read(member))
                code_column = self._series_code_column(frame)
                if code_column is None:
                    continue
                year_columns = [
                    str(column) for column in frame.columns if YEAR_RE.match(str(column))
                ]
                if not year_columns:
                    continue

                metadata = frame[code_column].astype(str).map(self._parse_code)
                for selector in selectors.values():
                    mask = pd.Series(
                        [
                            _matches_selector(
                                item,
                                country_code,
                                selector.unit_code,
                                selector.variable_code,
                            )
                            for item in metadata
                        ],
                        index=metadata.index,
                    )
                    if not mask.any():
                        continue
                    match_count = int(mask.sum())
                    if match_count > 1:
                        raise SourceError(
                            f"AMECO selector {selector.output_name} matched "
                            f"{match_count} rows in {member}"
                        )
                    if selector.output_name in matched_locations:
                        raise SourceError(
                            f"AMECO selector {selector.output_name} matched multiple "
                            f"archive members: {matched_locations[selector.output_name]}, "
                            f"{member}"
                        )
                    selected = frame.loc[mask, [code_column, *year_columns]]
                    long = selected.melt(
                        id_vars=[code_column],
                        var_name="year",
                        value_name=selector.output_name,
                    )
                    long["year"] = pd.to_numeric(long["year"], errors="coerce")
                    long[selector.output_name] = pd.to_numeric(
                        long[selector.output_name], errors="coerce"
                    )
                    long[f"{selector.output_name}_series_code"] = selected[code_column].iloc[0]
                    long[f"{selector.output_name}_source_member"] = member
                    found_outputs.add(selector.output_name)
                    matched_locations[selector.output_name] = member
                    pieces.append(
                        long.loc[
                            :,
                            [
                                "year",
                                selector.output_name,
                                f"{selector.output_name}_series_code",
                                f"{selector.output_name}_source_member",
                            ],
                        ]
                    )

        if not pieces:
            raise SourceError(
                "none of the configured AMECO selectors were found; run the discovery command "
                "and verify country/unit codes"
            )
        missing = sorted(
            selector.output_name
            for selector in selectors.values()
            if selector.output_name not in found_outputs
        )
        if missing:
            raise SourceError(f"configured AMECO selectors were not found: {missing}")

        merged: pd.DataFrame | None = None
        for piece in pieces:
            merged = piece if merged is None else merged.merge(piece, on="year", how="outer")
        assert merged is not None
        merged = merged.drop_duplicates(subset=["year"]).copy()
        merged["year"] = merged["year"].astype(int)
        merged = merged.loc[merged["year"].between(start_year, end_year)]
        if merged.empty:
            raise SourceError(
                "configured AMECO selectors returned no observations in the requested "
                f"year range {start_year}-{end_year}"
            )
        merged["observation_status_ameco"] = merged["year"].map(
            lambda year: "observed" if year <= forecast_cutoff_year else "forecast"
        )
        merged["accounting_basis_ameco"] = "linked_ESA2010_ESA95_ESA79"
        return merged.sort_values("year").reset_index(drop=True)

    def discover(self, archive_path: Path, patterns: list[str]) -> pd.DataFrame:
        """Search AMECO members for rows whose code or metadata matches all patterns."""
        records: list[dict[str, str]] = []
        lowered = [pattern.lower() for pattern in patterns]
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.namelist():
                if not member.lower().endswith(".csv"):
                    continue
                frame = self._read_csv_bytes(archive.read(member))
                text_columns = [column for column in frame.columns if frame[column].dtype == object]
                if not text_columns:
                    continue
                for _, row in frame[text_columns].fillna("").astype(str).iterrows():
                    joined = " | ".join(row.tolist())
                    if all(pattern in joined.lower() for pattern in lowered):
                        records.append({"member": member, "match": joined[:500]})
        return pd.DataFrame(records)
