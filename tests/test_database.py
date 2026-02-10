"""Tests for chessdashboard.database module."""

from chessdashboard.database import init_db, insert_game, game_exists, list_games


SAMPLE_GAME = dict(
    source="lichess",
    white="magnus",
    black="hikaru",
    year=2024,
    month=1,
    day=15,
    event="Blitz",
    result="1-0",
    eco="B90",
    time_control="300",
    url="https://lichess.org/abc123",
    moves="e4 c5 Nf3",
)


def test_init_db_creates_tables(db):
    tables = db.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
    ).fetchall()
    names = {t[0] for t in tables}
    assert names == {"dim_player", "dim_date", "dim_event", "dim_result", "dim_source", "fact_games"}


def test_init_db_seeds_sources(db):
    rows = db.execute("SELECT source FROM dim_source ORDER BY source").fetchall()
    assert [r[0] for r in rows] == ["chesscom", "lichess"]


def test_init_db_idempotent(db):
    init_db(db)
    rows = db.execute("SELECT source FROM dim_source").fetchall()
    assert len(rows) == 2


def test_insert_game_returns_id(db):
    game_id = insert_game(db, **SAMPLE_GAME)
    assert game_id == 1


def test_insert_game_creates_dimensions(db):
    insert_game(db, **SAMPLE_GAME)
    assert db.execute("SELECT COUNT(*) FROM dim_player").fetchone()[0] == 2
    assert db.execute("SELECT COUNT(*) FROM dim_date").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM dim_event").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM dim_result").fetchone()[0] == 1


def test_insert_game_reuses_dimensions(db):
    insert_game(db, **SAMPLE_GAME)
    insert_game(db, **{**SAMPLE_GAME, "url": "https://lichess.org/xyz789", "result": "0-1"})
    # Players shared — still only 2
    assert db.execute("SELECT COUNT(*) FROM dim_player").fetchone()[0] == 2
    # Two different results
    assert db.execute("SELECT COUNT(*) FROM dim_result").fetchone()[0] == 2


def test_game_exists_true(db):
    insert_game(db, **SAMPLE_GAME)
    assert game_exists(db, "lichess", "https://lichess.org/abc123") is True


def test_game_exists_false(db):
    assert game_exists(db, "lichess", "https://lichess.org/nope") is False


def test_list_games_with_platform_filter(db):
    insert_game(db, **SAMPLE_GAME)
    insert_game(db, **{**SAMPLE_GAME, "source": "chesscom", "url": "https://chess.com/1"})

    assert len(list_games(db, platform="lichess")) == 1
    assert len(list_games(db, platform="chesscom")) == 1
    assert len(list_games(db)) == 2
