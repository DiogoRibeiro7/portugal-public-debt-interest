from pathlib import Path

import pandas as pd

from pt_debt_interest.config import load_settings
from pt_debt_interest.pipeline import _canonicalise_annual_table, clear_ameco_interim


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


def test_clear_ameco_interim_removes_stale_file(tmp_path: Path) -> None:
    settings = load_settings("config/default.yaml")
    interim_dir = tmp_path / settings.paths.interim
    interim_dir.mkdir(parents=True)
    stale = interim_dir / "ameco_linked.csv"
    stale.write_text("year,value\n1994,1\n", encoding="utf-8")

    removed = clear_ameco_interim(settings, tmp_path)

    assert removed == stale
    assert not stale.exists()
