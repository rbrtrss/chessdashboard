"""Database operations for chessdashboard using DuckDB."""

from abc import ABC, abstractmethod

import duckdb
from pathlib import Path

from chessdashboard.schema import ALL_DDL

DEFAULT_DB_PATH = Path.home() / ".chessdashboard" / "games.duckdb"


class AbstractDatabase(ABC):
    @abstractmethod
    def insert_game(
        self,
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
        opening_name: str | None = None,
        opening_variation: str | None = None,
    ) -> int: ...

    @abstractmethod
    def game_exists(self, source: str, url: str) -> bool: ...

    @abstractmethod
    def list_games(self, platform: str | None = None) -> list[tuple]: ...

    @abstractmethod
    def close(self) -> None: ...


class DuckDBDatabase(AbstractDatabase):
    def __init__(self, db_path: Path | None = None, *, conn=None):
        self.conn = conn if conn is not None else _get_connection(db_path)
        _init_db(self.conn)

    def insert_game(
        self,
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
        opening_name: str | None = None,
        opening_variation: str | None = None,
    ) -> int:
        return _insert_game(
            self.conn, source, white, black, year, month, day, event,
            result, eco, time_control, url, moves, opening_name, opening_variation,
        )

    def game_exists(self, source: str, url: str) -> bool:
        return _game_exists(self.conn, source, url)

    def list_games(self, platform: str | None = None) -> list[tuple]:
        return _list_games(self.conn, platform)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def _get_connection(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    """Get a connection to the DuckDB database."""
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def _init_db(conn: duckdb.DuckDBPyConnection) -> None:
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


def _get_or_create_opening(
    conn: duckdb.DuckDBPyConnection,
    eco: str,
    name: str | None,
    variation: str | None,
) -> None:
    """Insert or update an opening in dim_opening (SCD Type 1)."""
    row = conn.execute("SELECT eco FROM dim_opening WHERE eco = ?", [eco]).fetchone()
    if row:
        conn.execute(
            """
            UPDATE dim_opening
            SET name      = COALESCE(?, name),
                variation = COALESCE(?, variation),
                updated_at = current_timestamp
            WHERE eco = ?
            """,
            [name, variation, eco],
        )
    else:
        conn.execute(
            "INSERT INTO dim_opening (eco, name, variation) VALUES (?, ?, ?)",
            [eco, name, variation],
        )


def _insert_game(
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
    opening_name: str | None = None,
    opening_variation: str | None = None,
) -> int:
    """Insert a game into the database and return its ID."""
    source_id = _get_or_create_source(conn, source)
    white_id = _get_or_create_player(conn, white)
    black_id = _get_or_create_player(conn, black)
    date_id = _get_or_create_date(conn, year, month, day)
    event_id = _get_or_create_event(conn, event)
    result_id = _get_or_create_result(conn, result)
    if eco:
        _get_or_create_opening(conn, eco, opening_name, opening_variation)

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


def _game_exists(conn: duckdb.DuckDBPyConnection, source: str, url: str) -> bool:
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


def _list_games(conn: duckdb.DuckDBPyConnection, platform: str | None = None) -> list[tuple]:
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
