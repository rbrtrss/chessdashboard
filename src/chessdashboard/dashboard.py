"""Streamlit dashboard for chessdashboard analytics."""

import os
import sys
from pathlib import Path

import duckdb
import streamlit as st
from dotenv import load_dotenv

from chessdashboard.database import DEFAULT_DB_PATH


def _parse_db_arg() -> Path:
    """Parse --db argument from sys.argv (passed after -- by Streamlit)."""
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--db" and i + 1 < len(args):
            return Path(args[i + 1])
    return DEFAULT_DB_PATH


@st.cache_resource
def get_conn():
    """Open a read-only DuckDB connection."""
    db_path = _parse_db_arg()
    if not db_path.exists():
        return None
    return duckdb.connect(str(db_path), read_only=True)


def _table_exists(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = ?", [name]
    ).fetchone()
    return row is not None


def _query(conn, sql: str, params=None):
    """Run a query and return a DataFrame."""
    if params:
        return conn.execute(sql, params).fetchdf()
    return conn.execute(sql).fetchdf()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Chess Dashboard", page_icon="♟", layout="wide")
col_title, col_refresh = st.columns([8, 1])
col_title.title("Chess Dashboard")
if col_refresh.button("Refresh", width="stretch"):
    st.cache_resource.clear()
    st.rerun()

conn = get_conn()

if conn is None:
    st.error(
        f"Database not found at `{_parse_db_arg()}`. "
        "Run `chessdashboard fetch` first to populate data."
    )
    st.stop()

required_tables = ["stg_games", "player_stats", "opening_stats",
                   "monthly_win_rate", "time_control_breakdown"]
missing = [t for t in required_tables if not _table_exists(conn, t)]
if missing:
    st.warning(
        f"Missing dbt models: {', '.join(missing)}. "
        "Run `cd chessdashboard_dbt && uv run dbt run` to build them."
    )
    st.stop()

# ---------------------------------------------------------------------------
# .env usernames
# ---------------------------------------------------------------------------

load_dotenv()
_lichess_user = os.getenv("LICHESS_USERNAME", "").strip()
_chesscom_user = os.getenv("CHESSCOM_USERNAME", "").strip()
env_users = sorted({u for u in [_lichess_user, _chesscom_user] if u})

if not env_users:
    st.warning(
        "No usernames configured. Set `LICHESS_USERNAME` and/or "
        "`CHESSCOM_USERNAME` in your `.env` file."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

platform = st.selectbox("Platform", ["All", "lichess", "chesscom"])

_quoted_env_users = ", ".join(f"'{u}'" for u in env_users)


def _player_where(extra: str = "") -> str:
    """WHERE clause for models with a `player` column."""
    clauses = [f"player IN ({_quoted_env_users})"]
    if platform != "All":
        clauses.append(f"source = '{platform}'")
    if extra:
        clauses.append(extra)
    return " WHERE " + " AND ".join(clauses)


def _stg_where() -> str:
    """WHERE clause for stg_games (white/black player columns)."""
    user_filter = (
        f"(white_player IN ({_quoted_env_users}) "
        f"OR black_player IN ({_quoted_env_users}))"
    )
    clauses = [user_filter]
    if platform != "All":
        clauses.append(f"source = '{platform}'")
    return " WHERE " + " AND ".join(clauses)


# ---------------------------------------------------------------------------
# 1. KPI row
# ---------------------------------------------------------------------------

st.header("Overview")

kpi_df = _query(
    conn,
    f"SELECT source, total_games, total_wins, win_rate FROM player_stats{_player_where()}",
)

if kpi_df.empty:
    st.info("No games match the current filters.")
    st.stop()

total_games = int(kpi_df["total_games"].sum())
total_wins = int(kpi_df["total_wins"].sum())
win_rate = round(total_wins / total_games * 100, 1) if total_games else 0.0
lichess_cnt = int(kpi_df.loc[kpi_df["source"] == "lichess", "total_games"].sum())
chesscom_cnt = int(kpi_df.loc[kpi_df["source"] == "chesscom", "total_games"].sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Games", total_games)
c2.metric("Win Rate", f"{win_rate}%")
c3.metric("Lichess Games", lichess_cnt)
c4.metric("Chess.com Games", chesscom_cnt)

# ---------------------------------------------------------------------------
# 2. Player Stats
# ---------------------------------------------------------------------------

st.header("Player Stats")
ps_df = _query(conn, f"SELECT * FROM player_stats{_player_where()}")
if ps_df.empty:
    st.info("No player stats available.")
else:
    st.dataframe(ps_df, width="stretch", hide_index=True)

# ---------------------------------------------------------------------------
# 3. Opening Stats + bar chart
# ---------------------------------------------------------------------------

st.header("Opening Stats")
src_clause = f" WHERE source = '{platform}'" if platform != "All" else ""
os_df = _query(conn, f"SELECT * FROM opening_stats{src_clause}")
if os_df.empty:
    st.info("No opening stats available.")
else:
    st.dataframe(os_df, width="stretch", hide_index=True)

    top = os_df[os_df["total_games"] >= 5].nlargest(10, "white_win_pct")
    if not top.empty:
        st.subheader("Top 10 Openings by White Win %  (min 5 games)")
        st.bar_chart(top.set_index("eco")["white_win_pct"])

# ---------------------------------------------------------------------------
# 4. Win Rate Over Time
# ---------------------------------------------------------------------------

st.header("Win Rate Over Time")

wrt_sql = f"""
    SELECT year, month, period, games, wins
    FROM monthly_win_rate{_player_where()}
    ORDER BY year, month
"""
wrt_df = _query(conn, wrt_sql)
if wrt_df.empty:
    st.info("No time data available.")
else:
    agg = (
        wrt_df.groupby(["year", "month", "period"], as_index=False)
        .agg(games=("games", "sum"), wins=("wins", "sum"))
    )
    agg["win_rate"] = (agg["wins"] / agg["games"].replace(0, float("nan")) * 100).round(1)
    st.line_chart(agg.set_index("period")["win_rate"])

# ---------------------------------------------------------------------------
# 5. Time Control Breakdown
# ---------------------------------------------------------------------------

st.header("Time Control Breakdown")

tc_sql = f"""
    SELECT time_control, SUM(games) AS games
    FROM time_control_breakdown{_player_where()}
    GROUP BY time_control
    ORDER BY games DESC
"""
tc_df = _query(conn, tc_sql)
if tc_df.empty:
    st.info("No time control data available.")
else:
    st.bar_chart(tc_df.set_index("time_control")["games"])

# ---------------------------------------------------------------------------
# 6. Recent Games
# ---------------------------------------------------------------------------

st.header("Recent Games")

rg_sql = f"""
    SELECT game_id, date, white_player, black_player, result, eco,
           time_control, source
    FROM stg_games{_stg_where()}
    ORDER BY game_id DESC
    LIMIT 50
"""
rg_df = _query(conn, rg_sql)
if rg_df.empty:
    st.info("No games to display.")
else:
    st.dataframe(rg_df, width="stretch", hide_index=True)
