import json
from pathlib import Path

import pytest

from pt_debt_interest.config import EurostatSeriesSpec, HttpSection
from pt_debt_interest.exceptions import SourceError
from pt_debt_interest.jsonstat import jsonstat_to_frame
from pt_debt_interest.sources.eurostat import EurostatClient


def test_jsonstat_to_frame_sparse_values() -> None:
    payload = json.loads(Path("tests/fixtures/eurostat_interest.json").read_text())
    frame = jsonstat_to_frame(payload)
    assert frame["time"].tolist() == ["2021", "2022", "2023"]
    assert frame["value"].tolist() == [5118.0, 4608.0, 5553.0]
    assert frame.loc[2, "status"] == "p"


def test_jsonstat_to_frame_rejects_dimension_size_mismatch() -> None:
    payload = json.loads(Path("tests/fixtures/eurostat_interest.json").read_text())
    payload["size"][-1] = 4

    with pytest.raises(SourceError, match="declares size 4"):
        jsonstat_to_frame(payload)


def test_jsonstat_to_frame_rejects_fractional_dimension_size() -> None:
    payload = json.loads(Path("tests/fixtures/eurostat_interest.json").read_text())
    payload["size"][-1] = 3.5

    with pytest.raises(SourceError, match="dimension time has invalid size"):
        jsonstat_to_frame(payload)


def test_jsonstat_to_frame_rejects_negative_dimension_size() -> None:
    payload = json.loads(Path("tests/fixtures/eurostat_interest.json").read_text())
    payload["size"][-1] = -1

    with pytest.raises(SourceError, match="dimension time has invalid size"):
        jsonstat_to_frame(payload)


def test_jsonstat_to_frame_rejects_out_of_range_sparse_index() -> None:
    payload = json.loads(Path("tests/fixtures/eurostat_interest.json").read_text())
    payload["value"]["99"] = 1.0

    with pytest.raises(SourceError, match="index 99 exceeds declared size"):
        jsonstat_to_frame(payload)


def test_jsonstat_to_frame_rejects_non_integer_sparse_index() -> None:
    payload = json.loads(Path("tests/fixtures/eurostat_interest.json").read_text())
    payload["status"] = {"bad": "p"}

    with pytest.raises(SourceError, match="non-integer index"):
        jsonstat_to_frame(payload)


def test_jsonstat_to_frame_rejects_fractional_sparse_index() -> None:
    payload = json.loads(Path("tests/fixtures/eurostat_interest.json").read_text())
    payload["status"] = {1.5: "p"}

    with pytest.raises(SourceError, match="non-integer index"):
        jsonstat_to_frame(payload)


def test_jsonstat_to_frame_rejects_duplicate_category_positions() -> None:
    payload = json.loads(Path("tests/fixtures/eurostat_interest.json").read_text())
    payload["dimension"]["time"]["category"]["index"] = {
        "2021": 0,
        "2022": 0,
        "2023": 2,
    }

    with pytest.raises(SourceError, match="positions must be unique"):
        jsonstat_to_frame(payload)


def test_jsonstat_to_frame_rejects_out_of_range_category_position() -> None:
    payload = json.loads(Path("tests/fixtures/eurostat_interest.json").read_text())
    payload["dimension"]["time"]["category"]["index"] = {
        "2021": 0,
        "2022": 1,
        "2023": 99,
    }

    with pytest.raises(SourceError, match="position exceeds declared size"):
        jsonstat_to_frame(payload)


def test_jsonstat_to_frame_rejects_fractional_category_position() -> None:
    payload = json.loads(Path("tests/fixtures/eurostat_interest.json").read_text())
    payload["dimension"]["time"]["category"]["index"] = {
        "2021": 0,
        "2022": 1.5,
        "2023": 2,
    }

    with pytest.raises(SourceError, match="non-integer index"):
        jsonstat_to_frame(payload)


def test_eurostat_client_rejects_unexpected_dimension(tmp_path: Path) -> None:
    payload = json.loads(Path("tests/fixtures/eurostat_interest.json").read_text())
    payload["dimension"]["geo"]["category"]["index"] = {"PT": 0, "ES": 1}
    payload["size"][4] = 2

    client = EurostatClient("https://example.invalid", HttpSection(), tmp_path)
    spec = EurostatSeriesSpec(
        dataset="gov_10a_main",
        filters={
            "freq": "A",
            "unit": "MIO_EUR",
            "sector": "S13",
            "na_item": "D41PAY",
            "geo": "PT",
        },
        value_name="interest_mio_eur",
    )

    def fake_request(dataset: str, params: list[tuple[str, str]]):
        return type(
            "Response",
            (),
            {
                "payload": payload,
                "content": json.dumps(payload).encode("utf-8"),
                "url": "https://example.invalid",
                "status_code": 200,
            },
        )()

    client._request = fake_request

    with pytest.raises(SourceError, match="returned geo"):
        client.fetch_series("interest", spec, 2021, 2023)


