"""Lichess API client — streams games as NDJSON."""

import json
from collections.abc import Iterator
from datetime import datetime, timezone

import chess.pgn
import httpx

LICHESS_API_BASE = "https://lichess.org/api"
USER_AGENT = "chessdashboard/0.1.0 (https://github.com/chessdashboard)"


def _parse_result(winner: str | None) -> str:
    """Convert Lichess winner field to PGN result."""
    if winner == "white":
        return "1-0"
    elif winner == "black":
        return "0-1"
    else:
        return "1/2-1/2"


def _epoch_to_date(epoch_ms: int | None) -> tuple[int | None, int | None, int | None]:
    """Convert epoch milliseconds to (year, month, day)."""
    if not epoch_ms:
        return (None, None, None)
    dt = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
    return (dt.year, dt.month, dt.day)


def _parse_game(data: dict) -> dict:
    """Parse a single Lichess game JSON object into our standard format."""
    players = data.get("players", {})
    white_user = players.get("white", {}).get("user", {})
    black_user = players.get("black", {}).get("user", {})

    year, month, day = _epoch_to_date(data.get("createdAt"))

    _raw = data.get("opening", {}).get("name")
    _name, _variation = _raw.split(": ", 1) if _raw and ": " in _raw else (_raw, None)

    return {
        "white": white_user.get("name", "Anonymous"),
        "black": black_user.get("name", "Anonymous"),
        "result": _parse_result(data.get("winner")),
        "year": year,
        "month": month,
        "day": day,
        "event": data.get("perf", "unknown"),
        "eco": data.get("opening", {}).get("eco"),
        "opening_name": _name,
        "opening_variation": _variation,
        "time_control": data.get("clock", {}).get("initial", ""),
        "url": f"https://lichess.org/{data['id']}",
        "moves": data.get("moves", ""),
    }


def fetch_games(username: str, max_games: int | None = None) -> Iterator[dict]:
    """Fetch games for a Lichess user via streaming NDJSON.

    Yields dicts with keys: white, black, result, year, month, day,
    event, eco, time_control, url, moves.
    """
    url = f"{LICHESS_API_BASE}/games/user/{username}"
    params = {"opening": "true"}
    if max_games:
        params["max"] = str(max_games)

    headers = {
        "Accept": "application/x-ndjson",
        "User-Agent": USER_AGENT,
    }

    with httpx.stream("GET", url, headers=headers, params=params, timeout=60.0) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line.strip():
                continue
            data = json.loads(line)
            yield _parse_game(data)
