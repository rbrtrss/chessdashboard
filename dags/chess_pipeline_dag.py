"""Airflow DAG: fetch chess games then run dbt transforms via Cosmos."""

import os
from datetime import datetime
from pathlib import Path

from airflow.decorators import dag, task
from cosmos import DbtTaskGroup, ProjectConfig, ProfileConfig, RenderConfig

DBT_PROJECT_PATH = Path("/opt/airflow/chessdashboard_dbt")
DBT_PROFILES_PATH = DBT_PROJECT_PATH / "profiles.yml"


def _load_env() -> None:
    """Load .env file mounted into the container."""
    from dotenv import load_dotenv

    load_dotenv("/opt/airflow/.env")


def _fetch_platform(platform: str, env_key: str) -> None:
    """Fetch games for a single platform and store them in DuckDB."""
    _load_env()

    username = os.environ.get(env_key)
    if not username:
        raise ValueError(f"{env_key} not set in .env")

    from chessdashboard.database import get_connection, init_db, insert_game, game_exists
    from chessdashboard import lichess_client, chesscom_client

    conn = get_connection(DUCKDB_PATH)
    init_db(conn)

    if platform == "lichess":
        games_iter = lichess_client.fetch_games(username)
    else:
        games_iter = chesscom_client.fetch_games(username)

    loaded, skipped = 0, 0
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

    conn.close()
    print(f"{platform}: {loaded} game(s) loaded, {skipped} duplicate(s) skipped.")


@dag(
    dag_id="chess_pipeline",
    schedule="0 6 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["chess", "etl"],
)
def chess_pipeline():
    @task()
    def fetch_lichess_games():
        _fetch_platform("lichess", "LICHESS_USERNAME")

    @task()
    def fetch_chesscom_games():
        _fetch_platform("chesscom", "CHESSCOM_USERNAME")

    dbt_transform = DbtTaskGroup(
        group_id="dbt_transform",
        project_config=ProjectConfig(dbt_project_path=str(DBT_PROJECT_PATH)),
        profile_config=ProfileConfig(
            profile_name="chessdashboard_dbt",
            target_name="dev",
            profiles_yml_filepath=str(DBT_PROFILES_PATH),
        ),
        render_config=RenderConfig(
            test_behavior="after_all",
        ),
    )

    fetch_lichess_games() >> fetch_chesscom_games() >> dbt_transform


chess_pipeline()
