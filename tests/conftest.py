"""Pytest configuration for stablecoin_premiums tests."""

import os
import sys
from pathlib import Path

# Add the src directory to Python path so we can import stablecoin_premiums
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def pytest_configure(config):
    """Configure pytest."""
    # Set test environment variables
    os.environ["LOG_LEVEL"] = "WARNING"  # Reduce noise during tests
    os.environ["REQUEST_TIMEOUT"] = "1.0"  # Short timeout for tests
    os.environ["MAX_RETRIES"] = "1"  # Minimal retries for tests
    os.environ["RETRY_SLEEP"] = "0.1"  # Short sleep for tests
