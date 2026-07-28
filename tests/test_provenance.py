from pathlib import Path

import pandas as pd

from pt_debt_interest.config import load_settings
from pt_debt_interest.pipeline import (
    _add_eurostat_row_provenance,
    write_source_coverage_report,
)


def test_add_eurostat_row_provenance_adds_source_database_and_series() -> None:
    frame = pd.DataFrame(
        {
            "year": [2024],
            "interest_mio_eur_retrieval_timestamp_utc": ["20260726T010000Z"],
            "interest_mio_eur_source_sha256": ["abc"],
            "interest_mio_eur_raw_file": ["eurostat_interest_20260726T010000Z.json"],
        }
    )

    result = _add_eurostat_row_provenance(frame)

    assert result.loc[0, "source_database"] == "Eurostat"
    assert result.loc[0, "source_table_or_series"] == (
        "eurostat_interest_20260726T010000Z.json"
    )


def test_write_source_coverage_report_summarises_complete_rows(tmp_path: Path) -> None:
    settings = load_settings("config/default.yaml")
    frame = pd.DataFrame(
        {
            "year": [2024, 2025],
            "source": ["Eurostat", "Eurostat"],
            "source_database": ["Eurostat", "Eurostat"],
            "accounting_basis": ["ESA2010", "ESA2010"],
            "observation_status": ["observed", "observed"],
            "is_harmonised_main_sample": [True, True],
            "is_historical_extension": [False, False],
            "interest_mio_eur": [1.0, None],
            "nominal_gdp_mio_eur": [100.0, 100.0],
            "debt_mio_eur": [90.0, 91.0],
        }
    )

    destination = write_source_coverage_report(frame, settings, tmp_path)
    result = pd.read_csv(destination)

    assert result.loc[0, "row_count"] == 2
    assert result.loc[0, "complete_core_rows"] == 1
