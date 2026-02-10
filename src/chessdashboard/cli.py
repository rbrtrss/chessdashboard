"""Command-line interface for chessdashboard."""

import click
from pathlib import Path

from .database import get_connection, init_db, insert_game, list_games, game_exists
from . import lichess_client, chesscom_client


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
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db


@main.command()
@click.argument("username")
@click.option(
    "--platform",
    type=click.Choice(["lichess", "chesscom"]),
    required=True,
    help="Platform to fetch games from.",
)
@click.option("--max", "max_games", type=int, default=None, help="Max games to fetch.")
@click.pass_context
def fetch(ctx: click.Context, username: str, platform: str, max_games: int | None) -> None:
    """Fetch games for USERNAME from a chess platform."""
    conn = get_connection(ctx.obj["db_path"])
    init_db(conn)

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

    conn.close()
    click.echo(f"Done: {loaded} game(s) loaded, {skipped} duplicate(s) skipped.")


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
        click.echo("No games stored. Use 'chessdashboard fetch <username> --platform <platform>' to fetch games.")
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
