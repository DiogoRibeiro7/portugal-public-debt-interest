"""Guards for repricing-model estimation helpers."""

from __future__ import annotations

import numpy as np

from pt_debt.repricing.estimate import _moving_block_indices


class _HighStartGenerator:
    def __init__(self) -> None:
        self.high: int | None = None

    def integers(self, low: int, high: int, size: int | tuple[int, ...]) -> np.ndarray:
        self.high = high
        return np.full(size, high - 1)


def test_moving_block_sampler_can_draw_the_last_valid_block() -> None:
    generator = _HighStartGenerator()
    indices = _moving_block_indices(10, 3, generator)  # type: ignore[arg-type]

    assert generator.high == 8
    assert 9 in indices
