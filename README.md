# chessdashboard

CLI tool to fetch chess games from Lichess and Chess.com, store in DuckDB, and analyze with dbt.

## Install

```bash
uv sync
```

## Usage

### Fetch games

```bash
# Fetch from Lichess
uv run chessdashboard fetch <username> --platform lichess

# Fetch from Chess.com
uv run chessdashboard fetch <username> --platform chesscom

# Limit number of games
uv run chessdashboard fetch <username> --platform lichess --max 50
```

### List stored games

```bash
uv run chessdashboard list
uv run chessdashboard list --platform lichess
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
