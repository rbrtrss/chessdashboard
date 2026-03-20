import os

from dotenv import load_dotenv

load_dotenv()

MOTHERDUCK_TOKEN = os.environ.get("MOTHERDUCK_TOKEN", "")
LICHESS_USERNAME = os.environ.get("LICHESS_USERNAME", "")
CHESSCOM_USERNAME = os.environ.get("CHESSCOM_USERNAME", "")
DESTINATION = os.environ.get("DESTINATION", "duckdb")
