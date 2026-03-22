import os

import altair as alt
import duckdb
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Chess Dashboard", layout="wide")

MOTHERDUCK_TOKEN = os.environ.get("MOTHERDUCK_TOKEN", "")
LICHESS_USERNAME = os.environ.get("LICHESS_USERNAME", "")
CHESSCOM_USERNAME = os.environ.get("CHESSCOM_USERNAME", "")


@st.cache_resource
def get_connection():
    return duckdb.connect(
        f"md:chessdashboard?motherduck_token={MOTHERDUCK_TOKEN}", read_only=True
    )


def _source_filter(source):
    if source == "Chess.com":
        return "AND source = 'chesscom'"
    elif source == "Lichess":
        return "AND source = 'lichess'"
    return ""


def _time_filter(time_categories):
    if not time_categories:
        return ""
    placeholders = ", ".join(f"'{tc}'" for tc in time_categories)
    return f"AND time_category IN ({placeholders})"


def _date_filter(start, end, date_col="played_at"):
    return f"AND {date_col} >= '{start}' AND {date_col} <= '{end}'"


@st.cache_data(ttl=600)
def load_date_range():
    conn = get_connection()
    row = conn.execute(
        "SELECT min(played_at)::date AS min_date, max(played_at)::date AS max_date "
        "FROM raw_analytics.fct_games"
    ).fetchone()
    return row[0], row[1]


@st.cache_data(ttl=600)
def load_rating_data(source, time_categories, start, end):
    conn = get_connection()
    sql = (
        "SELECT played_at, my_rating, time_category, source "
        "FROM raw_analytics.fct_games "
        f"WHERE 1=1 {_source_filter(source)} {_time_filter(time_categories)} "
        f"{_date_filter(start, end)} "
        "ORDER BY played_at"
    )
    df = conn.execute(sql).fetchdf()
    df["played_at"] = pd.to_datetime(df["played_at"])
    return df


@st.cache_data(ttl=600)
def load_daily_results(source, time_categories, start, end):
    conn = get_connection()
    sql = (
        "SELECT game_date, my_result, sum(games) AS games "
        "FROM raw_analytics.daily_results "
        f"WHERE 1=1 {_source_filter(source)} {_time_filter(time_categories)} "
        f"{_date_filter(start, end, 'game_date')} "
        "GROUP BY game_date, my_result "
        "ORDER BY game_date"
    )
    return conn.execute(sql).fetchdf()


@st.cache_data(ttl=600)
def load_opening_results(source, time_categories, start, end):
    conn = get_connection()
    sql = (
        "SELECT my_color, opening_name, "
        "sum(wins) AS wins, sum(losses) AS losses, sum(draws) AS draws, "
        "sum(games_played) AS total "
        "FROM raw_analytics.opening_stats "
        f"WHERE 1=1 {_source_filter(source)} {_time_filter(time_categories)} "
        f"{_date_filter(start, end, 'game_date')} "
        "GROUP BY my_color, opening_name "
        "ORDER BY total DESC"
    )
    return conn.execute(sql).fetchdf()


# ── Sidebar filters ──────────────────────────────────────────────────────────

st.sidebar.header("Filters")

platform = st.sidebar.radio("Platform", ["Both", "Chess.com", "Lichess"])

time_controls = st.sidebar.multiselect(
    "Time Control",
    options=["bullet", "blitz", "rapid", "classical"],
    default=["blitz", "rapid", "classical"],
)

min_date, max_date = load_date_range()
date_option = st.sidebar.radio("Date Range", ["Last 7 days", "Last 30 days", "All time"], index=2)

if date_option == "Last 7 days":
    start, end = max_date - pd.Timedelta(days=7), max_date
elif date_option == "Last 30 days":
    start, end = max_date - pd.Timedelta(days=30), max_date
else:
    start, end = min_date, max_date

# ── Title ─────────────────────────────────────────────────────────────────────

username = LICHESS_USERNAME or CHESSCOM_USERNAME or "Player"
st.title(f"{username} Chess Review")

# ── Load data ─────────────────────────────────────────────────────────────────

rating_df = load_rating_data(platform, time_controls, start, end)
daily_df = load_daily_results(platform, time_controls, start, end)
opening_df = load_opening_results(platform, time_controls, start, end)

st.caption(f"{rating_df.shape[0]} games")

if rating_df.empty:
    st.warning("No games match the selected filters.")
    st.stop()

# ── Chart 1: Elo over time ───────────────────────────────────────────────────

st.subheader("Rating over time")

rating_df["series"] = rating_df["source"] + " " + rating_df["time_category"]

elo_brush = alt.selection_interval(encodings=["x"])
series_list = sorted(rating_df["series"].unique().tolist())
elo_color = alt.Color("series:N", scale=alt.Scale(domain=series_list), legend=None)