def test_eurostat_client_rejects_id_size_mismatch(tmp_path: Path) -> None:
    payload = json.loads(Path("tests/fixtures/eurostat_interest.json").read_text())
    payload["size"] = payload["size"][:-1]
    client = EurostatClient("https://example.invalid", HttpSection(), tmp_path)
    spec = EurostatSeriesSpec(
        dataset="gov_10a_main",
        filters={
            "freq": "A",
            "unit": "MIO_EUR",
            "sector": "S13",
            "na_item": "D41PAY",
            "geo": "PT",
        },
        value_name="interest_mio_eur",
    )

    def fake_request(dataset: str, params: list[tuple[str, str]]):
        return type(
            "Response",
            (),
            {
                "payload": payload,
                "content": json.dumps(payload).encode("utf-8"),
                "url": "https://example.invalid",
                "status_code": 200,
            },
        )()

    client._request = fake_request

    with pytest.raises(SourceError, match="id and size lengths differ"):
        client.fetch_series("interest", spec, 2021, 2023)


def test_eurostat_client_returns_raw_provenance(tmp_path: Path) -> None:
    payload = json.loads(Path("tests/fixtures/eurostat_interest.json").read_text())
    client = EurostatClient("https://example.invalid", HttpSection(), tmp_path)
    spec = EurostatSeriesSpec(
        dataset="gov_10a_main",
        filters={
            "freq": "A",
            "unit": "MIO_EUR",
            "sector": "S13",
            "na_item": "D41PAY",
            "geo": "PT",
        },
        value_name="interest_mio_eur",
    )

    def fake_request(dataset: str, params: list[tuple[str, str]]):
        return type(
            "Response",
            (),
            {
                "payload": payload,
                "content": json.dumps(payload).encode("utf-8"),
                "url": "https://example.invalid",
                "status_code": 200,
            },
        )()

    client._request = fake_request

    frame = client.fetch_series("interest", spec, 2021, 2023)

    assert "interest_mio_eur_retrieval_timestamp_utc" in frame.columns
    assert "interest_mio_eur_source_sha256" in frame.columns
    assert "interest_mio_eur_raw_file" in frame.columns
    assert list(tmp_path.glob("eurostat_interest_*.manifest.json"))


def test_eurostat_client_rejects_duplicate_time_labels(tmp_path: Path) -> None:
    payload = json.loads(Path("tests/fixtures/eurostat_interest.json").read_text())
    payload["dimension"]["time"]["category"]["index"] = ["2021", "2021", "2022"]
    client = EurostatClient("https://example.invalid", HttpSection(), tmp_path)
    spec = EurostatSeriesSpec(
        dataset="gov_10a_main",
        filters={
            "freq": "A",
            "unit": "MIO_EUR",
            "sector": "S13",
            "na_item": "D41PAY",
            "geo": "PT",
        },
        value_name="interest_mio_eur",
    )

    def fake_request(dataset: str, params: list[tuple[str, str]]):
        return type(
            "Response",
            (),
            {
                "payload": payload,
                "content": json.dumps(payload).encode("utf-8"),
                "url": "https://example.invalid",
                "status_code": 200,
            },
        )()

    client._request = fake_request

    with pytest.raises(SourceError, match="duplicate years"):
        client.fetch_series("interest", spec, 2021, 2023)


def test_eurostat_client_rejects_fractional_time_labels(tmp_path: Path) -> None:
    payload = json.loads(Path("tests/fixtures/eurostat_interest.json").read_text())
    payload["dimension"]["time"]["category"]["index"] = ["2021", "2021.5", "2022"]
    client = EurostatClient("https://example.invalid", HttpSection(), tmp_path)
    spec = EurostatSeriesSpec(
        dataset="gov_10a_main",
        filters={
            "freq": "A",
            "unit": "MIO_EUR",
            "sector": "S13",
            "na_item": "D41PAY",
            "geo": "PT",
        },
        value_name="interest_mio_eur",
    )

    def fake_request(dataset: str, params: list[tuple[str, str]]):
        return type(
            "Response",
            (),
            {
                "payload": payload,
                "content": json.dumps(payload).encode("utf-8"),
                "url": "https://example.invalid",
                "status_code": 200,
            },
        )()

    client._request = fake_request

    with pytest.raises(SourceError, match="non-annual time labels"):
        client.fetch_series("interest", spec, 2021, 2023)
