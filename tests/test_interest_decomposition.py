import numpy as np
import pandas as pd
import pytest

from pt_debt_interest.exceptions import ValidationError
from pt_debt_interest.interest_decomposition import (
    build_interest_burden_decomposition,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year": [2020, 2021, 2022],
            "interest_mio_eur": [2.0, 2.31, 2.875],
            "implicit_interest_rate_average_debt_decimal": [0.02, 0.022, 0.025],
            "debt_mio_eur": [100.0, 110.0, 120.0],
            "nominal_gdp_mio_eur": [100.0, 105.0, 112.0],
        }
    )


def test_interest_burden_decomposition_reconstructs_changes() -> None:
    result = build_interest_burden_decomposition(_frame())

    complete = result.dropna(
        subset=[
            "calculated_interest_burden_change_pp",
            "reconstructed_interest_burden_change_pp",
        ]
    )
    assert np.allclose(
        complete["calculated_interest_burden_change_pp"],
        complete["reconstructed_interest_burden_change_pp"],
    )
    assert np.allclose(
        complete["interest_burden_decomposition_residual_pp"],
        0.0,
        atol=1e-12,
    )


def test_interest_burden_decomposition_requires_inputs() -> None:
    frame = _frame().drop(columns=["debt_mio_eur"])

    with pytest.raises(ValidationError, match="missing columns"):
        build_interest_burden_decomposition(frame)


def test_interest_burden_decomposition_rejects_fractional_years() -> None:
    frame = _frame()
    frame.loc[1, "year"] = 2021.5

    with pytest.raises(ValidationError, match="whole-number years"):
        build_interest_burden_decomposition(frame)
