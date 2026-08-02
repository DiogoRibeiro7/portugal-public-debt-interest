"""ECB Data Portal acquisition: the covariates driving the behavioural hazard.

A retail certificate holder chooses between the certificate's remuneration and
the competing return on a household deposit. Those competing returns, the money
market, the sovereign curve, and the policy rate all come from the ECB Data
Portal's REST API, which serves SDMX-JSON and is machine-readable.

Each series is fetched independently with its own provenance sidecar, so a
partial outage degrades to a named gap rather than a silent hole.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from pt_debt_interest.exceptions import SourceError

from .provenance import FetchResult, fetch_with_provenance

BASE_URL = "https://data-api.ecb.europa.eu/service/data"


@dataclass(frozen=True)
class EcbSeries:
    """One fetched ECB series and its tidy frame."""

    name: str
    key: str
    fetch: FetchResult
    frame: pd.DataFrame


def _parse_sdmx_json(payload: bytes, name: str) -> pd.DataFrame:
    """Turn an SDMX-JSON message into a tidy period/value frame."""
    try:
        document: dict[str, Any] = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SourceError(f"{name}: ECB payload is not JSON") from exc

    try:
        structure = document["structure"]["dimensions"]["observation"][0]["values"]
        periods = [str(entry["id"]) for entry in structure]
        series_block = document["dataSets"][0]["series"]
    except (KeyError, IndexError) as exc:
        raise SourceError(
            f"{name}: unexpected ECB SDMX-JSON layout; the API contract changed"
        ) from exc

    if not series_block:
        raise SourceError(f"{name}: ECB returned no series for this key")

    observations = next(iter(series_block.values()))["observations"]
    records = []
    for index_text, values in observations.items():
        index = int(index_text)
        if index < len(periods) and values and values[0] is not None:
            records.append({"period": periods[index], "value": float(values[0])})

    frame = pd.DataFrame(records)
    if frame.empty:
        raise SourceError(f"{name}: ECB series contained no observations")
    frame["series"] = name
    return frame.sort_values("period").reset_index(drop=True)


def fetch_series(
    name: str,
    dataflow: str,
    key: str,
    raw_dir: Path,
    *,
    refresh: bool = False,
    timeout_seconds: float = 60.0,
) -> EcbSeries:
    """Fetch one ECB series by dataflow and series key."""
    url = f"{BASE_URL}/{dataflow}/{key}?format=jsondata"
    result = fetch_with_provenance(
        f"ecb_{name}",
        url,
        raw_dir,
        suffix=".json",
        refresh=refresh,
        timeout_seconds=timeout_seconds,
        extra_manifest={"publisher": "ECB", "dataflow": dataflow, "series_key": key},
    )
    return EcbSeries(
        name=name,
        key=key,
        fetch=result,
        frame=_parse_sdmx_json(result.content, name),
    )


def fetch_configured(
    series: dict[str, dict[str, str]],
    raw_dir: Path,
    *,
    refresh: bool = False,
    timeout_seconds: float = 60.0,
) -> dict[str, EcbSeries]:
    """Fetch every configured ECB series, reporting failures by name.

    A failure is raised rather than swallowed: a missing covariate changes what
    the estimation can identify, and that must not be discovered silently.
    """
    fetched: dict[str, EcbSeries] = {}
    failures: list[str] = []
    for name, spec in series.items():
        try:
            fetched[name] = fetch_series(
                name,
                spec["dataflow"],
                spec["key"],
                raw_dir,
                refresh=refresh,
                timeout_seconds=timeout_seconds,
            )
        except SourceError as exc:
            failures.append(f"{name}: {exc}")
    if failures:
        raise SourceError(
            "ECB acquisition incomplete; see docs/manual_ingest.md. " + " | ".join(failures)
        )
    return fetched
