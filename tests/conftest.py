"""Shared test fixtures for Folio."""

from unittest.mock import patch

import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def tmp_config(tmp_path):
    """Write a valid .profile.yml to a temp directory and return its path."""
    config_text = (FIXTURES_DIR / "sample_config.yml").read_text()
    config_path = tmp_path / ".profile.yml"
    config_path.write_text(config_text)
    return config_path


@pytest.fixture(autouse=True)
def _no_network_contributions():
    """Block the contribution GraphQL POST by default; tests opt in explicitly."""
    with patch("folio.github.requests.post", side_effect=ConnectionError("blocked in tests")):
        yield
