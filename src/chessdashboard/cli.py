"""Command-line interface for chessdashboard."""

import os

import click
from dotenv import load_dotenv
from pathlib import Path

from .database import get_connection, init_db, insert_game, list_games, game_exists
from . import lichess_client, chesscom_client


_ENV_KEYS = {
    "lichess": "LICHESS_USERNAME",
    "chesscom": "CHESSCOM_USERNAME",
}


def _resolve_username(username: str | None, platform: str) -> str:
    """Return explicit username or fall back to the matching env var."""
    if username:
        return username
    env_key = _ENV_KEYS[platform]
    val = os.environ.get(env_key)
    if not val:
        raise click.UsageError(f"{env_key} not set in .env")
    return val


def _fetch_platform(
    conn, platform: str, username: str, max_games: int | None
) -> None:
    """Fetch and store games for one platform."""
    click.echo(f"Fetching games for {username} from {platform}...")

    if platform == "lichess":
        games_iter = lichess_client.fetch_games(username, max_games=max_games)
    else:
        games_iter = chesscom_client.fetch_games(username)

    loaded = 0
    skipped = 0
    for game in games_iter:
        url = game.get("url")
        if url and game_exists(conn, platform, url):
            skipped += 1
            continue

        insert_game(
            conn,
            source=platform,
            white=game["white"],
            black=game["black"],
            year=game["year"],
            month=game["month"],
            day=game["day"],
            event=game.get("event"),
            result=game["result"],
            eco=game.get("eco"),
            time_control=game.get("time_control"),
            url=url,
            moves=game.get("moves", ""),
        )
        loaded += 1
        if max_games and loaded >= max_games:
            break

    click.echo(f"Done: {loaded} game(s) loaded, {skipped} duplicate(s) skipped.")


@click.group()
@click.option(
    "--db",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to the database file (default: ~/.chessdashboard/games.duckdb)",
)
@click.pass_context
def main(ctx: click.Context, db: Path | None) -> None:
    """chessdashboard - Fetch and analyze chess games from Lichess and Chess.com."""
    load_dotenv()
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db


@main.command()
@click.option("-u", "--username", default=None, help="Username (defaults to .env value).")
@click.option(
    "--platform",
    type=click.Choice(["lichess", "chesscom"]),
    default=None,
    help="Platform to fetch games from (omit to fetch both).",
)
@click.option("--max", "max_games", type=int, default=None, help="Max games to fetch.")
@click.pass_context
def fetch(ctx: click.Context, username: str | None, platform: str | None, max_games: int | None) -> None:
    """Fetch games from chess platforms. Defaults to both platforms using .env usernames."""
    conn = get_connection(ctx.obj["db_path"])
    init_db(conn)

    if platform:
        targets = [(platform, _resolve_username(username, platform))]
    else:
        if username:
            raise click.UsageError("--username requires --platform")
        targets = [
            ("lichess", _resolve_username(None, "lichess")),
            ("chesscom", _resolve_username(None, "chesscom")),
        ]

    for plat, user in targets:
        _fetch_platform(conn, plat, user, max_games)

    conn.close()


@main.command(name="list")
@click.option(
    "--platform",
    type=click.Choice(["lichess", "chesscom"]),
    default=None,
    help="Filter by platform.",
)
@click.pass_context
def list_cmd(ctx: click.Context, platform: str | None) -> None:
    """List all stored games."""
    conn = get_connection(ctx.obj["db_path"])
    init_db(conn)

    games = list_games(conn, platform)
    conn.close()

    if not games:
        click.echo("No games stored. Use 'chessdashboard fetch' to fetch games.")
        return

    click.echo(f"{'ID':<6} {'White':<20} {'Black':<20} {'Date':<12} {'Result':<10} {'ECO':<6} {'TC':<10} {'Source'}")
    click.echo("-" * 100)
    for game_id, white, black, year, month, day, result, eco, tc, source in games:
        date_str = f"{year or '?'}-{month or '?':>02}-{day or '?':>02}" if year else "-"
        white_disp = (white[:17] + "...") if len(white) > 20 else white
        black_disp = (black[:17] + "...") if len(black) > 20 else black
        click.echo(
            f"{game_id:<6} {white_disp:<20} {black_disp:<20} {date_str:<12} "
            f"{result or '-':<10} {eco or '-':<6} {tc or '-':<10} {source}"
        )


if __name__ == "__main__":
    main()
