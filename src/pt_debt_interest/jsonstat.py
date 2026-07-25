"""Minimal, dependency-free JSON-stat 2 parser for Eurostat responses."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .exceptions import SourceError


def _ordered_categories(category_index: object) -> list[str]:
    """Return category codes in their declared JSON-stat order."""
    if isinstance(category_index, list):
        return [str(item) for item in category_index]
    if isinstance(category_index, dict):
        return [
            str(code)
            for code, _ in sorted(category_index.items(), key=lambda item: int(item[1]))
        ]
    raise SourceError("unsupported JSON-stat category index")


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
    for dimension in dimensions:
        try:
            index = dimension_meta[dimension]["category"]["index"]
        except (KeyError, TypeError) as exc:
            raise SourceError(f"missing category index for {dimension}") from exc
        categories.append(_ordered_categories(index))

    total_size = int(np.prod(sizes, dtype=np.int64))
    values_obj = payload.get("value", {})
    statuses_obj = payload.get("status", {})

    if isinstance(values_obj, list):
        values = {index: value for index, value in enumerate(values_obj)}
    elif isinstance(values_obj, dict):
        values = {int(index): value for index, value in values_obj.items()}
    else:
        raise SourceError("unsupported JSON-stat value container")

    if isinstance(statuses_obj, list):
        statuses = {index: value for index, value in enumerate(statuses_obj)}
    elif isinstance(statuses_obj, dict):
        statuses = {int(index): value for index, value in statuses_obj.items()}
    else:
        statuses = {}

    rows: list[dict[str, object]] = []
    for flat_index in range(total_size):
        if flat_index not in values and flat_index not in statuses:
            continue
        coordinates = np.unravel_index(flat_index, tuple(int(size) for size in sizes))
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
