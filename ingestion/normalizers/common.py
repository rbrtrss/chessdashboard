"""
Transformer functions that map Lichess and Chess.com raw records to the
common raw.games schema.

Common schema columns:
    game_id, source, played_at, white_username, black_username,
    white_rating, black_rating, result, eco, time_control, moves
"""

from __future__ import annotations

import chess.pgn
import io
from typing import Iterator


def _parse_result(raw: str) -> str:
    """Normalize result string to 'white', 'black', or 'draw'."""
    if raw == "1-0":
        return "white"
    if raw == "0-1":
        return "black"
    return "draw"


def normalize_lichess(game: dict) -> dict:
    """Map a Lichess NDJSON game record to the common schema."""
    players = game.get("players", {})
    white = players.get("white", {})
    black = players.get("black", {})

    opening = game.get("opening", {}) or {}

    return {
        "game_id": f"lichess_{game['id']}",
        "source": "lichess",
        "played_at": game.get("createdAt"),  # epoch ms — dlt will cast
        "white_username": white.get("user", {}).get("name", ""),
        "black_username": black.get("user", {}).get("name", ""),
        "white_rating": white.get("rating"),
        "black_rating": black.get("rating"),
        "result": _parse_result(game.get("winner", "draw") if "winner" in game else game.get("status", "draw")),
        "eco": opening.get("eco", ""),
        "time_control": str(game["clock"]["initial"]) if game.get("clock") else game.get("speed", ""),
        "moves": game.get("moves", ""),
    }


def normalize_chesscom(game: dict) -> dict:
    """Map a Chess.com players_games record to the common schema."""
    pgn_text = game.get("pgn", "")
    headers: dict = {}

    if pgn_text:
        pgn_game = chess.pgn.read_game(io.StringIO(pgn_text))
        if pgn_game:
            headers = dict(pgn_game.headers)
            moves = pgn_game.board().variation_san(pgn_game.mainline_moves()) if pgn_game else ""
        else:
            moves = ""
    else:
        moves = ""

    white_username = game.get("white", {}).get("username", headers.get("White", ""))
    black_username = game.get("black", {}).get("username", headers.get("Black", ""))

    raw_result = game.get("white", {}).get("result", headers.get("Result", "*"))
    if raw_result == "win":
        result = "white"
    elif game.get("black", {}).get("result") == "win":
        result = "black"
    else:
        result = _parse_result(headers.get("Result", "*"))

    return {
        "game_id": f"chesscom_{game.get('url', game.get('uuid', ''))}",
        "source": "chesscom",
        "played_at": game.get("end_time"),  # epoch seconds
        "white_username": white_username,
        "black_username": black_username,
        "white_rating": game.get("white", {}).get("rating"),
        "black_rating": game.get("black", {}).get("rating"),
        "result": result,
        "eco": headers.get("ECO", ""),
        "time_control": game.get("time_control", headers.get("TimeControl", "")),
        "moves": moves,
    }
