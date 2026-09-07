"""Pytest configuration and shared fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Provide a TestClient instance for testing API endpoints."""
    with TestClient(app) as test_client:
        yield test_client
