import pytest
from pydantic import ValidationError

from pt_debt_interest.config import AnalysisSection


def test_analysis_config_rejects_excess_refinancing_shares() -> None:
    with pytest.raises(ValidationError, match="outstanding stock"):
        AnalysisSection(default_refinancing_shares=[0.6, 0.5])


def test_analysis_config_rejects_overlapping_regimes() -> None:
    with pytest.raises(ValidationError, match="must not overlap"):
        AnalysisSection(
            regime_boundaries=[
                {"start": 2000, "end": 2005, "label": "First"},
                {"start": 2005, "end": 2010, "label": "Second"},
            ]
        )


def test_analysis_config_rejects_reversed_regime() -> None:
    with pytest.raises(ValidationError, match="start must be before"):
        AnalysisSection(
            regime_boundaries=[
                {"start": 2010, "end": 2009, "label": "Invalid"},
            ]
        )
