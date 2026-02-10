"""Tests for chessdashboard.cli module."""

import duckdb
from click.testing import CliRunner
from unittest.mock import patch

from chessdashboard.cli import main
from chessdashboard.database import init_db, insert_game


SAMPLE_GAME = dict(
    source="lichess",
    white="magnus",
    black="hikaru",
    year=2024,
    month=1,
    day=15,
    event="Blitz",
    result="1-0",
    eco="B90",
    time_control="300",
    url="https://lichess.org/abc123",
    moves="e4 c5 Nf3",
)

FAKE_LICHESS_GAME = {
    "white": "A",
    "black": "B",
    "result": "1-0",
    "year": 2024,
    "month": 1,
    "day": 1,
    "event": "blitz",
    "eco": "C50",
    "time_control": "300",
    "url": "https://lichess.org/x",
    "moves": "e4 e5",
}

FAKE_CHESSCOM_GAME = {
    "white": "X",
    "black": "Y",
    "result": "0-1",
    "year": 2024,
    "month": 2,
    "day": 10,
    "event": "rapid",
    "eco": "A00",
    "time_control": "600",
    "url": "https://chess.com/game/1",
    "moves": "d4 d5",
}


def _make_db():
    conn = duckdb.connect(":memory:")
    init_db(conn)
    return conn


def test_list_empty_db():
    conn = _make_db()
    with patch("chessdashboard.cli.get_connection", return_value=conn):
        result = CliRunner().invoke(main, ["list"])
    assert "No games stored" in result.output


def test_list_with_games():
    conn = _make_db()
    insert_game(conn, **SAMPLE_GAME)
    with patch("chessdashboard.cli.get_connection", return_value=conn):
        result = CliRunner().invoke(main, ["list"])
    assert "magnus" in result.output
    assert "hikaru" in result.output


def test_fetch_lichess():
    conn = _make_db()
    with (
        patch("chessdashboard.cli.get_connection", return_value=conn),
        patch("chessdashboard.cli.lichess_client.fetch_games", return_value=iter([FAKE_LICHESS_GAME])),
    ):
        result = CliRunner().invoke(main, ["fetch", "--platform", "lichess", "-u", "testuser"])
    assert "1 game(s) loaded" in result.output


def test_fetch_skips_duplicates():
    conn = _make_db()
    insert_game(conn, **SAMPLE_GAME)
    dup_game = {**SAMPLE_GAME}
    del dup_game["source"]
    with (
        patch("chessdashboard.cli.get_connection", return_value=conn),
        patch("chessdashboard.cli.lichess_client.fetch_games", return_value=iter([dup_game])),
    ):
        result = CliRunner().invoke(main, ["fetch", "--platform", "lichess", "-u", "magnus"])
    assert "0 game(s) loaded" in result.output
    assert "1 duplicate(s) skipped" in result.output


def test_fetch_chesscom():
    conn = _make_db()
    with (
        patch("chessdashboard.cli.get_connection", return_value=conn),
        patch("chessdashboard.cli.chesscom_client.fetch_games", return_value=iter([FAKE_CHESSCOM_GAME])),
    ):
        result = CliRunner().invoke(main, ["fetch", "--platform", "chesscom", "-u", "testuser"])
    assert "1 game(s) loaded" in result.output


def test_fetch_both_platforms_from_env():
    """No args + env vars set → fetches both platforms."""
    conn = _make_db()
    env = {"LICHESS_USERNAME": "envuser", "CHESSCOM_USERNAME": "envuser"}
    with (
        patch("chessdashboard.cli.get_connection", return_value=conn),
        patch("chessdashboard.cli.lichess_client.fetch_games", return_value=iter([FAKE_LICHESS_GAME])) as mock_lic,
        patch("chessdashboard.cli.chesscom_client.fetch_games", return_value=iter([FAKE_CHESSCOM_GAME])) as mock_cc,
        patch.dict("os.environ", env, clear=False),
    ):
        result = CliRunner().invoke(main, ["fetch"])
    assert result.exit_code == 0
    mock_lic.assert_called_once_with("envuser", max_games=None)
    mock_cc.assert_called_once_with("envuser")


def test_fetch_single_platform_from_env():
    """--platform lichess + env var → fetches lichess only using env username."""
    conn = _make_db()
    env = {"LICHESS_USERNAME": "envuser"}
    with (
        patch("chessdashboard.cli.get_connection", return_value=conn),
        patch("chessdashboard.cli.lichess_client.fetch_games", return_value=iter([FAKE_LICHESS_GAME])) as mock_lic,
        patch.dict("os.environ", env, clear=False),
    ):
        result = CliRunner().invoke(main, ["fetch", "--platform", "lichess"])
    assert result.exit_code == 0
    mock_lic.assert_called_once_with("envuser", max_games=None)


def test_fetch_username_without_platform_errors():
    """-u without --platform → error."""
    conn = _make_db()
    with patch("chessdashboard.cli.get_connection", return_value=conn):
        result = CliRunner().invoke(main, ["fetch", "-u", "someone"])
    assert result.exit_code != 0
    assert "--username requires --platform" in result.output


def test_fetch_missing_env_var_errors():
    """No args + missing env var → error."""
    conn = _make_db()
    env = {"LICHESS_USERNAME": "", "CHESSCOM_USERNAME": ""}
    with (
        patch("chessdashboard.cli.get_connection", return_value=conn),
        patch.dict("os.environ", env, clear=False),
    ):
        result = CliRunner().invoke(main, ["fetch"])
    assert result.exit_code != 0
    assert "not set in .env" in result.output
