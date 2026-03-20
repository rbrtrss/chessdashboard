from typing import Iterator

import dlt
import requests


_HEADERS = {"User-Agent": "chessdashboard/0.1 (github.com/rbrtrss/chessdashboard)"}


@dlt.resource(
    name="games",
    primary_key="uuid",
    write_disposition="merge",
)
def chesscom_games(username: str, max_games: int | None = None) -> Iterator[dict]:
    """Stream games from the Chess.com API, newest months first."""
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
    resp = requests.get(archives_url, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    archives = resp.json().get("archives", [])

    count = 0
    for archive_url in reversed(archives):  # newest first
        if max_games is not None and count >= max_games:
            break
        r = requests.get(archive_url, headers=_HEADERS, timeout=30)
        r.raise_for_status()
        for game in r.json().get("games", []):
            if max_games is not None and count >= max_games:
                break
            yield game
            count += 1
