"""AMECO archive downloader and linked-series parser."""

from __future__ import annotations

import io
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
        pieces: list[pd.DataFrame] = []
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.namelist():
                if not member.lower().endswith(".csv"):
                    continue
                frame = self._read_csv_bytes(archive.read(member))
                code_column = self._series_code_column(frame)
                if code_column is None:
                    continue
                year_columns = [str(column) for column in frame.columns if YEAR_RE.match(str(column))]
                if not year_columns:
                    continue

                metadata = frame[code_column].astype(str).map(self._parse_code)
                for selector in selectors.values():
                    mask = metadata.map(
                        lambda item: bool(
                            item
                            and item[0] == country_code
                            and item[1] == selector.unit_code
                            and item[2] == selector.variable_code
                        )
                    )
                    if not mask.any():
                        continue
                    selected = frame.loc[mask, [code_column, *year_columns]].head(1)
                    long = selected.melt(
                        id_vars=[code_column],
                        var_name="year",
                        value_name=selector.output_name,
                    )
                    long["year"] = pd.to_numeric(long["year"], errors="coerce")
                    long[selector.output_name] = pd.to_numeric(
                        long[selector.output_name], errors="coerce"
                    )
                    pieces.append(long.loc[:, ["year", selector.output_name]])

        if not pieces:
            raise SourceError(
                "none of the configured AMECO selectors were found; run the discovery command "
                "and verify country/unit codes"
            )

        merged: pd.DataFrame | None = None
        for piece in pieces:
            merged = piece if merged is None else merged.merge(piece, on="year", how="outer")
        assert merged is not None
        merged = merged.drop_duplicates(subset=["year"]).copy()
        merged["year"] = merged["year"].astype(int)
        merged = merged.loc[merged["year"].between(start_year, end_year)]
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
