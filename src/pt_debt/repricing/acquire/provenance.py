"""Fetching with provenance, shared by every acquisition module.

The interest-burden pipeline already established the discipline: a raw payload
is never mutated, and every fetch writes a sidecar recording the source, the
retrieval timestamp, the payload size, and the SHA-256 checksum. This module
carries that discipline into the repricing work rather than reimplementing it
per source.

Raw payloads are cached. A re-run with ``refresh=False`` reuses the newest
cached payload for a given name, so estimation work never re-hits a source.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from pt_debt_interest.exceptions import SourceError

#: Sidecar suffix, matching the burden pipeline's convention.
MANIFEST_SUFFIX = ".manifest.json"


def sha256_hex(content: bytes) -> str:
    """Return the SHA-256 of a payload."""
    return hashlib.sha256(content).hexdigest()


def utc_stamp() -> str:
    """Return a compact UTC timestamp usable in a filename."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


@dataclass(frozen=True)
class FetchResult:
    """A payload together with the sidecar describing where it came from."""

    name: str
    path: Path
    manifest_path: Path
    content: bytes
    sha256: str
    retrieved_at_utc: str
    source_url: str
    from_cache: bool

    @property
    def size_bytes(self) -> int:
        return len(self.content)


def _cached(raw_dir: Path, name: str, suffix: str) -> Path | None:
    """Return the newest cached payload for a name, if one exists.

    Sidecars are excluded explicitly. A JSON payload's sidecar also ends in
    ``.json``, so a naive glob picks the manifest and the parser then fails on
    a file that was never the payload.
    """
    candidates = sorted(
        path
        for path in raw_dir.glob(f"{name}_*{suffix}")
        if not path.name.endswith(MANIFEST_SUFFIX)
    )
    return candidates[-1] if candidates else None


def fetch_with_provenance(
    name: str,
    url: str,
    raw_dir: Path,
    *,
    suffix: str,
    timeout_seconds: float = 60.0,
    max_retries: int = 3,
    backoff_seconds: float = 1.0,
    headers: dict[str, str] | None = None,
    refresh: bool = False,
    extra_manifest: dict[str, Any] | None = None,
) -> FetchResult:
    """Fetch a payload, or reuse the newest cached copy.

    Raises
    ------
    SourceError
        If the payload cannot be retrieved and no cached copy exists. The
        pipeline halts loudly rather than proceeding with a gap.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)

    if not refresh:
        cached = _cached(raw_dir, name, suffix)
        if cached is not None:
            content = cached.read_bytes()
            manifest_path = cached.with_suffix(cached.suffix + MANIFEST_SUFFIX)
            manifest: dict[str, Any] = {}
            if manifest_path.is_file():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            return FetchResult(
                name=name,
                path=cached,
                manifest_path=manifest_path,
                content=content,
                sha256=str(manifest.get("sha256", sha256_hex(content))),
                retrieved_at_utc=str(manifest.get("retrieved_at_utc", "unknown")),
                source_url=str(manifest.get("source_url", url)),
                from_cache=True,
            )

    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = httpx.get(
                url,
                timeout=timeout_seconds,
                follow_redirects=True,
                headers=headers or {"User-Agent": "pt-debt-repricing/0.1"},
            )
            response.raise_for_status()
            content = response.content
            if not content:
                raise SourceError(f"{name}: empty payload from {url}")
            break
        except (httpx.HTTPError, SourceError) as exc:
            last_error = exc
            if attempt + 1 < max_retries:
                time.sleep(backoff_seconds * (attempt + 1))
    else:  # pragma: no cover - loop always breaks or exhausts
        content = b""

    if last_error is not None and not content:
        cached = _cached(raw_dir, name, suffix)
        if cached is not None:
            raise SourceError(
                f"{name}: could not retrieve {url} ({last_error}); a cached copy "
                f"exists at {cached} and can be used with refresh=False"
            )
        raise SourceError(
            f"{name}: could not retrieve {url} ({last_error}). No cached payload "
            "exists. See docs/manual_ingest.md for the manual-ingest route."
        )

    stamp = utc_stamp()
    path = raw_dir / f"{name}_{stamp}{suffix}"
    path.write_bytes(content)

    manifest = {
        "name": name,
        "source_url": url,
        "retrieved_at_utc": stamp,
        "size_bytes": len(content),
        "sha256": sha256_hex(content),
        "raw_file": path.name,
    }
    if extra_manifest:
        manifest.update(extra_manifest)
    manifest_path = path.with_suffix(path.suffix + MANIFEST_SUFFIX)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return FetchResult(
        name=name,
        path=path,
        manifest_path=manifest_path,
        content=content,
        sha256=str(manifest["sha256"]),
        retrieved_at_utc=stamp,
        source_url=url,
        from_cache=False,
    )
