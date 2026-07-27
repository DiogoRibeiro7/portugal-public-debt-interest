"""Eurostat Dissemination API client."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from ..config import EurostatSeriesSpec, HttpSection
from ..exceptions import SourceError
from ..jsonstat import jsonstat_to_frame


@dataclass(frozen=True)
class EurostatResponse:
    """Parsed Eurostat response with request provenance."""

    payload: dict[str, Any]
    content: bytes
    url: str
    status_code: int


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _category_values(payload: dict[str, Any], dimension: str) -> set[str]:
    try:
        index = payload["dimension"][dimension]["category"]["index"]
    except (KeyError, TypeError) as exc:
        raise SourceError(f"Eurostat response is missing dimension {dimension}") from exc
    if isinstance(index, list):
        return {str(value) for value in index}
    if isinstance(index, dict):
        return {str(value) for value in index}
    raise SourceError(f"Eurostat dimension {dimension} has unsupported category index")


def _validate_requested_dimensions(
    payload: dict[str, Any],
    filters: dict[str, str],
    dataset: str,
) -> None:
    dimensions = payload.get("id")
    sizes = payload.get("size")
    if not isinstance(dimensions, list) or not isinstance(sizes, list):
        raise SourceError(f"Eurostat {dataset} response is missing id or size")
    if len(dimensions) != len(sizes):
        raise SourceError(f"Eurostat {dataset} id and size lengths differ")
    dimension_sizes = dict(zip((str(item) for item in dimensions), sizes, strict=True))
    for dimension, expected in filters.items():
        if dimension not in dimension_sizes:
            raise SourceError(
                f"Eurostat {dataset} response omitted requested dimension {dimension}"
            )
        values = _category_values(payload, dimension)
        if values != {expected}:
            raise SourceError(
                f"Eurostat {dataset} returned {dimension}={sorted(values)}; expected {expected}"
            )
        if int(dimension_sizes[dimension]) != 1:
            raise SourceError(f"Eurostat {dataset} returned multiple values for {dimension}")


class EurostatClient:
    """Fetch and cache annual Eurostat series from the JSON-stat API."""

    def __init__(self, base_url: str, http: HttpSection, raw_dir: Path) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = http
        self.raw_dir = raw_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def _request(
        self,
        dataset: str,
        params: Sequence[tuple[str, str | int | float | bool | None]],
    ) -> EurostatResponse:
        url = f"{self.base_url}/{dataset}"
        headers = {"Accept": "application/json"}
        last_error: Exception | None = None
        for attempt in range(self.http.max_retries):
            try:
                response = httpx.get(
                    url,
                    params=list(params),
                    headers=headers,
                    timeout=self.http.timeout_seconds,
                    follow_redirects=True,
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise SourceError(f"Eurostat {dataset} did not return a JSON object")
                return EurostatResponse(
                    payload=payload,
                    content=response.content,
                    url=str(response.url),
                    status_code=response.status_code,
                )
            except (httpx.HTTPError, ValueError, SourceError) as exc:
                last_error = exc
                if attempt + 1 < self.http.max_retries:
                    time.sleep(self.http.backoff_seconds * (2**attempt))
        raise SourceError(f"failed to fetch Eurostat dataset {dataset}: {last_error}")

    def fetch_series(
        self,
        name: str,
        spec: EurostatSeriesSpec,
        start_year: int,
        end_year: int,
    ) -> pd.DataFrame:
        """Fetch one configured series and return year/value/status columns."""
        params: list[tuple[str, str]] = [
            ("lang", "en"),
            ("sinceTimePeriod", str(start_year)),
            ("untilTimePeriod", str(end_year)),
        ]
        params.extend((dimension, value) for dimension, value in spec.filters.items())
        source_response = self._request(spec.dataset, params)
        payload = source_response.payload
        _validate_requested_dimensions(payload, spec.filters, spec.dataset)

        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        cache_path = self.raw_dir / f"eurostat_{name}_{stamp}.json"
        cache_path.write_bytes(source_response.content)
        manifest_path = self.raw_dir / f"eurostat_{name}_{stamp}.manifest.json"
        manifest = {
            "source": "Eurostat",
            "dataset": spec.dataset,
            "url": source_response.url,
            "dimensions": list(spec.filters.keys()),
            "filters": spec.filters,
            "retrieval_time_utc": stamp,
            "http_status": source_response.status_code,
            "payload_size_bytes": len(source_response.content),
            "sha256": _sha256(source_response.content),
            "raw_file": cache_path.name,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        checksum = str(manifest["sha256"])
        raw_file = str(manifest["raw_file"])

        frame = jsonstat_to_frame(payload)
        if frame.empty:
            raise SourceError(f"Eurostat series {name} returned no observations")
        if "time" not in frame.columns:
            raise SourceError(f"Eurostat series {name} has no time dimension")

        output = frame.loc[:, ["time", "value", "status"]].copy()
        output["year"] = pd.to_numeric(output["time"], errors="raise").astype(int)
        duplicated_years = output.loc[
            output["year"].duplicated(keep=False),
            "year",
        ].tolist()
        if duplicated_years:
            raise SourceError(
                f"Eurostat series {name} returned duplicate years: {duplicated_years}"
            )
        output[spec.value_name] = pd.to_numeric(output["value"], errors="coerce")
        output[f"{spec.value_name}_status"] = output["status"].astype("string")
        output[f"{spec.value_name}_retrieval_timestamp_utc"] = stamp
        output[f"{spec.value_name}_source_sha256"] = checksum
        output[f"{spec.value_name}_raw_file"] = raw_file
        return output.loc[
            :,
            [
                "year",
                spec.value_name,
                f"{spec.value_name}_status",
                f"{spec.value_name}_retrieval_timestamp_utc",
                f"{spec.value_name}_source_sha256",
                f"{spec.value_name}_raw_file",
            ],
        ]

    def fetch_all(
        self,
        series: dict[str, EurostatSeriesSpec],
        start_year: int,
        end_year: int,
    ) -> pd.DataFrame:
        """Fetch and outer-join all configured Eurostat series."""
        merged: pd.DataFrame | None = None
        for name, spec in series.items():
            current = self.fetch_series(name, spec, start_year, end_year)
            merged = current if merged is None else merged.merge(current, on="year", how="outer")
        if merged is None:
            raise SourceError("no Eurostat series configured")
        return merged.sort_values("year").reset_index(drop=True)
