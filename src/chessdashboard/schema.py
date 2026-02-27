"""DDL definitions for the star schema of chess games."""

DIM_PLAYER_DDL = """
CREATE TABLE IF NOT EXISTS dim_player (
    player_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL
);
"""

DIM_DATE_DDL = """
CREATE TABLE IF NOT EXISTS dim_date (
    date_id INTEGER PRIMARY KEY,
    date TEXT,
    year INTEGER,
    month INTEGER,
    day INTEGER
);
"""

DIM_EVENT_DDL = """
CREATE TABLE IF NOT EXISTS dim_event (
    event_id INTEGER PRIMARY KEY,
    name TEXT,
    site TEXT,
    round TEXT
);
"""

DIM_RESULT_DDL = """
CREATE TABLE IF NOT EXISTS dim_result (
    result_id INTEGER PRIMARY KEY,
    result TEXT NOT NULL UNIQUE
);
"""

DIM_SOURCE_DDL = """
CREATE TABLE IF NOT EXISTS dim_source (
    source_id INTEGER PRIMARY KEY,
    source TEXT NOT NULL UNIQUE
);
"""

DIM_OPENING_DDL = """
CREATE TABLE IF NOT EXISTS dim_opening (
    eco        TEXT PRIMARY KEY,
    name       TEXT,
    variation  TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);
"""

FACT_GAMES_DDL = """
CREATE TABLE IF NOT EXISTS fact_games (
    game_id INTEGER NOT NULL,
    date_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    source_id INTEGER NOT NULL,
    playing_white_id INTEGER NOT NULL,
    playing_black_id INTEGER NOT NULL,
    result_id INTEGER NOT NULL,
    eco TEXT,
    time_control TEXT,
    url TEXT,
    moves TEXT,
    PRIMARY KEY (game_id),
    FOREIGN KEY (playing_white_id) REFERENCES dim_player(player_id),
    FOREIGN KEY (playing_black_id) REFERENCES dim_player(player_id),
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id),
    FOREIGN KEY (event_id) REFERENCES dim_event(event_id),
    FOREIGN KEY (result_id) REFERENCES dim_result(result_id),
    FOREIGN KEY (source_id) REFERENCES dim_source(source_id)
);
"""

# Order for table creation (dimensions before fact)
ALL_DDL = [
    DIM_PLAYER_DDL,
    DIM_DATE_DDL,
    DIM_EVENT_DDL,
    DIM_RESULT_DDL,
    DIM_SOURCE_DDL,
    DIM_OPENING_DDL,
    FACT_GAMES_DDL,
]
