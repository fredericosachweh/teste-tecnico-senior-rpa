"""Pytest configuration and fixtures for app/tests."""
import sys


def pytest_ignore_collect(collection_path, config):
    """Skip test_models_films on Python 3.14+ (Pydantic typing API not yet compatible)."""
    if sys.version_info >= (3, 14) and "test_models_films" in str(collection_path):
        return True
    return False
