"""Shared test fixtures and configuration for ToyDB tests"""
import os
import shutil
import tempfile
import pytest
from pathlib import Path


@pytest.fixture
def temp_db_path():
    """Create a temporary database path for testing"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    yield db_path
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def clean_test_files():
    """Clean up test database files after test"""
    test_files = ["test.db", "test.db.wal"]
    yield
    for f in test_files:
        if os.path.exists(f):
            os.remove(f)


@pytest.fixture(scope="session")
def project_root():
    """Get the project root directory"""
    return Path(__file__).parent.parent
