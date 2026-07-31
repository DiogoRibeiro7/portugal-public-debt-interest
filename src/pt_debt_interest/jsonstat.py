"""Minimal, dependency-free JSON-stat 2 parser for Eurostat responses."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .exceptions import SourceError


def _integer_index(value: object, label: str) -> int:
    """Parse a JSON-stat index value without truncating non-integer numbers."""
    if isinstance(value, bool) or not isinstance(value, str | int | float):
        raise SourceError(f"JSON-stat {label} contains a non-integer index")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise SourceError(f"JSON-stat {label} contains a non-integer index") from exc
    if not np.isfinite(numeric) or numeric % 1 != 0:
        raise SourceError(f"JSON-stat {label} contains a non-integer index")
    return int(numeric)


def _dimension_size(value: object, dimension: str) -> int:
    """Parse a JSON-stat dimension size without truncating invalid values."""
    try:
        size = _integer_index(value, "dimension size")
    except SourceError as exc:
        raise SourceError(f"JSON-stat dimension {dimension} has invalid size") from exc
    if size < 0:
        raise SourceError(f"JSON-stat dimension {dimension} has invalid size")
    return size


def _ordered_categories(category_index: object, declared_size: int) -> list[str]:
    """Return category codes in their declared JSON-stat order."""
    if isinstance(category_index, list):
        ordered = [str(item) for item in category_index]
        if len(set(ordered)) != len(ordered):
            raise SourceError("JSON-stat category labels must be unique")
        return ordered
    if isinstance(category_index, dict):
        positions: list[int] = []
        pairs: list[tuple[str, int]] = []
        for code, raw_position in category_index.items():
            position = _integer_index(raw_position, "category index")
            if position < 0 or position >= declared_size:
                raise SourceError("JSON-stat category index position exceeds declared size")
            positions.append(position)
            pairs.append((str(code), position))
        if len(set(positions)) != len(positions):
            raise SourceError("JSON-stat category index positions must be unique")
        ordered = [
            str(code)
            for code, _ in sorted(pairs, key=lambda item: item[1])
        ]
        if len(set(ordered)) != len(ordered):
            raise SourceError("JSON-stat category labels must be unique")
        return ordered
    raise SourceError("unsupported JSON-stat category index")


def _indexed_values(container: object, total_size: int, label: str) -> dict[int, object]:
    if isinstance(container, list):
        if len(container) > total_size:
            raise SourceError(f"JSON-stat {label} length exceeds declared size")
        return {index: value for index, value in enumerate(container)}
    if isinstance(container, dict):
        values: dict[int, object] = {}
        for raw_index, value in container.items():
            index = _integer_index(raw_index, label)
            if index < 0 or index >= total_size:
                raise SourceError(f"JSON-stat {label} index {index} exceeds declared size")
            values[index] = value
        return values
    raise SourceError(f"unsupported JSON-stat {label} container")


def jsonstat_to_frame(payload: dict[str, Any]) -> pd.DataFrame:
    """Convert a Eurostat JSON-stat response into a tidy DataFrame.

    The parser supports sparse values represented as a dictionary and dense values
    represented as a list. It retains a `status` column when observation flags are
    available.
    """
    dimensions = payload.get("id")
    sizes = payload.get("size")
    dimension_meta = payload.get("dimension")
    if not isinstance(dimensions, list) or not isinstance(sizes, list):
        raise SourceError("JSON-stat response is missing id or size")
    if not isinstance(dimension_meta, dict):
        raise SourceError("JSON-stat response is missing dimension metadata")
    if len(dimensions) != len(sizes):
        raise SourceError("JSON-stat id and size lengths differ")

    categories: list[list[str]] = []
    parsed_sizes: list[int] = []
    for dimension, size in zip(dimensions, sizes, strict=True):
        declared_size = _dimension_size(size, str(dimension))
        try:
            index = dimension_meta[dimension]["category"]["index"]
        except (KeyError, TypeError) as exc:
            raise SourceError(f"missing category index for {dimension}") from exc
        ordered = _ordered_categories(index, declared_size)
        if len(ordered) != declared_size:
            raise SourceError(
                f"JSON-stat dimension {dimension} declares size {declared_size} "
                f"but has {len(ordered)} categories"
            )
        categories.append(ordered)
        parsed_sizes.append(declared_size)

    total_size = int(np.prod(parsed_sizes, dtype=np.int64))
    values_obj = payload.get("value", {})
    statuses_obj = payload.get("status", {})
    values = _indexed_values(values_obj, total_size, "value")
    statuses = _indexed_values(statuses_obj, total_size, "status")

    rows: list[dict[str, object]] = []
    for flat_index in range(total_size):
        if flat_index not in values and flat_index not in statuses:
            continue
        coordinates = np.unravel_index(flat_index, tuple(parsed_sizes))
        row: dict[str, object] = {
            dimension: categories[position][coordinate]
            for position, (dimension, coordinate) in enumerate(
                zip(dimensions, coordinates, strict=True)
            )
        }
        row["value"] = values.get(flat_index)
        row["status"] = statuses.get(flat_index)
        rows.append(row)

    columns = [*dimensions, "value", "status"]
    return pd.DataFrame(rows, columns=columns)
