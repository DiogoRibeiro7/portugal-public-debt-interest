"""Presentation layer for generated tables and figures.

The analytical dataset stores decimal ratios. Nothing outside this module may
turn a ratio into a percentage or a percentage point, and nothing inside the
analytical layer may format a number for publication. Keeping the conversion in
one place is what stops a decimal ratio from being printed under a percentage
heading.

Publication labels also live here: internal snake_case identifiers are fine in
a dataframe and unacceptable in a printed table.
"""

from __future__ import annotations

import math
from typing import Final

#: Source note used wherever a generated artefact has no per-row provenance
#: metadata to report. Derived series have no accounting basis of their own.
SOURCE_NOTE: Final[str] = "Source: author calculations from Eurostat data."

#: Residuals below this magnitude are reported as a bound rather than a value,
#: so that floating-point noise never prints as a signed zero.
RESIDUAL_DISPLAY_FLOOR: Final[float] = 1e-10

#: Internal identifiers that must never reach a printed table.
PUBLICATION_LABELS: Final[dict[str, str]] = {
    "rate": "Financing cost",
    "debt_exposure": "Debt exposure",
    "tie": "Tie",
    "observed": "Observed",
    "rate_2014_with_exposure_2025": "2014 rate with 2025 debt exposure",
    "rate_2025_with_exposure_2014": "2025 rate with 2014 debt exposure",
}


def publication_label(identifier: object) -> str:
    """Map an internal identifier to its printed label.

    Unknown identifiers are humanised rather than passed through, so a new
    internal name cannot leak into the paper unnoticed.
    """
    text = str(identifier).strip()
    if text in PUBLICATION_LABELS:
        return PUBLICATION_LABELS[text]
    if "_with_exposure_" in text and text.startswith("rate_"):
        remainder = text[len("rate_") :]
        rate_year, _, exposure_year = remainder.partition("_with_exposure_")
        return f"{rate_year} rate with {exposure_year} debt exposure"
    return text.replace("_", " ").capitalize()


def as_percent(decimal_ratio: float) -> float:
    """Convert a decimal ratio to a percentage."""
    return float(decimal_ratio) * 100.0


def as_percentage_points(decimal_ratio: float) -> float:
    """Convert a decimal contribution to percentage points."""
    return float(decimal_ratio) * 100.0


def format_residual(value: object, digits: int = 3) -> str:
    """Format a reconciliation residual without printing a negative zero.

    A residual that is numerically zero to within floating-point noise is
    reported as a bound. Anything larger is printed at the requested precision,
    which means a real reconciliation failure stays visible.
    """
    try:
        numeric = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(numeric):
        return ""
    if abs(numeric) < RESIDUAL_DISPLAY_FLOOR:
        return "$< 10^{-10}$"
    formatted = f"{numeric:.{digits}f}"
    # Guard against a rounded-to-zero value carrying a sign.
    if float(formatted) == 0.0:
        return f"{0.0:.{digits}f}"
    return formatted


def round_components_to_total(
    components: list[float],
    total: float,
    digits: int,
) -> list[float]:
    """Round components so they add to the rounded total exactly.

    Rounding each component independently can leave a table that does not add
    up: three of the eight decomposition intervals drifted by one unit in the
    last place. The discrepancy is assigned to the component that was rounded
    furthest, so no component moves by more than one unit and the published
    arithmetic closes.
    """
    rounded_total = round(float(total), digits)
    rounded = [round(float(value), digits) for value in components]
    discrepancy = round(rounded_total - sum(rounded), digits)
    if discrepancy != 0.0 and rounded:
        errors = [
            abs(float(value) - rounded_value)
            for value, rounded_value in zip(components, rounded, strict=True)
        ]
        target = errors.index(max(errors))
        rounded[target] = round(rounded[target] + discrepancy, digits)
    return rounded


def components_sum_to_total(
    components: list[float],
    total: float,
    digits: int,
) -> bool:
    """Report whether displayed components add to the displayed total.

    The check is performed on the rounded values a reader actually sees, not on
    the unrounded inputs, because that is where a table stops adding up.
    """
    rounded_total = round(float(total), digits)
    rounded_components = sum(round(float(value), digits) for value in components)
    tolerance = 0.5 * 10.0**-digits
    return abs(rounded_components - rounded_total) <= tolerance
