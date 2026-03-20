.PHONY: ingest transform dash

ingest:
	uv run python -m ingestion.pipeline

transform:
	cd transform && uv run dbt build

dash:
	uv run streamlit run dashboard/app.py
