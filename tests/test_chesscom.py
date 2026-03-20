from unittest.mock import MagicMock, patch

import pytest
import requests
from dlt.extract.exceptions import ResourceExtractionError

from ingestion.sources.chesscom import chesscom_games


def _make_response(json_data: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.json.return_value = json_data
    return mock_resp


def _side_effect(archives_data: dict, archive_responses: dict):
    """Return a side_effect function that dispatches by URL."""
    def _get(url, **kwargs):
        if url.endswith("/archives"):
            return _make_response(archives_data)
        return _make_response(archive_responses[url])
    return _get


@patch("ingestion.sources.chesscom.requests.get")
def test_yields_games_from_archives(mock_get):
    archives = {"archives": ["url/2024/01", "url/2024/02"]}
    responses = {
        "url/2024/01": {"games": [{"uuid": "a"}, {"uuid": "b"}]},
        "url/2024/02": {"games": [{"uuid": "c"}, {"uuid": "d"}]},
    }
    mock_get.side_effect = _side_effect(archives, responses)

    results = list(chesscom_games("testuser"))

    assert len(results) == 4
    assert {g["uuid"] for g in results} == {"a", "b", "c", "d"}


@patch("ingestion.sources.chesscom.requests.get")
def test_newest_first(mock_get):
    archives = {"archives": ["url/2024/01", "url/2024/02"]}
    responses = {
        "url/2024/01": {"games": [{"uuid": "old"}]},
        "url/2024/02": {"games": [{"uuid": "new"}]},
    }
    mock_get.side_effect = _side_effect(archives, responses)

    results = list(chesscom_games("testuser"))

    assert results[0]["uuid"] == "new"
    assert results[1]["uuid"] == "old"


@patch("ingestion.sources.chesscom.requests.get")
def test_max_games_respected(mock_get):
    archives = {"archives": ["url/2024/01", "url/2024/02"]}
    responses = {
        "url/2024/01": {"games": [{"uuid": "a"}, {"uuid": "b"}, {"uuid": "c"}]},
        "url/2024/02": {"games": [{"uuid": "d"}, {"uuid": "e"}, {"uuid": "f"}]},
    }
    mock_get.side_effect = _side_effect(archives, responses)

    results = list(chesscom_games("testuser", max_games=2))

    assert len(results) == 2


@patch("ingestion.sources.chesscom.requests.get")
def test_empty_archives(mock_get):
    mock_get.return_value = _make_response({"archives": []})

    results = list(chesscom_games("testuser"))

    assert results == []
    assert mock_get.call_count == 1


@patch("ingestion.sources.chesscom.requests.get")
def test_raises_on_archives_http_error(mock_get):
    mock_resp = _make_response({})
    mock_resp.raise_for_status.side_effect = requests.HTTPError("403")
    mock_get.return_value = mock_resp

    with pytest.raises(ResourceExtractionError) as exc_info:
        list(chesscom_games("testuser"))
    assert isinstance(exc_info.value.__cause__, requests.HTTPError)
