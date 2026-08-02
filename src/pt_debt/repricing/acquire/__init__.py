"""Acquisition modules, one per source family."""

from .provenance import FetchResult, fetch_with_provenance

__all__ = ["FetchResult", "fetch_with_provenance"]
