import pandas as pd

from pt_debt_interest.pipeline import _canonicalise_annual_table


def test_canonical_table_adds_provenance_and_basis_break() -> None:
    frame = pd.DataFrame(
        {
            "year": [1994, 1995],
            "source": ["AMECO", "Eurostat"],
            "accounting_basis": ["linked_ESA2010_ESA95_ESA79", "ESA2010"],
            "observation_status": ["observed", "observed"],
        }
    )

    result = _canonicalise_annual_table(frame, 1995)

    assert "source_vintage" in result.columns
    assert "retrieval_timestamp_utc" in result.columns
    assert bool(result.loc[result["year"] == 1995, "basis_break"].iloc[0]) is True
    assert result["year"].tolist() == [1994, 1995]
