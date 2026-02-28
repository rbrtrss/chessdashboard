"""Shared fixtures for chessdashboard tests."""

import duckdb
import pytest

from chessdashboard.database import DuckDBDatabase


@pytest.fixture
def db():
    """In-memory DuckDB connection with schema initialized."""
    conn = duckdb.connect(":memory:")
    database = DuckDBDatabase(conn=conn)
    yield database
    database.close()
