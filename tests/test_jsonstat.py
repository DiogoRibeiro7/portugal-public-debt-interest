import json
from pathlib import Path

from pt_debt_interest.jsonstat import jsonstat_to_frame


def test_jsonstat_to_frame_sparse_values() -> None:
    payload = json.loads(Path("tests/fixtures/eurostat_interest.json").read_text())
    frame = jsonstat_to_frame(payload)
    assert frame["time"].tolist() == ["2021", "2022", "2023"]
    assert frame["value"].tolist() == [5118.0, 4608.0, 5553.0]
    assert frame.loc[2, "status"] == "p"
