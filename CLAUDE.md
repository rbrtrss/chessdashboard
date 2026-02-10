# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

chessdashboard fetches chess games from Lichess and Chess.com APIs, stores them in a DuckDB star schema, and provides a dbt layer for analytics.

## Plan Mode

- Make the plan extremely concise. Sacrifice grammar for the sake of concision.
- At the end of each plan, give me a list of unresolved questions to answer, if any.

## Development Rules

- **Always use `uv` for all Python operations.** Do not use pip, python, or other tools directly. Use `uv run`, `uv sync`, `uv add`, etc.

## Development Commands

```bash
# Sync dependencies
uv sync

# Fetch games (uses .env usernames by default)
uv run chessdashboard fetch                                    # both platforms
uv run chessdashboard fetch --platform lichess [--max N]       # one platform
uv run chessdashboard fetch -u <username> --platform lichess   # explicit user

# List stored games
uv run chessdashboard list [--platform lichess|chesscom]

# Launch Streamlit dashboard (requires dbt models)
uv run chessdashboard dashboard [--port 8501]

# Run dbt models
cd chessdashboard_dbt && uv run dbt run
cd chessdashboard_dbt && uv run dbt test
```

## Architecture

The codebase follows a simple layered structure in `src/chessdashboard/`:

- **cli.py**: Click-based CLI entry point. Defines commands (fetch, list, dashboard) and orchestrates the other modules.
- **dashboard.py**: Streamlit analytics dashboard. Displays KPIs, player stats, opening stats, win rate over time, and recent games for .env usernames.
- **schema.py**: DDL definitions for the star schema database structure.
- **database.py**: DuckDB persistence layer using a star schema with `_get_or_create` pattern.
- **lichess_client.py**: Streams games from Lichess API as NDJSON via httpx.
- **chesscom_client.py**: Fetches games from Chess.com monthly archives, parses PGN fields.

### Database Schema

Star schema stored in `~/.chessdashboard/games.duckdb`:
- **dim_player**: username-based player dimension
- **dim_date**: year/month/day
- **dim_event**: tournament/match info
- **dim_result**: game outcomes
- **dim_source**: platform origin (lichess, chesscom)
- **fact_games**: central fact table with FKs to all dimensions

### dbt Layer

Located in `chessdashboard_dbt/`. Transforms raw star schema into analytics-ready models:
- **stg_games**: denormalized view joining all dimensions
- **player_stats**: win/loss/draw by player and source
- **opening_stats**: win rates by ECO code and source

### Commit Guidelines
- Before committing changes, **ALWAYS** use the @.claude/skills/generating-commit-messages skill to generate commit messages
