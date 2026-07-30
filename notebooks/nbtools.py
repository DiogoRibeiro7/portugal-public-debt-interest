"""Shared helpers for the analysis notebooks.

The notebooks are readers, not producers: they consume the artefacts written by
``pt-debt all`` and never fetch from the network or rewrite ``data/``. This
module centralises path discovery, artefact loading, and the chart styling so
that every notebook renders the same way and fails with the same actionable
message when the pipeline has not been run.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure

__all__ = [
    "GRID",
    "INK",
    "MUTED",
    "NEGATIVE",
    "ORDINAL",
    "POSITIVE",
    "RECEDED",
    "SERIES",
    "SUBTLE",
    "SURFACE",
    "MissingArtefactError",
    "annotate_point",
    "artefact_inventory",
    "bar_colors",
    "dataset_vintage",
    "emphasis_palette",
    "figure",
    "finish",
    "headroom",
    "label_last_point",
    "load_counterfactuals",
    "load_dataset",
    "load_decomposition",
    "load_panel",
    "load_reproducibility",
    "load_settings",
    "load_validation",
    "main_series",
    "observed",
    "pct",
    "regime_spans",
    "repo_root",
    "shade_regimes",
    "signed_colors",
    "use_package",
    "use_style",
]

# Categorical slots in fixed order, light surface. Assign by entity, never by
# rank, and never cycle past the eighth slot. Validated for colour-vision
# deficiency on the adjacent-pair list (worst adjacent CVD dE 9.1, OKLab x100).
SERIES: tuple[str, ...] = (
    "#2a78d6",  # 1 blue
    "#eb6834",  # 2 orange
    "#1baf7a",  # 3 aqua
    "#eda100",  # 4 yellow
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 green
    "#4a3aa7",  # 7 violet
    "#e34948",  # 8 red
)

# Ordinal ramp: one hue, light to dark, for *ordered* categories such as a
# sweep of assumption values. The lightest step still clears 2:1 against the
# light surface, so no step disappears into the background.
ORDINAL: tuple[str, ...] = (
    "#86b6ef",
    "#5598e7",
    "#2a78d6",
    "#1c5cab",
    "#104281",
)

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
SUBTLE = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"

# Diverging poles for signed quantities. Warm and cool read as opposite; the
# midpoint stays neutral grey so "no change" reads as nothing.
POSITIVE = SERIES[7]  # red: adds to the burden
NEGATIVE = SERIES[0]  # blue: reduces the burden

_REGIME_BAND = "#f0efec"

# The tone every non-featured entity falls back to once the eight categorical
# hues are spoken for. Recessive, but still legible against the surface.
RECEDED = "#c3c2b7"


class MissingArtefactError(FileNotFoundError):
    """Raised when a notebook input has not been generated yet."""


def use_package(root: Path | None = None) -> Path | None:
    """Make ``pt_debt_interest`` importable from a plain checkout.

    The notebooks reuse the project library rather than reimplementing its
    formulas, but a clone that has not run ``pip install -e .`` cannot import
    it. Adding ``src`` to the path keeps the notebooks runnable either way and
    is a no-op when the package is already installed.
    """
    if importlib.util.find_spec("pt_debt_interest") is not None:
        return None
    source = (root or repo_root()) / "src"
    if source.is_dir() and str(source) not in sys.path:
        sys.path.insert(0, str(source))
        return source
    return None


def repo_root(start: Path | None = None) -> Path:
    """Return the repository root, whatever directory the kernel started in."""
    here = (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise MissingArtefactError(
        "could not locate the repository root: no pyproject.toml above "
        f"{here}. Start the kernel inside the checkout."
    )


def _require(path: Path, command: str) -> Path:
    if not path.is_file():
        raise MissingArtefactError(
            f"{path} is missing. Generate it with:\n\n"
            f"    {command}\n\n"
            "Processed data and figures are deliberately git-ignored, so a "
            "fresh checkout has to run the pipeline once before the notebooks "
            "can be re-executed."
        )
    return path


def load_dataset(root: Path | None = None) -> pd.DataFrame:
    """Load the annual analytical dataset produced by ``pt-debt build``."""
    base = root or repo_root()
    path = _require(
        base / "data" / "processed" / "portugal_debt_interest.csv",
        "pt-debt all --config config/default.yaml",
    )
    frame = pd.read_csv(path)
    return frame.sort_values("year").reset_index(drop=True)


def load_panel(root: Path | None = None) -> pd.DataFrame:
    """Load the European comparator panel produced by ``pt-debt build-panel``."""
    base = root or repo_root()
    path = _require(
        base / "data" / "processed" / "eurostat_panel_metrics.csv",
        "pt-debt fetch-panel && pt-debt build-panel",
    )
    frame = pd.read_csv(path)
    return frame.sort_values(["geo", "year"]).reset_index(drop=True)


def load_decomposition(root: Path | None = None) -> pd.DataFrame:
    """Load the endpoint interest-burden decomposition."""
    base = root or repo_root()
    path = _require(
        base / "data" / "processed" / "interest_burden_decomposition.csv",
        "pt-debt all --config config/default.yaml",
    )
    return pd.read_csv(path)


def load_counterfactuals(root: Path | None = None) -> pd.DataFrame:
    """Load the cross-rate and cross-exposure burden counterfactuals."""
    base = root or repo_root()
    path = _require(
        base / "data" / "processed" / "interest_burden_counterfactuals.csv",
        "pt-debt all --config config/default.yaml",
    )
    return pd.read_csv(path)


def load_validation(root: Path | None = None) -> dict[str, Any]:
    """Load the data-quality report produced by ``pt-debt validate``."""
    base = root or repo_root()
    path = _require(base / "reports" / "validation.json", "pt-debt validate")
    with path.open(encoding="utf-8") as handle:
        loaded: dict[str, Any] = json.load(handle)
    return loaded


def load_reproducibility(root: Path | None = None) -> dict[str, Any]:
    """Load the build metadata recorded alongside the processed dataset."""
    base = root or repo_root()
    path = _require(
        base / "reports" / "reproducibility.json",
        "pt-debt all --config config/default.yaml",
    )
    with path.open(encoding="utf-8") as handle:
        loaded: dict[str, Any] = json.load(handle)
    return loaded


def load_settings(root: Path | None = None) -> Any:
    """Load the typed project settings so notebooks reuse configured values."""
    base = root or repo_root()
    use_package(base)
    from pt_debt_interest.config import load_settings as _load_settings

    return _load_settings(base / "config" / "default.yaml")


def main_series(frame: pd.DataFrame) -> pd.DataFrame:
    """Return only the harmonised ESA 2010 rows.

    Any linked historical extension is kept out of every analytical statement:
    mixing accounting bases across a lag would silently corrupt growth rates,
    effective rates, and the debt-dynamics identity. The pipeline flags the
    sample directly; the accounting basis is the fallback for older vintages.
    """
    if "is_harmonised_main_sample" in frame.columns:
        selected = frame.loc[_boolean_flag(frame["is_harmonised_main_sample"])]
    else:
        selected = frame.loc[frame["accounting_basis"].eq("ESA2010")]
    return selected.sort_values("year").reset_index(drop=True)


def _boolean_flag(values: pd.Series) -> pd.Series:
    """Read a boolean column that may have round-tripped through CSV as text."""
    if values.dtype == bool:
        return values
    return values.astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def observed(frame: pd.DataFrame) -> pd.DataFrame:
    """Return only observed rows, excluding anything flagged as a forecast."""
    if "observation_status" not in frame.columns:
        return frame
    selected = frame.loc[frame["observation_status"].astype("string").ne("forecast")]
    return selected.reset_index(drop=True)


def dataset_vintage(frame: pd.DataFrame) -> dict[str, object]:
    """Summarise which vintage of the sources a loaded dataset came from."""
    main = main_series(frame)
    timestamps = (
        frame.get("retrieval_timestamp_utc", pd.Series(dtype="object"))
        .dropna()
        .astype(str)
        .str.split(";")
        .explode()
        .str.strip()
    )
    return {
        "rows": len(frame),
        "full_year_range": f"{int(frame['year'].min())}-{int(frame['year'].max())}",
        "esa2010_year_range": f"{int(main['year'].min())}-{int(main['year'].max())}",
        "sources": ", ".join(sorted(frame["source"].dropna().unique())),
        "accounting_bases": ", ".join(sorted(frame["accounting_basis"].dropna().unique())),
        "earliest_retrieval_utc": timestamps.min() if not timestamps.empty else "unknown",
        "latest_retrieval_utc": timestamps.max() if not timestamps.empty else "unknown",
    }


def artefact_inventory(root: Path | None = None) -> pd.DataFrame:
    """Report which pipeline artefacts exist, so a notebook states its inputs."""
    base = root or repo_root()
    expected = {
        "annual dataset": base / "data" / "processed" / "portugal_debt_interest.csv",
        "sqlite copy": base / "data" / "processed" / "portugal_debt_interest.sqlite",
        "comparator panel": base / "data" / "processed" / "eurostat_panel_metrics.csv",
        "burden decomposition": (base / "data" / "processed" / "interest_burden_decomposition.csv"),
        "validation report": base / "reports" / "validation.json",
        "source coverage": base / "reports" / "source_coverage.csv",
        "reproducibility metadata": base / "reports" / "reproducibility.json",
        "summary report": base / "reports" / "summary.md",
        "figure manifest": base / "reports" / "figures" / "figures_manifest.csv",
    }
    rows = [
        {
            "artefact": name,
            "path": path.relative_to(base).as_posix(),
            "present": path.is_file(),
            "size_kb": round(path.stat().st_size / 1024, 1) if path.is_file() else None,
        }
        for name, path in expected.items()
    ]
    return pd.DataFrame(rows)


def use_style() -> None:
    """Apply the shared chart style: thin marks, hairline grid, recessive chrome."""
    mpl.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            # 88 dpi keeps every committed notebook clear of the 500 kB
            # large-file limit while staying legible at full width.
            "figure.dpi": 88,
            "savefig.facecolor": SURFACE,
            "savefig.bbox": "tight",
            "axes.facecolor": SURFACE,
            "axes.edgecolor": GRID,
            "axes.labelcolor": SUBTLE,
            "axes.titlecolor": INK,
            "axes.titlesize": 12,
            "axes.titleweight": "600",
            "axes.titlelocation": "left",
            "axes.titlepad": 10,
            "axes.labelsize": 10,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "axes.prop_cycle": mpl.cycler(color=list(SERIES)),
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "grid.linestyle": "-",
            "lines.linewidth": 2.0,
            "lines.markersize": 4.5,
            "legend.frameon": False,
            "legend.fontsize": 9,
            "legend.labelcolor": SUBTLE,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "font.size": 10,
            "font.family": "sans-serif",
            "figure.autolayout": False,
        }
    )
    pd.set_option("display.max_columns", 60)
    pd.set_option("display.width", 160)
    pd.set_option("display.float_format", lambda value: f"{value:,.2f}")


def figure(
    height: float = 4.2,
    width: float = 9.6,
    nrows: int = 1,
    ncols: int = 1,
    **kwargs: Any,
) -> tuple[Figure, Any]:
    """Create a figure sized for a notebook column."""
    return plt.subplots(nrows, ncols, figsize=(width, height), **kwargs)


def finish(
    ax: Axes,
    title: str = "",
    subtitle: str = "",
    ylabel: str = "",
    xlabel: str = "",
    source: str = "Eurostat, ESA 2010 general government (D41PAY, GD, B1GQ, B9).",
) -> Axes:
    """Apply the shared titling, axis, and source-note treatment."""
    if title:
        ax.set_title(title, pad=26 if subtitle else 10)
    if subtitle:
        ax.text(
            0.0,
            1.015,
            subtitle,
            transform=ax.transAxes,
            fontsize=9.5,
            color=SUBTLE,
            va="bottom",
        )
    ax.set_ylabel(ylabel, color=SUBTLE)
    ax.set_xlabel(xlabel, color=SUBTLE)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    if source:
        ax.figure.text(0.0, -0.02, source, fontsize=8, color=MUTED, ha="left", va="top")
    return ax


def regime_spans(frame: pd.DataFrame) -> pd.DataFrame:
    """Return the regime periods with the short band numbers used on charts."""
    spans = (
        frame.dropna(subset=["regime"])
        .groupby("regime", sort=False)["year"]
        .agg(first_year="min", last_year="max")
        .sort_values("first_year")
    )
    spans.insert(0, "band", range(1, len(spans) + 1))
    spans["first_year"] = spans["first_year"].astype(int)
    spans["last_year"] = spans["last_year"].astype(int)
    return spans


def shade_regimes(ax: Axes, frame: pd.DataFrame, annotate: bool = True) -> Axes:
    """Shade alternating policy regimes behind the plot as a reading aid.

    Bands carry a short number rather than their full label: a rotated
    sentence inside the plot collides with the data it is meant to frame. The
    number-to-label mapping travels with the regime table.
    """
    if "regime" not in frame.columns:
        return ax
    spans = regime_spans(frame)
    top = ax.get_ylim()[1]
    for position, (_, row) in enumerate(spans.iterrows()):
        if position % 2 == 0:
            ax.axvspan(
                row["first_year"] - 0.5,
                row["last_year"] + 0.5,
                color=_REGIME_BAND,
                zorder=0,
            )
        if annotate:
            ax.text(
                (row["first_year"] + row["last_year"]) / 2,
                top,
                str(row["band"]),
                fontsize=8,
                color=MUTED,
                ha="center",
                va="top",
            )
    return ax


def headroom(ax: Axes, top: float = 1.20, bottom: float = 1.08) -> Axes:
    """Expand the y limits so marks, labels, and legends do not collide."""
    low, high = ax.get_ylim()
    ax.set_ylim(low * bottom if low < 0 else low, high * top if high > 0 else high)
    return ax


def annotate_point(
    ax: Axes,
    x: float,
    y: float,
    text: str,
    color: str = SUBTLE,
    dy: float = 10.0,
) -> Axes:
    """Annotate one point, nudging the alignment away from the plot edges."""
    left, right = ax.get_xlim()
    position = (x - left) / (right - left) if right > left else 0.5
    if position < 0.15:
        ha, dx = "left", 8.0
    elif position > 0.85:
        ha, dx = "right", -8.0
    else:
        ha, dx = "center", 0.0
    ax.annotate(
        text,
        xy=(x, y),
        xytext=(dx, dy),
        textcoords="offset points",
        fontsize=9,
        color=color,
        ha=ha,
    )
    return ax


def label_last_point(
    ax: Axes,
    years: Sequence[float],
    values: Sequence[float],
    label: str,
    color: str,
    fmt: str = "{:.1f}",
) -> Axes:
    """Direct-label the endpoint of a line, selectively rather than every point."""
    series = pd.Series(list(values), index=list(years)).dropna()
    if series.empty:
        return ax
    x = float(series.index[-1])
    y = float(series.iloc[-1])
    ax.annotate(
        f"{label} {fmt.format(y)}".strip(),
        xy=(x, y),
        xytext=(6, 0),
        textcoords="offset points",
        fontsize=9,
        color=color,
        va="center",
        ha="left",
    )
    return ax


def signed_colors(values: Iterable[float]) -> list[str]:
    """Colour signed bars on the diverging pair: warm adds, cool subtracts."""
    return [POSITIVE if value >= 0 else NEGATIVE for value in values]


def bar_colors(labels: Iterable[str], highlight: str) -> list[str]:
    """Emphasise one category and let the rest recede to a neutral tone."""
    return [SERIES[0] if label == highlight else RECEDED for label in labels]


def emphasis_palette(featured: Sequence[str]) -> dict[str, str]:
    """Assign categorical hues to the named entities only.

    A categorical palette carries eight hues. Past that, a ninth colour is
    indistinguishable from one already in use, so the honest move is to name
    the handful of entities the chart is actually about and let the rest recede
    into a single neutral tone. Colour still follows the entity, so a series
    keeps its hue no matter how the panel is filtered.
    """
    if len(featured) > len(SERIES):
        raise ValueError(
            f"at most {len(SERIES)} entities can carry a categorical hue; got {len(featured)}"
        )
    return {name: SERIES[position] for position, name in enumerate(featured)}


def pct(value: float | None, digits: int = 1) -> str:
    """Format a percentage for prose, tolerating missing values."""
    if value is None or pd.isna(value):
        return "n/a"
    return f"{value:.{digits}f}%"


# Importing this module is enough to make the project library importable, so a
# notebook can do `import nbtools` and then `from pt_debt_interest... import ...`
# in the same cell without an editable install.
use_package()
