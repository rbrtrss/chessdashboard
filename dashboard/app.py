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


@st.cache_data(ttl=600)
def load_games():
    conn = get_connection()
    df = conn.execute(
        "SELECT game_id, source, played_at, time_category, my_color, my_result, my_rating, opening_name "
        "FROM raw_analytics.fct_games ORDER BY played_at"
    ).fetchdf()
    df["played_at"] = pd.to_datetime(df["played_at"])
    return df


df = load_games()

# ── Sidebar filters ──────────────────────────────────────────────────────────

st.sidebar.header("Filters")

platform = st.sidebar.radio("Platform", ["Both", "Chess.com", "Lichess"])

time_controls = st.sidebar.multiselect(
    "Time Control",
    options=["bullet", "blitz", "rapid", "classical"],
    default=["blitz", "rapid", "classical"],
)

min_date = df["played_at"].min().date()
max_date = df["played_at"].max().date()
date_range = st.sidebar.date_input(
    "Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date
)

# ── Apply filters ─────────────────────────────────────────────────────────────

filtered = df.copy()

if platform == "Chess.com":
    filtered = filtered[filtered["source"] == "chesscom"]
elif platform == "Lichess":
    filtered = filtered[filtered["source"] == "lichess"]

if time_controls:
    filtered = filtered[filtered["time_category"].isin(time_controls)]

if len(date_range) == 2:
    start, end = date_range
    filtered = filtered[
        (filtered["played_at"].dt.date >= start)
        & (filtered["played_at"].dt.date <= end)
    ]

# ── Title ─────────────────────────────────────────────────────────────────────

username = LICHESS_USERNAME or CHESSCOM_USERNAME or "Player"
st.title(f"{username} Chess Review")
st.caption(f"{len(filtered)} games")

if filtered.empty:
    st.warning("No games match the selected filters.")
    st.stop()

# ── Chart 1: Elo over time ───────────────────────────────────────────────────

st.subheader("Rating over time")

elo_chart = (
    alt.Chart(filtered)
    .mark_line(interpolate="monotone")
    .encode(
        x=alt.X("played_at:T", title="Date"),
        y=alt.Y("my_rating:Q", title="Elo", scale=alt.Scale(zero=False)),
        tooltip=["played_at:T", "my_rating:Q", "time_category:N", "source:N"],
    )
    .properties(height=350, width="container")
    .interactive()
)
st.altair_chart(elo_chart, use_container_width=True)

# ── Chart 2: Results over time ────────────────────────────────────────────────

st.subheader("Results over time")

results = filtered.copy()
results["day"] = results["played_at"].dt.date

results_agg = (
    results.groupby(["day", "my_result"]).size().reset_index(name="count")
)

# Pivot to compute y positions: wins above zero, losses below, draws centered at zero
pivot = results_agg.pivot(index="day", columns="my_result", values="count").fillna(0).reset_index()
for col in ["win", "draw", "loss"]:
    if col not in pivot.columns:
        pivot[col] = 0
pivot = pivot.astype({"win": int, "draw": int, "loss": int})

bars = []
for _, row in pivot.iterrows():
    d = row["day"]
    # Wins: 0 to +wins
    if row["win"] > 0:
        bars.append({"day": d, "y": 0, "y2": row["win"], "result": "win", "count": row["win"]})
    # Draws: centered around 0 (-half to +half)
    if row["draw"] > 0:
        half = row["draw"] / 2
        bars.append({"day": d, "y": -half, "y2": half, "result": "draw", "count": row["draw"]})
    # Losses: 0 to -losses
    if row["loss"] > 0:
        bars.append({"day": d, "y": 0, "y2": -row["loss"], "result": "loss", "count": row["loss"]})

bars_df = pd.DataFrame(bars)

color_scale = alt.Scale(
    domain=["win", "draw", "loss"],
    range=["#4CAF50", "#9E9E9E", "#F44336"],
)

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

top_openings = (
    filtered.groupby("opening_name")
    .size()
    .reset_index(name="total")
    .nlargest(8, "total")["opening_name"]
)

opening_data = filtered[filtered["opening_name"].isin(top_openings)]
opening_agg = (
    opening_data.groupby(["opening_name", "my_result"])
    .size()
    .reset_index(name="count")
)

cols = st.columns(min(4, len(top_openings)))
for i, opening in enumerate(top_openings):
    with cols[i % len(cols)]:
        data = opening_agg[opening_agg["opening_name"] == opening]
        pie = (
            alt.Chart(data)
            .mark_arc(innerRadius=30)
            .encode(
                theta=alt.Theta("count:Q"),
                color=alt.Color("my_result:N", title="Result", scale=color_scale),
                tooltip=["my_result:N", "count:Q"],
            )
            .properties(title=opening, height=200, width=200)
        )
        st.altair_chart(pie)
