from ingestion.normalizers.common import _parse_result, normalize_chesscom, normalize_lichess


# ── _parse_result ─────────────────────────────────────────────────────────────


def test_parse_result_white():
    assert _parse_result("1-0") == "white"


def test_parse_result_black():
    assert _parse_result("0-1") == "black"


def test_parse_result_draw():
    assert _parse_result("1/2-1/2") == "draw"


def test_parse_result_unknown():
    assert _parse_result("*") == "draw"


# ── normalize_lichess ─────────────────────────────────────────────────────────

LICHESS_FULL = {
    "id": "abc123",
    "createdAt": 1700000000000,
    "players": {
        "white": {"user": {"name": "alice"}, "rating": 1500},
        "black": {"user": {"name": "bob"}, "rating": 1600},
    },
    "winner": "white",
    "opening": {"eco": "B20"},
    "clock": {"initial": 300},
    "moves": "e4 c5 Nf3",
}


def test_normalize_lichess_full():
    result = normalize_lichess(LICHESS_FULL)
    assert result["game_id"] == "lichess_abc123"
    assert result["source"] == "lichess"
    assert result["played_at"] == 1700000000000
    assert result["white_username"] == "alice"
    assert result["black_username"] == "bob"
    assert result["white_rating"] == 1500
    assert result["black_rating"] == 1600
    assert result["result"] == "white"
    assert result["eco"] == "B20"
    assert result["time_control"] == "300"
    assert result["moves"] == "e4 c5 Nf3"


def test_normalize_lichess_draw_no_winner():
    game = {
        "id": "draw1",
        "createdAt": 1700000000000,
        "players": {
            "white": {"user": {"name": "a"}, "rating": 1500},
            "black": {"user": {"name": "b"}, "rating": 1500},
        },
        "moves": "",
    }
    result = normalize_lichess(game)
    assert result["result"] == "draw"
    assert result["eco"] == ""
    assert result["time_control"] == ""


def test_normalize_lichess_speed_fallback():
    game = {
        "id": "speed1",
        "createdAt": 1700000000000,
        "players": {
            "white": {"user": {"name": "a"}, "rating": 1500},
            "black": {"user": {"name": "b"}, "rating": 1500},
        },
        "winner": "black",
        "speed": "blitz",
        "moves": "d4 d5",
    }
    result = normalize_lichess(game)
    assert result["time_control"] == "blitz"


# ── normalize_chesscom ────────────────────────────────────────────────────────

CHESSCOM_PGN = (
    '[Event "Live Chess"]\n'
    '[White "alice"]\n'
    '[Black "bob"]\n'
    '[Result "1-0"]\n'
    '[ECO "C50"]\n'
    '[TimeControl "600+5"]\n'
    "\n"
    "1. e4 e5 2. Nf3 Nc6 3. Bc4 1-0\n"
)

CHESSCOM_FULL = {
    "url": "https://chess.com/game/123",
    "end_time": 1700000000,
    "time_control": "600+5",
    "white": {"username": "alice", "rating": 1200, "result": "win"},
    "black": {"username": "bob", "rating": 1300, "result": "checkmated"},
    "pgn": CHESSCOM_PGN,
}


def test_normalize_chesscom_full():
    result = normalize_chesscom(CHESSCOM_FULL)
    assert result["game_id"] == "chesscom_https://chess.com/game/123"
    assert result["source"] == "chesscom"
    assert result["played_at"] == 1700000000
    assert result["white_username"] == "alice"
    assert result["black_username"] == "bob"
    assert result["white_rating"] == 1200
    assert result["black_rating"] == 1300
    assert result["result"] == "white"
    assert result["eco"] == "C50"
    assert result["time_control"] == "600+5"
    assert "Nf3" in result["moves"]


def test_normalize_chesscom_black_wins():
    game = {
        **CHESSCOM_FULL,
        "white": {"username": "alice", "rating": 1200, "result": "checkmated"},
        "black": {"username": "bob", "rating": 1300, "result": "win"},
    }
    result = normalize_chesscom(game)
    assert result["result"] == "black"


def test_normalize_chesscom_draw_via_pgn():
    pgn = (
        '[Event "Live Chess"]\n'
        '[White "alice"]\n'
        '[Black "bob"]\n'
        '[Result "1/2-1/2"]\n'
        "\n"
        "1. e4 e5 1/2-1/2\n"
    )
    game = {
        "url": "draw1",
        "end_time": 1700000000,
        "time_control": "300",
        "white": {"username": "alice", "rating": 1200, "result": "stalemate"},
        "black": {"username": "bob", "rating": 1300, "result": "stalemate"},
        "pgn": pgn,
    }
    result = normalize_chesscom(game)
    assert result["result"] == "draw"


def test_normalize_chesscom_missing_pgn():
    game = {
        "url": "nopgn1",
        "end_time": 1700000000,
        "time_control": "300",
        "white": {"username": "alice", "rating": 1200, "result": "win"},
        "black": {"username": "bob", "rating": 1300, "result": "checkmated"},
        "pgn": "",
    }
    result = normalize_chesscom(game)
    assert result["moves"] == ""
    assert result["result"] == "white"


def test_normalize_chesscom_username_fallback_to_pgn():
    game = {
        "url": "fallback1",
        "end_time": 1700000000,
        "time_control": "300",
        "white": {"rating": 1200, "result": "win"},
        "black": {"rating": 1300, "result": "checkmated"},
        "pgn": CHESSCOM_PGN,
    }
    result = normalize_chesscom(game)
    assert result["white_username"] == "alice"
    assert result["black_username"] == "bob"
