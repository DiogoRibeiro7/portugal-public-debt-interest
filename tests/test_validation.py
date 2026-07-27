import pandas as pd

from pt_debt_interest.validation import validate_dataset


def test_validation_passes_accounting_identity() -> None:
    frame = pd.DataFrame(
        {
            "year": [1995, 1996],
            "accounting_basis": ["ESA2010", "ESA2010"],
            "source": ["Eurostat", "Eurostat"],
            "source_vintage": ["", ""],
            "observation_status": ["observed", "observed"],
            "retrieval_timestamp_utc": ["", ""],
            "source_flags": ["", ""],
            "basis_break": [True, False],
            "interest_pct_gdp_official": [4.0, 3.8],
            "interest_pct_gdp_calculated": [4.0, 3.81],
            "debt_pct_gdp_official": [60.0, 61.0],
            "debt_pct_gdp_calculated": [60.01, 61.0],
            "interest_pct_gdp": [4.0, 3.8],
            "overall_balance_pct_gdp": [-4.0, -3.0],
            "primary_balance_pct_gdp": [0.0, 0.8],
        }
    )
    result = validate_dataset(frame, 1995, 1996, 0.15, 0.05)
    assert result["passed"] is True


def test_validation_reports_missing_core_columns() -> None:
    frame = pd.DataFrame({"source": ["Eurostat"]})

    result = validate_dataset(frame, 1995, 1996, 0.15, 0.05)
    check = next(item for item in result["checks"] if item["name"] == "core_columns_present")

    assert result["passed"] is False
    assert check["passed"] is False
    assert check["severity"] == "error"
    assert check["detail"] == "Missing core columns: ['year', 'accounting_basis']"


def test_validation_reports_missing_accounting_basis_without_crashing() -> None:
    frame = pd.DataFrame({"year": [1995], "source": ["Eurostat"]})

    result = validate_dataset(frame, 1995, 1996, 0.15, 0.05)
    check = next(item for item in result["checks"] if item["name"] == "core_columns_present")

    assert result["passed"] is False
    assert check["detail"] == "Missing core columns: ['accounting_basis']"


def test_validation_reports_missing_core_values_without_crashing() -> None:
    frame = pd.DataFrame(
        {
            "year": [1995, None],
            "accounting_basis": ["ESA2010", "ESA2010"],
        }
    )

    result = validate_dataset(frame, 1995, 1996, 0.15, 0.05)
    check = next(item for item in result["checks"] if item["name"] == "core_values_present")

    assert result["passed"] is False
    assert check["passed"] is False
    assert check["severity"] == "error"


def test_validation_reports_missing_accounting_basis_values() -> None:
    frame = pd.DataFrame(
        {
            "year": [1995, 1996],
            "accounting_basis": ["ESA2010", None],
        }
    )

    result = validate_dataset(frame, 1995, 1996, 0.15, 0.05)
    check = next(item for item in result["checks"] if item["name"] == "core_values_present")

    assert result["passed"] is False
    assert check["affected_years"] == [1996]


def test_validation_reports_non_numeric_year_values_without_crashing() -> None:
    frame = pd.DataFrame(
        {
            "year": [1995, "not-a-year"],
            "accounting_basis": ["ESA2010", "ESA2010"],
        }
    )

    result = validate_dataset(frame, 1995, 1996, 0.15, 0.05)
    check = next(item for item in result["checks"] if item["name"] == "year_values_numeric")

    assert result["passed"] is False
    assert check["passed"] is False
    assert check["severity"] == "error"


def test_validation_reports_all_duplicate_year_rows() -> None:
    frame = pd.DataFrame(
        {
            "year": [1995, 1995, 1996],
            "accounting_basis": ["ESA2010", "ESA2010", "ESA2010"],
        }
    )

    result = validate_dataset(frame, 1995, 1996, 0.15, 0.05)
    check = next(item for item in result["checks"] if item["name"] == "unique_years")

    assert result["passed"] is False
    assert check["affected_years"] == [1995, 1995]


def test_validation_fails_observed_forecast_collision() -> None:
    frame = pd.DataFrame(
        {
            "year": [2025, 2025],
            "accounting_basis": ["ESA2010", "ESA2010"],
            "source": ["Eurostat", "AMECO"],
            "source_vintage": ["", ""],
            "observation_status": ["observed", "forecast"],
            "retrieval_timestamp_utc": ["", ""],
            "source_flags": ["", ""],
            "basis_break": [False, False],
        }
    )
    result = validate_dataset(frame, 1995, 2025, 0.15, 0.05)
    assert result["passed"] is False
    check = next(
        item for item in result["checks"] if item["name"] == "observed_forecast_separation"
    )
    assert check["affected_years"] == [2025]


def test_validation_warns_on_missing_retrieval_timestamp() -> None:
    frame = pd.DataFrame(
        {
            "year": [2024],
            "accounting_basis": ["ESA2010"],
            "source": ["Eurostat"],
            "source_vintage": ["eurostat_interest_20260726T010000Z.json"],
            "observation_status": ["observed"],
            "retrieval_timestamp_utc": [""],
            "source_flags": [""],
            "basis_break": [False],
        }
    )

    result = validate_dataset(frame, 2024, 2024, 0.15, 0.05)
    check = next(
        item for item in result["checks"] if item["name"] == "retrieval_timestamps_present"
    )

    assert result["passed"] is True
    assert check["passed"] is False
    assert check["severity"] == "warning"
    assert check["affected_years"] == [2024]
