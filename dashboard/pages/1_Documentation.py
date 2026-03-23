import streamlit as st

st.set_page_config(page_title="Documentation", layout="wide")

st.title("Documentation")

st.header("Data sources")
st.markdown(
    """
    - **Lichess** -- games fetched from the Lichess API (NDJSON export)
    - **Chess.com** -- games fetched from the Chess.com Published Data API (PGN archives)

    The pipeline runs daily at **06:00 UTC** via GitHub Actions. Games are deduplicated
    on `game_id`, so re-runs never create duplicates. Dashboard data is cached for
    10 minutes.
    """
)

st.header("How games are classified")

st.subheader("Time controls")
st.markdown(
    """
    Time control is derived from the formula: **base seconds + 40 x increment**.

    | Category | Total time |
    |---|---|
    | Bullet | < 3 min |
    | Blitz | < 10 min |
    | Rapid | < 30 min |
    | Classical | >= 30 min |
    """
)

st.subheader("Opponent strength")
st.markdown(
    """
    Based on Elo difference (your rating minus opponent rating):

    | Bucket | Rating difference |
    |---|---|
    | Much stronger | < -200 |
    | Stronger | -200 to -50 |
    | Even | -50 to +50 |
    | Weaker | +50 to +200 |
    | Much weaker | > +200 |
    """
)

st.subheader("Openings")
st.markdown(
    """
    Openings are identified by ECO code (Encyclopedia of Chess Openings, A00--E99)
    and mapped to human-readable names.
    """
)

st.header("Charts")
st.markdown(
    """
    - **Rating over time** -- line chart of your Elo per game, split by platform and
      time control. Use the brush on the mini-chart below to zoom into a date range.
    - **Results over time** -- bar chart showing daily wins (green), draws (grey), and
      losses (red). Also supports brush-to-zoom.
    - **Results by opening** -- donut charts for your top 8 openings as white and black,
      showing win/draw/loss distribution.
    """
)

st.header("Filters")
st.markdown(
    """
    All filters are in the sidebar on the main page:

    - **Platform** -- show games from both platforms or just one
    - **Time Control** -- select one or more categories
    - **Date Range** -- last 7 days, last 30 days, or all time (relative to most recent game)
    """
)
