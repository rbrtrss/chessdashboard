from unittest.mock import MagicMock, patch

import pytest

# ── Sample raw game data ──────────────────────────────────────────────────────

RAW_LICHESS = {
    "id": "abc123",
    "createdAt": 1700000000000,
    "players": {
        "white": {"user": {"name": "alice"}, "rating": 1500},
        "black": {"user": {"name": "bob"}, "rating": 1600},
    },
    "winner": "white",
    "opening": {"eco": "B20"},
    "clock": {"initial": 300},
    "moves": "e4 c5",
}

RAW_CHESSCOM = {
    "url": "https://chess.com/game/1",
    "end_time": 1700000000,
    "time_control": "600",
    "white": {"username": "alice", "rating": 1200, "result": "win"},
    "black": {"username": "bob", "rating": 1300, "result": "checkmated"},
    "pgn": (
        '[Event "Live Chess"]\n[White "alice"]\n[Black "bob"]\n'
        '[Result "1-0"]\n[ECO "C50"]\n\n1. e4 e5 1-0\n'
    ),
}


# ── build_pipeline ────────────────────────────────────────────────────────────


@patch("ingestion.pipeline.MOTHERDUCK_TOKEN", "test_token")
@patch("ingestion.pipeline.DESTINATION", "motherduck")
def test_build_pipeline_motherduck():
    from ingestion.pipeline import build_pipeline

    pipeline = build_pipeline()
    assert pipeline.pipeline_name == "chessdashboard"
    assert pipeline.dataset_name == "raw"


@patch("ingestion.pipeline.MOTHERDUCK_TOKEN", "")
@patch("ingestion.pipeline.DESTINATION", "motherduck")
def test_build_pipeline_missing_token_raises():
    from ingestion.pipeline import build_pipeline

    with pytest.raises(ValueError, match="MOTHERDUCK_TOKEN"):
        build_pipeline()


@patch("ingestion.pipeline.DESTINATION", "duckdb")
def test_build_pipeline_duckdb():
    from ingestion.pipeline import build_pipeline

    pipeline = build_pipeline()
    assert pipeline.pipeline_name == "chessdashboard"


# ── normalized_lichess ────────────────────────────────────────────────────────


@patch("ingestion.pipeline.lichess_games")
def test_normalized_lichess_yields_games(mock_source):
    mock_source.return_value = iter([RAW_LICHESS])
    from ingestion.pipeline import normalized_lichess

    results = list(normalized_lichess("alice"))
    assert len(results) == 1
    assert results[0]["game_id"] == "lichess_abc123"
    assert results[0]["source"] == "lichess"


# ── normalized_chesscom ──────────────────────────────────────────────────────


@patch("ingestion.pipeline.chesscom_games")
def test_normalized_chesscom_yields_games(mock_source):
    mock_source.return_value = iter([RAW_CHESSCOM])
    from ingestion.pipeline import normalized_chesscom

    results = list(normalized_chesscom("alice"))
    assert len(results) == 1
    assert results[0]["game_id"].startswith("chesscom_")
    assert results[0]["source"] == "chesscom"


@patch("ingestion.pipeline.chesscom_games")
def test_normalized_chesscom_respects_max(mock_source):
    mock_source.return_value = iter([RAW_CHESSCOM] * 5)
    from ingestion.pipeline import normalized_chesscom

    results = list(normalized_chesscom("alice", max_games=2))
    assert len(results) == 2


# ── run ──────────────────────────────────────────────────────────────────────


@patch("ingestion.pipeline.LICHESS_USERNAME", "")
def test_run_missing_lichess_username_raises():
    from ingestion.pipeline import run

    with pytest.raises(ValueError, match="LICHESS_USERNAME"):
        run(platform="lichess")


@patch("ingestion.pipeline.CHESSCOM_USERNAME", "")
def test_run_missing_chesscom_username_raises():
    from ingestion.pipeline import run

    with pytest.raises(ValueError, match="CHESSCOM_USERNAME"):
        run(platform="chesscom")


@patch("ingestion.pipeline.build_pipeline")
@patch("ingestion.pipeline.LICHESS_USERNAME", "alice")
@patch("ingestion.pipeline.lichess_games")
def test_run_calls_pipeline(mock_source, mock_build):
    mock_source.return_value = iter([RAW_LICHESS])
    mock_pipeline = MagicMock()
    mock_build.return_value = mock_pipeline

    from ingestion.pipeline import run

    run(platform="lichess")
    mock_pipeline.run.assert_called_once()
