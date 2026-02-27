"""Chess.com API client — fetches games via monthly archives."""

import io
from collections.abc import Iterator

import chess.pgn
import httpx

CHESSCOM_API_BASE = "https://api.chess.com/pub"
USER_AGENT = "chessdashboard/0.1.0 (https://github.com/chessdashboard)"


def _parse_pgn_game(pgn_text: str, username: str) -> dict | None:
    """Parse a PGN string from Chess.com into our standard format."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return None

    headers = game.headers

    # Extract date components
    date_str = headers.get("UTCDate", headers.get("Date", ""))
    year, month, day = None, None, None
    if date_str and date_str != "????.??.??":
        parts = date_str.split(".")
        if len(parts) == 3:
            try:
                year = int(parts[0]) if parts[0] != "????" else None
                month = int(parts[1]) if parts[1] != "??" else None
                day = int(parts[2]) if parts[2] != "??" else None
            except ValueError:
                pass

    # Collect SAN moves
    moves = []
    node = game
    while node.variations:
        node = node.variation(0)
        moves.append(node.san())

    white = headers.get("White", "Unknown")
    black = headers.get("Black", "Unknown")

    return {
        "white": white,
        "black": black,
        "result": headers.get("Result", "*"),
        "year": year,
        "month": month,
        "day": day,
        "event": headers.get("Event"),
        "eco": headers.get("ECO"),
        "opening_name": headers.get("Opening"),
        "opening_variation": headers.get("Variation"),
        "time_control": headers.get("TimeControl"),
        "url": headers.get("Link"),
        "moves": " ".join(moves),
    }


def _get_archives(username: str) -> list[str]:
    """Get list of monthly archive URLs for a Chess.com user."""
    url = f"{CHESSCOM_API_BASE}/player/{username}/games/archives"
    headers = {"User-Agent": USER_AGENT}
    response = httpx.get(url, headers=headers, timeout=30.0)
    response.raise_for_status()
    return response.json().get("archives", [])


def fetch_games(
    username: str,
    year: int | None = None,
    month: int | None = None,
) -> Iterator[dict]:
    """Fetch games for a Chess.com user from monthly archives.

    Optionally filter by year and/or month.
    Yields dicts with keys: white, black, result, year, month, day,
    event, eco, time_control, url, moves.
    """
    archives = _get_archives(username)
    headers = {"User-Agent": USER_AGENT}

    for archive_url in archives:
        # Archive URLs end with /YYYY/MM — filter if requested
        parts = archive_url.rstrip("/").split("/")
        archive_year = int(parts[-2])
        archive_month = int(parts[-1])
        if year and archive_year != year:
            continue
        if month and archive_month != month:
            continue

        response = httpx.get(archive_url, headers=headers, timeout=60.0)
        response.raise_for_status()
        games = response.json().get("games", [])

        for game_data in games:
            pgn_text = game_data.get("pgn")
            if not pgn_text:
                continue
            parsed = _parse_pgn_game(pgn_text, username)
            if parsed:
                yield parsed
