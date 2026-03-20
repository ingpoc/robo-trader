"""
Pytest configuration for API tests
"""

import pytest
import httpx


@pytest.fixture
def client():
    """HTTP client fixture"""
    return httpx.Client()


@pytest.fixture
def BASE_URL():
    """Base URL fixture"""
    return "http://localhost:8000"
