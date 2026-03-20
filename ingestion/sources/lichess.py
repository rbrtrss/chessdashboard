import json
from typing import Iterator

import dlt
import requests


@dlt.resource(
    name="games",
    primary_key="id",
    write_disposition="merge",
)
def lichess_games(username: str, max_games: int | None = None) -> Iterator[dict]:
    """Stream games from the Lichess API as NDJSON."""
    url = f"https://lichess.org/api/games/user/{username}"
    params = {
        "pgnInJson": "true",
        "opening": "true",
        "clocks": "false",
        "evals": "false",
        "max": max_games,
    }
    # Remove None params
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"Accept": "application/x-ndjson"}

    with requests.get(url, params=params, headers=headers, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                yield json.loads(line)
