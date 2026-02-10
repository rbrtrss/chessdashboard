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

# Fetch games
uv run chessdashboard fetch <username> --platform lichess [--max N]
uv run chessdashboard fetch <username> --platform chesscom

# List stored games
uv run chessdashboard list [--platform lichess|chesscom]

# Run dbt models
cd chessdashboard_dbt && uv run dbt run
cd chessdashboard_dbt && uv run dbt test
```

## Architecture

The codebase follows a simple layered structure in `src/chessdashboard/`:

- **cli.py**: Click-based CLI entry point. Defines commands (fetch, list) and orchestrates the other modules.
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
- Before commiting changes, **ALWAYS** use the @.claude/skills/generating-commit-messages skill to generate commit messages
