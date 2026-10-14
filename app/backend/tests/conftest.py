from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from store.api import create_app  # noqa: E402


@pytest.fixture
def app(tmp_path: Path):
    return create_app(tmp_path / "test.db")


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client

