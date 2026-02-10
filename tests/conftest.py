"""Shared fixtures for chessdashboard tests."""

import duckdb
import pytest

from chessdashboard.database import init_db


@pytest.fixture
def db():
    """In-memory DuckDB connection with schema initialized."""
    conn = duckdb.connect(":memory:")
    init_db(conn)
    yield conn
    conn.close()
