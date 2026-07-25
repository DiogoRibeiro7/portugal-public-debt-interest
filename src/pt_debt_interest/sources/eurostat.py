"""Eurostat Dissemination API client."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from ..config import EurostatSeriesSpec, HttpSection
from ..exceptions import SourceError
from ..jsonstat import jsonstat_to_frame


class EurostatClient:
    """Fetch and cache annual Eurostat series from the JSON-stat API."""

    def __init__(self, base_url: str, http: HttpSection, raw_dir: Path) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = http
        self.raw_dir = raw_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def _request(self, dataset: str, params: list[tuple[str, str]]) -> dict[str, Any]:
        url = f"{self.base_url}/{dataset}"
        headers = {"Accept": "application/json"}
        last_error: Exception | None = None
        for attempt in range(self.http.max_retries):
            try:
                response = httpx.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.http.timeout_seconds,
                    follow_redirects=True,
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise SourceError(f"Eurostat {dataset} did not return a JSON object")
                return payload
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
        payload = self._request(spec.dataset, params)

        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        cache_path = self.raw_dir / f"eurostat_{name}_{stamp}.json"
        cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        frame = jsonstat_to_frame(payload)
        if frame.empty:
            raise SourceError(f"Eurostat series {name} returned no observations")
        if "time" not in frame.columns:
            raise SourceError(f"Eurostat series {name} has no time dimension")

        output = frame.loc[:, ["time", "value", "status"]].copy()
        output["year"] = pd.to_numeric(output["time"], errors="raise").astype(int)
        output[spec.value_name] = pd.to_numeric(output["value"], errors="coerce")
        output[f"{spec.value_name}_status"] = output["status"].astype("string")
        return output.loc[:, ["year", spec.value_name, f"{spec.value_name}_status"]]

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
