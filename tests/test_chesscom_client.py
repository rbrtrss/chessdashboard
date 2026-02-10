"""Tests for chessdashboard.chesscom_client module."""

from unittest.mock import MagicMock, patch

from chessdashboard.chesscom_client import _parse_pgn_game, _get_archives, fetch_games


SAMPLE_PGN = """[Event "Live Chess"]
[Site "Chess.com"]
[Date "2024.01.15"]
[White "magnus"]
[Black "hikaru"]
[Result "1-0"]
[UTCDate "2024.01.15"]
[ECO "B90"]
[TimeControl "300"]
[Link "https://www.chess.com/game/live/1"]

1. e4 c5 2. Nf3 d6 1-0"""


def test_parse_pgn_game_valid():
    result = _parse_pgn_game(SAMPLE_PGN, "magnus")
    assert result is not None
    assert result["white"] == "magnus"
    assert result["black"] == "hikaru"
    assert result["result"] == "1-0"
    assert result["year"] == 2024
    assert result["month"] == 1
    assert result["day"] == 15
    assert result["eco"] == "B90"
    assert result["moves"] == "e4 c5 Nf3 d6"


def test_parse_pgn_game_none_on_empty():
    assert _parse_pgn_game("", "user") is None


def test_get_archives():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "archives": [
            "https://api.chess.com/pub/player/magnus/games/2024/01",
            "https://api.chess.com/pub/player/magnus/games/2024/02",
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("chessdashboard.chesscom_client.httpx.get", return_value=mock_response):
        urls = _get_archives("magnus")

    assert len(urls) == 2
    assert "2024/01" in urls[0]


def test_fetch_games_filters_by_year_month():
    archives_response = MagicMock()
    archives_response.json.return_value = {
        "archives": [
            "https://api.chess.com/pub/player/u/games/2024/01",
            "https://api.chess.com/pub/player/u/games/2024/02",
        ]
    }
    archives_response.raise_for_status = MagicMock()

    games_response = MagicMock()
    games_response.json.return_value = {"games": [{"pgn": SAMPLE_PGN}]}
    games_response.raise_for_status = MagicMock()

    def mock_get(url, **kwargs):
        if "archives" in url:
            return archives_response
        return games_response

    with patch("chessdashboard.chesscom_client.httpx.get", side_effect=mock_get):
        games = list(fetch_games("u", year=2024, month=1))

    assert len(games) == 1
    assert games[0]["white"] == "magnus"