elo_chart = (
    alt.Chart(rating_df)
    .mark_line(interpolate="monotone")
    .encode(
        x=alt.X("played_at:T", title="Date"),
        y=alt.Y("my_rating:Q", title="Elo", scale=alt.Scale(zero=False)),
        color=elo_color,
        tooltip=["played_at:T", "my_rating:Q", "series:N"],
    )
    .properties(height=300, width="container")
    .transform_filter(elo_brush)
)

elo_overview = (
    alt.Chart(rating_df)
    .mark_line(interpolate="monotone")
    .encode(
        x=alt.X("played_at:T", title=""),
        y=alt.Y("my_rating:Q", title="", axis=None, scale=alt.Scale(zero=False)),
        color=elo_color,
    )
    .properties(height=60, width="container")
    .add_params(elo_brush)
)

# Get Altair's default color palette to match legend colors
palette = alt.theme.get()
default_colors = ["#4c78a8", "#f58518", "#e45756", "#72b7b2", "#54a24b", "#eeca3b", "#b279a2", "#ff9da6"]
legend_html = " &nbsp; ".join(
    f'<span style="color:{default_colors[i % len(default_colors)]}">&#9644;</span> {s}'
    for i, s in enumerate(series_list)
)
st.markdown(legend_html, unsafe_allow_html=True)
st.altair_chart(elo_chart & elo_overview, use_container_width=True)

# ── Chart 2: Results over time ────────────────────────────────────────────────

st.subheader("Results over time")

pivot = daily_df.pivot(index="game_date", columns="my_result", values="games").fillna(0).reset_index()
for col in ["win", "draw", "loss"]:
    if col not in pivot.columns:
        pivot[col] = 0
pivot = pivot.astype({"win": int, "draw": int, "loss": int})

bars = []
for _, row in pivot.iterrows():
    d = row["game_date"]
    if row["win"] > 0:
        bars.append({"day": d, "y": 0, "y2": row["win"], "result": "win", "count": row["win"]})
    if row["draw"] > 0:
        half = row["draw"] / 2
        bars.append({"day": d, "y": -half, "y2": half, "result": "draw", "count": row["draw"]})
    if row["loss"] > 0:
        bars.append({"day": d, "y": 0, "y2": -row["loss"], "result": "loss", "count": row["loss"]})

bars_df = pd.DataFrame(bars)

color_scale = alt.Scale(
    domain=["win", "draw", "loss"],
    range=["#4CAF50", "#9E9E9E", "#F44336"],
)

if not bars_df.empty:
    brush = alt.selection_interval(encodings=["x"])

    results_chart = (
        alt.Chart(bars_df)
        .mark_bar()
        .encode(
            x=alt.X("day:T", title="Day"),
            y=alt.Y("y:Q", title="Games"),
            y2=alt.Y2("y2:Q"),
            color=alt.Color("result:N", title="Result", scale=color_scale),
            tooltip=["day:T", "result:N", "count:Q"],
        )
        .properties(height=300, width="container")
        .transform_filter(brush)
    )

    overview = (
        alt.Chart(bars_df)
        .mark_bar()
        .encode(
            x=alt.X("day:T", title=""),
            y=alt.Y("y:Q", title="", axis=None),
            y2=alt.Y2("y2:Q"),
            color=alt.Color("result:N", scale=color_scale, legend=None),
        )
        .properties(height=60, width="container")
        .add_params(brush)
    )

    st.altair_chart(results_chart & overview, use_container_width=True)

# ── Chart 3: Results by opening ──────────────────────────────────────────────

st.subheader("Results by opening")

if not opening_df.empty:
    col_white, col_sep, col_black = st.columns([10, 1, 10])

    for color, label, container in [
        ("white", "As White", col_white),
        ("black", "As Black", col_black),
    ]:
        color_df = opening_df[opening_df["my_color"] == color]
        with container:
            st.markdown(f"**{label}**")
            if color_df.empty:
                st.info("No games.")
                continue

            top = color_df.nlargest(8, "total")

            long = top.melt(
                id_vars=["opening_name", "total"],
                value_vars=["wins", "losses", "draws"],
                var_name="my_result",
                value_name="count",
            )
            long["my_result"] = long["my_result"].map(
                {"wins": "win", "losses": "loss", "draws": "draw"}
            )

            cols = st.columns(min(4, len(top)))
            for i, opening in enumerate(top["opening_name"]):
                with cols[i % len(cols)]:
                    data = long[long["opening_name"] == opening]
                    pie = (
                        alt.Chart(data)
                        .mark_arc(innerRadius=30)
                        .encode(
                            theta=alt.Theta("count:Q"),
                            color=alt.Color("my_result:N", scale=color_scale, legend=None),
                            tooltip=["my_result:N", "count:Q"],
                        )
                        .properties(title=opening, height=200, width=200)
                    )
                    st.altair_chart(pie)

    with col_sep:
        st.html('<div style="border-left: 1px solid #444; height: 100%; min-height: 400px;"></div>')
