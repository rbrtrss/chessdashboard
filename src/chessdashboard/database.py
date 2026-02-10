"""Database operations for chessdashboard using DuckDB."""

import duckdb
from pathlib import Path

from chessdashboard.schema import ALL_DDL

DEFAULT_DB_PATH = Path.home() / ".chessdashboard" / "games.duckdb"


def get_connection(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    """Get a connection to the DuckDB database."""
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def init_db(conn: duckdb.DuckDBPyConnection) -> None:
    """Initialize the database schema and seed dimension tables."""
    for ddl in ALL_DDL:
        conn.execute(ddl)
    # Seed dim_source with known platforms
    for source in ("lichess", "chesscom"):
        _get_or_create_source(conn, source)


def _get_or_create_player(conn: duckdb.DuckDBPyConnection, username: str) -> int:
    """Get or create a player and return their ID."""
    row = conn.execute(
        "SELECT player_id FROM dim_player WHERE username = ?", [username]
    ).fetchone()
    if row:
        return row[0]

    result = conn.execute(
        """
        INSERT INTO dim_player (player_id, username, display_name)
        VALUES ((SELECT COALESCE(MAX(player_id), 0) + 1 FROM dim_player), ?, ?)
        RETURNING player_id
        """,
        [username, username],
    ).fetchone()
    return result[0]


def _get_or_create_date(
    conn: duckdb.DuckDBPyConnection,
    year: int | None,
    month: int | None = None,
    day: int | None = None,
) -> int:
    """Get or create a date entry and return its ID."""
    date_str = None
    if year and month and day:
        date_str = f"{year:04d}-{month:02d}-{day:02d}"

    row = conn.execute(
        """SELECT date_id FROM dim_date
        WHERE year IS NOT DISTINCT FROM ?
        AND month IS NOT DISTINCT FROM ?
        AND day IS NOT DISTINCT FROM ?""",
        [year, month, day],
    ).fetchone()
    if row:
        return row[0]

    result = conn.execute(
        """
        INSERT INTO dim_date (date_id, date, year, month, day)
        VALUES ((SELECT COALESCE(MAX(date_id), 0) + 1 FROM dim_date), ?, ?, ?, ?)
        RETURNING date_id
        """,
        [date_str, year, month, day],
    ).fetchone()
    return result[0]


def _get_or_create_event(
    conn: duckdb.DuckDBPyConnection,
    name: str | None,
    site: str | None = None,
    round_: str | None = None,
) -> int:
    """Get or create an event and return its ID."""
    row = conn.execute(
        """SELECT event_id FROM dim_event
        WHERE name IS NOT DISTINCT FROM ?
        AND site IS NOT DISTINCT FROM ?
        AND round IS NOT DISTINCT FROM ?""",
        [name, site, round_],
    ).fetchone()
    if row:
        return row[0]

    result = conn.execute(
        """
        INSERT INTO dim_event (event_id, name, site, round)
        VALUES ((SELECT COALESCE(MAX(event_id), 0) + 1 FROM dim_event), ?, ?, ?)
        RETURNING event_id
        """,
        [name, site, round_],
    ).fetchone()
    return result[0]


def _get_or_create_result(conn: duckdb.DuckDBPyConnection, result_str: str | None) -> int:
    """Get or create a result and return its ID."""
    value = result_str or "*"
    row = conn.execute(
        "SELECT result_id FROM dim_result WHERE result = ?", [value]
    ).fetchone()
    if row:
        return row[0]

    result = conn.execute(
        """
        INSERT INTO dim_result (result_id, result)
        VALUES ((SELECT COALESCE(MAX(result_id), 0) + 1 FROM dim_result), ?)
        RETURNING result_id
        """,
        [value],
    ).fetchone()
    return result[0]


def _get_or_create_source(conn: duckdb.DuckDBPyConnection, source: str) -> int:
    """Get or create a source and return its ID."""
    row = conn.execute(
        "SELECT source_id FROM dim_source WHERE source = ?", [source]
    ).fetchone()
    if row:
        return row[0]

    result = conn.execute(
        """
        INSERT INTO dim_source (source_id, source)
        VALUES ((SELECT COALESCE(MAX(source_id), 0) + 1 FROM dim_source), ?)
        RETURNING source_id
        """,
        [source],
    ).fetchone()
    return result[0]


def insert_game(
    conn: duckdb.DuckDBPyConnection,
    source: str,
    white: str,
    black: str,
    year: int | None,
    month: int | None,
    day: int | None,
    event: str | None,
    result: str | None,
    eco: str | None,
    time_control: str | None,
    url: str | None,
    moves: str,
) -> int:
    """Insert a game into the database and return its ID."""
    source_id = _get_or_create_source(conn, source)
    white_id = _get_or_create_player(conn, white)
    black_id = _get_or_create_player(conn, black)
    date_id = _get_or_create_date(conn, year, month, day)
    event_id = _get_or_create_event(conn, event)
    result_id = _get_or_create_result(conn, result)

    result_row = conn.execute(
        """
        INSERT INTO fact_games (game_id, date_id, event_id, source_id,
                                playing_white_id, playing_black_id, result_id,
                                eco, time_control, url, moves)
        VALUES ((SELECT COALESCE(MAX(game_id), 0) + 1 FROM fact_games),
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING game_id
        """,
        [date_id, event_id, source_id, white_id, black_id, result_id,
         eco, time_control, url, moves],
    ).fetchone()
    return result_row[0]


def game_exists(conn: duckdb.DuckDBPyConnection, source: str, url: str) -> bool:
    """Check if a game already exists by source platform and URL."""
    row = conn.execute(
        """
        SELECT 1 FROM fact_games g
        JOIN dim_source s ON g.source_id = s.source_id
        WHERE s.source = ? AND g.url = ?
        LIMIT 1
        """,
        [source, url],
    ).fetchone()
    return row is not None


def list_games(conn: duckdb.DuckDBPyConnection, platform: str | None = None) -> list[tuple]:
    """List all games in the database, optionally filtered by platform."""
    query = """
        SELECT
            g.game_id,
            pw.username AS white,
            pb.username AS black,
            d.year,
            d.month,
            d.day,
            r.result,
            g.eco,
            g.time_control,
            s.source
        FROM fact_games g
        JOIN dim_player pw ON g.playing_white_id = pw.player_id
        JOIN dim_player pb ON g.playing_black_id = pb.player_id
        JOIN dim_date d ON g.date_id = d.date_id
        JOIN dim_result r ON g.result_id = r.result_id
        JOIN dim_source s ON g.source_id = s.source_id
    """
    params = []
    if platform:
        query += " WHERE s.source = ?"
        params.append(platform)
    query += " ORDER BY g.game_id ASC"

    return conn.execute(query, params).fetchall()
