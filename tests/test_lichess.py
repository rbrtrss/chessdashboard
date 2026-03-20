import json
from unittest.mock import MagicMock, patch

import pytest
import requests
from dlt.extract.exceptions import ResourceExtractionError

from ingestion.sources.lichess import lichess_games


def _make_response(*lines: bytes) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.iter_lines.return_value = iter(lines)
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


@patch("ingestion.sources.lichess.requests.get")
def test_yields_games(mock_get):
    game1 = {"id": "abc", "rated": True}
    game2 = {"id": "def", "rated": False}
    mock_get.return_value = _make_response(
        json.dumps(game1).encode(), json.dumps(game2).encode()
    )

    results = list(lichess_games("testuser"))

    assert results == [game1, game2]


@patch("ingestion.sources.lichess.requests.get")
def test_max_games_passed_as_param(mock_get):
    mock_get.return_value = _make_response()

    list(lichess_games("testuser", max_games=5))

    _, kwargs = mock_get.call_args
    assert kwargs["params"]["max"] == 5


@patch("ingestion.sources.lichess.requests.get")
def test_no_max_by_default(mock_get):
    mock_get.return_value = _make_response()

    list(lichess_games("testuser"))

    _, kwargs = mock_get.call_args
    assert "max" not in kwargs["params"]


@patch("ingestion.sources.lichess.requests.get")
def test_skips_empty_lines(mock_get):
    game = {"id": "abc"}
    mock_get.return_value = _make_response(
        json.dumps(game).encode(), b"", json.dumps(game).encode()
    )

    results = list(lichess_games("testuser"))

    assert len(results) == 2


@patch("ingestion.sources.lichess.requests.get")
def test_raises_on_http_error(mock_get):
    mock_resp = _make_response()
    mock_resp.raise_for_status.side_effect = requests.HTTPError("404")
    mock_get.return_value = mock_resp

    with pytest.raises(ResourceExtractionError) as exc_info:
        list(lichess_games("testuser"))
    assert isinstance(exc_info.value.__cause__, requests.HTTPError)
