"""Monthly repricing panel for the subscription-margin design.

This replaces the event-history construction the competing-risks design called
for. That design needed observed exits; the data has net stock. The revision is
recorded in ``docs/repricing_design_revision.md``.

Unit of observation
-------------------
Instrument class by month. **Not** individual holders, and **not** ISIN level.
Retail certificate data is published as an aggregate stock, so the unit is a
class-month cell. An aggregate cell is not an individual-level model and the
manuscript must not describe it as one.

The repriced flow
-----------------
Money arriving on the prevailing rate reprices the stock whether it comes from
a new subscription or from a redemption and reissue. Only the net change is
observed, and gross subscriptions are at least the net change when the net
change is positive. So the repriced amount is **bounded below** by positive net
flow. That bound is the estimable object; the redemption margin is not
identified and is not modelled.

Clock
-----
Calendar time. The subscription margin is a flow responding to contemporaneous
conditions, not a survival object indexed by time since issuance, so there is
no duration clock here. Dropping it is a consequence of dropping the hazard.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pandas as pd

from pt_debt_interest.exceptions import ValidationError

#: Instrument classes carried in the panel, and whether the class reprices
#: through the behavioural (subscription) margin.
BEHAVIOURAL_CLASSES: Final[tuple[str, ...]] = (
    "savings_certificates",
    "treasury_certificates",
)

#: The June 2023 terms change that switched the subscription channel off. Dated
#: from the data: net flow falls from +670 million in June to +39 by October and
#: turns negative in November.
POLICY_BREAK: Final[pd.Timestamp] = pd.Timestamp("2023-06-30")


def _series(frame: pd.DataFrame, name: str) -> pd.Series:
    selected = frame.loc[frame["series"].eq(name)].dropna(subset=["value"])
    if selected.empty:
        raise ValidationError(f"repricing panel requires the {name} series")
    return selected.set_index("period")["value"].sort_index()


def build_repricing_panel(
    stock: pd.DataFrame,
    indicators: pd.DataFrame,
    covariates: dict[str, pd.Series],
) -> pd.DataFrame:
    """Build the monthly instrument-class panel.

    Parameters
    ----------
    stock:
        Tidy IGCP debt stock by instrument.
    indicators:
        Tidy IGCP debt indicators, for the maturity and fixed-rate share.
    covariates:
        Monthly covariate series keyed by name, already aligned to month end.
    """
    total = _series(stock, "total_debt_mio_eur")
    maturity = _series(indicators, "average_residual_term_years")
    fixed_share = _series(indicators, "share_fixed_rate_pct")

    frames: list[pd.DataFrame] = []
    for instrument in BEHAVIOURAL_CLASSES:
        outstanding = _series(stock, f"{instrument}_mio_eur")
        net_flow = outstanding.diff()
        panel = pd.DataFrame(
            {
                "period": outstanding.index,
                "instrument_class": instrument,
                "outstanding_mio_eur": outstanding.to_numpy(),
                "opening_outstanding_mio_eur": outstanding.shift(1).to_numpy(),
                "net_flow_mio_eur": net_flow.to_numpy(),
            }
        )
        # The positive part of the change in outstanding value.
        #
        # This is NOT a lower bound on gross household subscriptions, and an
        # earlier version of this file said it was. The published series is
        # outstanding *value*, which for Savings Certificates decomposes into
        # subscription principal and capitalised interest:
        #
        #     R_t = P_t + A_t   so   dR_t = dP_t + dA_t
        #
        # Series F pays quarterly and capitalises matured interest, so dA_t is
        # positive by construction and can create or enlarge a positive dR_t
        # with no new household money at all. IGCP's 2024 accounts make the
        # scale plain: the balance rose 684 million euro over the year, of
        # which subscription value contributed 63 and accrued interest 622.
        #
        # Worse for the estimation, capitalisation tracks the remuneration
        # formula, which for Series F is indexed to three-month Euribor. The
        # outcome can therefore move with rates through pure accounting, which
        # is a mechanical channel running in the same direction as the
        # behavioural one being tested. The name records what the quantity is.
        panel["outstanding_value_increase_mio_eur"] = panel["net_flow_mio_eur"].clip(
            lower=0.0
        )
        # Retained under the old name so downstream code and archived artefacts
        # keep working; both columns carry the same values and the same caveat.
        panel["repriced_lower_bound_mio_eur"] = panel[
            "outstanding_value_increase_mio_eur"
        ]
        panel["net_outflow_mio_eur"] = (-panel["net_flow_mio_eur"]).clip(lower=0.0)
        frames.append(panel)

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.dropna(subset=["opening_outstanding_mio_eur"])

    # Repricing intensity: the share of the opening stock repriced this month.
    combined["repriced_share"] = (
        combined["repriced_lower_bound_mio_eur"] / combined["opening_outstanding_mio_eur"]
    )

    combined["total_debt_mio_eur"] = combined["period"].map(total)
    combined["average_residual_term_years"] = combined["period"].map(maturity)
    combined["share_fixed_rate_pct"] = combined["period"].map(fixed_share)
    combined["share_of_total_debt"] = (
        combined["outstanding_mio_eur"] / combined["total_debt_mio_eur"]
    )

    for name, series in covariates.items():
        combined[name] = combined["period"].map(series)

    combined["post_policy_break"] = combined["period"] > POLICY_BREAK
    combined["months_since_policy_break"] = (
        combined["period"].dt.year - POLICY_BREAK.year
    ) * 12 + (combined["period"].dt.month - POLICY_BREAK.month)
    return combined.sort_values(["instrument_class", "period"]).reset_index(drop=True)


def add_competing_return_spread(
    panel: pd.DataFrame,
    short_rate_column: str,
    deposit_rate_column: str,
    lag_months: int = 1,
) -> pd.DataFrame:
    """Add the competing-return spread and its signed parts.

    The certificate's own remuneration rate is not published in machine-readable
    form (see ``docs/manual_ingest.md``). The formula tracked short rates, so a
    short-rate index stands in for the certificate leg. That is a proxy, not the
    contractual rate, and every result resting on it inherits that caveat.

    Covariates are lagged so that no estimate uses information a household could
    not have observed at the decision point.
    """
    output = panel.copy()
    spread = output[short_rate_column] - output[deposit_rate_column]
    output["competing_return_spread_pp"] = spread.groupby(output["instrument_class"]).shift(
        lag_months
    )
    # Entered separately so that widening and narrowing can load differently.
    output["spread_widening_pp"] = output["competing_return_spread_pp"].clip(lower=0.0)
    output["spread_narrowing_pp"] = (-output["competing_return_spread_pp"]).clip(lower=0.0)
    output["covariate_lag_months"] = lag_months
    return output


def validate_panel(panel: pd.DataFrame, tolerance_mio_eur: float = 1.0) -> pd.DataFrame:
    """Run the accounting and structural checks, returning a check table."""
    checks: list[dict[str, object]] = []

    def record(name: str, passed: bool, detail: str, severity: str = "error") -> None:
        checks.append({"check": name, "passed": passed, "severity": severity, "detail": detail})

    duplicated = panel.duplicated(subset=["instrument_class", "period"]).sum()
    record(
        "unique_class_period",
        duplicated == 0,
        f"{duplicated} duplicated instrument-class months",
    )

    negative = (panel["outstanding_mio_eur"] < 0).sum()
    record("non_negative_exposure", negative == 0, f"{negative} negative exposures")

    # Opening stock plus net flow must equal closing stock, by construction.
    residual = (
        panel["opening_outstanding_mio_eur"]
        + panel["net_flow_mio_eur"]
        - panel["outstanding_mio_eur"]
    ).abs()
    worst = float(residual.max()) if len(residual) else 0.0
    record(
        "stock_flow_closure",
        worst <= tolerance_mio_eur,
        f"largest opening-plus-flow residual {worst:.6f} EUR million",
    )

    share = panel["repriced_share"].dropna()
    record(
        "repriced_share_in_range",
        bool(((share >= 0) & (share <= 1.0)).all()),
        f"repriced share spans {share.min():.4f} to {share.max():.4f}",
        severity="warning",
    )

    coverage = panel.groupby("instrument_class")["period"].agg(["min", "max", "size"])
    record(
        "coverage_reported",
        True,
        "; ".join(
            f"{name}: {row['min'].date()}..{row['max'].date()} n={row['size']}"
            for name, row in coverage.iterrows()
        ),
        severity="info",
    )
    return pd.DataFrame(checks)


def reconcile_to_aggregate_debt(
    panel: pd.DataFrame,
    burden_frame: pd.DataFrame,
) -> pd.DataFrame:
    """Reconcile IGCP State direct debt against the burden paper's Maastricht debt.

    This is the cross-check between the two papers. The two are **not** the same
    concept: IGCP publishes State direct debt, the burden paper uses general
    government consolidated gross debt under the excessive deficit procedure.
    A gap is expected. The point is to report it per year rather than to assert
    agreement, so a reader can see whether it is stable.
    """
    annual = (
        panel.loc[panel["period"].dt.month.eq(12), ["period", "total_debt_mio_eur"]]
        .drop_duplicates("period")
        .assign(year=lambda frame: frame["period"].dt.year)
        .set_index("year")["total_debt_mio_eur"]
    )
    maastricht = (
        burden_frame.dropna(subset=["debt_mio_eur"]).set_index("year")["debt_mio_eur"].astype(float)
    )
    shared = sorted(set(annual.index) & set(maastricht.index))
    if not shared:
        raise ValidationError("no overlapping years between the two debt concepts")

    comparison = pd.DataFrame(
        {
            "year": shared,
            "igcp_state_direct_debt_mio_eur": [float(annual[year]) for year in shared],
            "maastricht_debt_mio_eur": [float(maastricht[year]) for year in shared],
        }
    )
    comparison["difference_mio_eur"] = (
        comparison["maastricht_debt_mio_eur"] - comparison["igcp_state_direct_debt_mio_eur"]
    )
    comparison["difference_pct_of_maastricht"] = (
        comparison["difference_mio_eur"] / comparison["maastricht_debt_mio_eur"] * 100.0
    )
    return comparison


def write_panel(panel: pd.DataFrame, processed_dir: Path) -> dict[str, Path]:
    """Persist the panel as parquet with a CSV extract."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}
    csv_path = processed_dir / "repricing_panel.csv"
    panel.to_csv(csv_path, index=False)
    outputs["csv"] = csv_path
    try:
        parquet_path = processed_dir / "repricing_panel.parquet"
        panel.to_parquet(parquet_path, index=False)
        outputs["parquet"] = parquet_path
    except (ImportError, ValueError):
        # A parquet engine is optional; the CSV is the portable artefact.
        pass
    return outputs
