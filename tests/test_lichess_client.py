"""Tests for chessdashboard.lichess_client module."""

import json
from unittest.mock import MagicMock, patch

from chessdashboard.lichess_client import _parse_result, _epoch_to_date, _parse_game, fetch_games


def test_parse_result_white():
    assert _parse_result("white") == "1-0"


def test_parse_result_black():
    assert _parse_result("black") == "0-1"


def test_parse_result_draw():
    assert _parse_result(None) == "1/2-1/2"


def test_epoch_to_date_known():
    # 2024-01-01 00:00:00 UTC = 1704067200000 ms
    assert _epoch_to_date(1704067200000) == (2024, 1, 1)


def test_epoch_to_date_none():
    assert _epoch_to_date(None) == (None, None, None)


def test_parse_game():
    data = {
        "id": "abc123",
        "createdAt": 1704067200000,
        "players": {
            "white": {"user": {"name": "Magnus"}},
            "black": {"user": {"name": "Hikaru"}},
        },
        "winner": "white",
        "perf": "blitz",
        "opening": {"eco": "B90"},
        "clock": {"initial": 300},
        "moves": "e4 c5 Nf3",
    }
    result = _parse_game(data)
    assert result["white"] == "Magnus"
    assert result["black"] == "Hikaru"
    assert result["result"] == "1-0"
    assert result["year"] == 2024
    assert result["eco"] == "B90"
    assert result["url"] == "https://lichess.org/abc123"
    assert result["moves"] == "e4 c5 Nf3"


def test_fetch_games_yields_parsed():
    ndjson_line = json.dumps({
        "id": "xyz",
        "createdAt": 1704067200000,
        "players": {
            "white": {"user": {"name": "A"}},
            "black": {"user": {"name": "B"}},
        },
        "winner": "black",
        "perf": "rapid",
        "opening": {"eco": "C50"},
        "clock": {"initial": 600},
        "moves": "e4 e5",
    })

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.iter_lines.return_value = [ndjson_line]
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("chessdashboard.lichess_client.httpx.stream", return_value=mock_response):
        games = list(fetch_games("testuser"))

    assert len(games) == 1
    assert games[0]["white"] == "A"
    assert games[0]["result"] == "0-1"
