-include .env
export

.PHONY: setup ingest transform dash test

setup:
	uv run python -c "\
import os; from dotenv import load_dotenv; load_dotenv(); \
import duckdb; \
token = os.environ['MOTHERDUCK_TOKEN']; \
conn = duckdb.connect(f'md:?motherduck_token={token}'); \
conn.execute('CREATE DATABASE IF NOT EXISTS chessdashboard'); \
conn.execute('CREATE SCHEMA IF NOT EXISTS chessdashboard.raw'); \
conn.execute('CREATE SCHEMA IF NOT EXISTS chessdashboard.analytics'); \
print('MotherDuck setup complete')"

ingest:
	uv run python -m ingestion.pipeline

transform:
	cd transform && uv run dbt build

dash:
	uv run streamlit run dashboard/app.py

test:
	uv run pytest tests/ -v
