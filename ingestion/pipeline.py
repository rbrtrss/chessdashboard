"""
Chess dashboard ingestion pipeline.

Usage:
    uv run python -m ingestion.pipeline [--platform lichess|chesscom|both] [--max N]
"""

from __future__ import annotations

import argparse
import os
from typing import Iterator

import dlt

from ingestion.config import (
    CHESSCOM_USERNAME,
    DESTINATION,
    LICHESS_USERNAME,
    MOTHERDUCK_TOKEN,
)
from ingestion.normalizers.common import normalize_chesscom, normalize_lichess
from ingestion.sources.chesscom import chesscom_games
from ingestion.sources.lichess import lichess_games


@dlt.resource(
    name="games",
    primary_key="game_id",
    write_disposition="merge",
)
def normalized_lichess(username: str, max_games: int | None = None) -> Iterator[dict]:
    for game in lichess_games(username, max_games):
        yield normalize_lichess(game)


@dlt.resource(
    name="games",
    primary_key="game_id",
    write_disposition="merge",
)
def normalized_chesscom(username: str, max_games: int | None = None) -> Iterator[dict]:
    source = chesscom_games(username, max_games)
    count = 0
    for game in source:
        if max_games is not None and count >= max_games:
            break
        yield normalize_chesscom(game)
        count += 1


def build_pipeline() -> dlt.Pipeline:
    if DESTINATION == "motherduck":
        if not MOTHERDUCK_TOKEN:
            raise ValueError("MOTHERDUCK_TOKEN must be set when DESTINATION=motherduck")
        destination = dlt.destinations.motherduck(
            f"md:chessdashboard?motherduck_token={MOTHERDUCK_TOKEN}"
        )
    else:
        destination = DESTINATION  # type: ignore[assignment]

    return dlt.pipeline(
        pipeline_name="chessdashboard",
        destination=destination,
        dataset_name="raw",
    )


def run(platform: str = "both", max_games: int | None = None) -> None:
    pipeline = build_pipeline()
    resources = []

    if platform in ("lichess", "both"):
        if not LICHESS_USERNAME:
            raise ValueError("LICHESS_USERNAME must be set")
        resources.append(normalized_lichess(LICHESS_USERNAME, max_games))

    if platform in ("chesscom", "both"):
        if not CHESSCOM_USERNAME:
            raise ValueError("CHESSCOM_USERNAME must be set")
        resources.append(normalized_chesscom(CHESSCOM_USERNAME, max_games))

    load_info = pipeline.run(resources)
    print(load_info)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest chess games into DuckDB/MotherDuck")
    parser.add_argument(
        "--platform",
        choices=["lichess", "chesscom", "both"],
        default="both",
        help="Which platform to ingest from (default: both)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        dest="max_games",
        help="Maximum number of games to fetch per platform",
    )
    args = parser.parse_args()
    run(platform=args.platform, max_games=args.max_games)


if __name__ == "__main__":
    main()
