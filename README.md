# chessdashboard

CLI tool to fetch chess games from Lichess and Chess.com, store in DuckDB, and analyze with dbt.

## Architecture

### Pipeline

```mermaid
flowchart TD
    LI[Lichess API\nNDJSON stream]
    CC[Chess.com API\nPGN archives]
    LC[lichess_client.py]
    CCC[chesscom_client.py]
    DB[(DuckDB\ngames.duckdb)]
    STG[stg_games\nincremental]
    PS[player_stats\ntable]
    OS[opening_stats\ntable]
    DASH[Streamlit\nDashboard]

    LI --> LC
    CC --> CCC
    LC --> DB
    CCC --> DB
    DB --> STG
    STG --> PS
    STG --> OS
    PS --> DASH
    OS --> DASH
    STG --> DASH
```

### Database schema

```mermaid
erDiagram
    fact_games {
        int game_id PK
        int date_id FK
        int event_id FK
        int source_id FK
        int playing_white_id FK
        int playing_black_id FK
        int result_id FK
        text eco
        text time_control
        text url
        text moves
    }
    dim_player {
        int player_id PK
        text username
        text display_name
    }
    dim_date {
        int date_id PK
        text date
        int year
        int month
        int day
    }
    dim_event {
        int event_id PK
        text name
        text site
        text round
    }
    dim_result {
        int result_id PK
        text result
    }
    dim_source {
        int source_id PK
        text source
    }
    dim_opening {
        text eco PK
        text name
        text variation
        timestamp created_at
        timestamp updated_at
    }

    fact_games }o--|| dim_player : "plays white"
    fact_games }o--|| dim_player : "plays black"
    fact_games }o--|| dim_date : "played on"
    fact_games }o--|| dim_event : "part of"
    fact_games }o--|| dim_result : "ended with"
    fact_games }o--|| dim_source : "from"
    fact_games }o--o| dim_opening : "opened with"
```

## Install

```bash
uv sync
```

## Configuration

Create a `.env` file in the project root with your usernames:

```bash
LICHESS_USERNAME=your_lichess_username
CHESSCOM_USERNAME=your_chesscom_username
```

The `fetch` command uses these as defaults when `--username` is omitted. The dashboard filters games to these usernames.

## Usage

### Fetch games

```bash
# Fetch from both platforms using .env usernames
uv run chessdashboard fetch

# Fetch from one platform
uv run chessdashboard fetch --platform lichess

# Explicit username and limit
uv run chessdashboard fetch -u <username> --platform lichess --max 50
```

### List stored games

```bash
uv run chessdashboard list
uv run chessdashboard list --platform lichess
```

### Launch dashboard

```bash
# Requires dbt models: cd chessdashboard_dbt && uv run dbt run
uv run chessdashboard dashboard

# Custom port
uv run chessdashboard dashboard --port 8080
```

## dbt Usage

The dbt project transforms raw game data into analytics-ready models.

```bash
cd chessdashboard_dbt

# Run all models
uv run dbt run

# Run tests
uv run dbt test

# Run both
uv run dbt build
```

### Models

- **stg_games**: Denormalized view of all games with dimensions joined
- **player_stats**: Win/loss/draw statistics per player and source
- **opening_stats**: Performance statistics by ECO opening code and source
