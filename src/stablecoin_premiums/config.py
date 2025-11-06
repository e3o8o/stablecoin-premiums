"""
Configuration module for stablecoin_premiums.

Reads configuration from environment variables with sane defaults.
Optionally loads a local ".env" file if python-dotenv is installed.

Usage:
    from stablecoin_premiums.config import (
        XE_API_ACCOUNT_ID, XE_API_KEY, XE_API_BASE_URL,
        COINAPI_KEY, COINAPI_BASE_URL,
        ELDORADO_API_BASE_URL,
        REQUEST_TIMEOUT, MAX_RETRIES, RETRY_SLEEP,
        DEFAULT_ASSET, REF_FIAT, DEFAULT_FIATS,
        LOG_LEVEL, require, asdict,
    )

Notes:
- Do NOT hardcode secrets in code. Provide them via environment variables.
- To use a local .env in development, install "python-dotenv" and call
  load_dotenv_if_present() before accessing config variables.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

__all__ = [
    # Core FX & data providers
    "XE_API_ACCOUNT_ID",
    "XE_API_KEY",
    "XE_API_BASE_URL",
    "COINAPI_KEY",
    "COINAPI_BASE_URL",
    "ELDORADO_API_BASE_URL",
    # Runtime knobs
    "REQUEST_TIMEOUT",
    "MAX_RETRIES",
    "RETRY_SLEEP",
    # Defaults for CLI / examples
    "DEFAULT_ASSET",
    "REF_FIAT",
    "DEFAULT_FIATS",
    "LOG_LEVEL",
    # Helpers
    "load_dotenv_if_present",
    "get_env",
    "get_int",
    "get_float",
    "parse_list",
    "require",
    "asdict",
]


# --------
# Helpers
# --------


def load_dotenv_if_present(dotenv_path: Optional[str] = None) -> bool:
    """
    Best-effort .env loader. Returns True if loaded, False otherwise.

    This function does nothing if python-dotenv is not installed. Keep it
    optional so production environments do not require the dependency.
    """
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return False
    return bool(load_dotenv(dotenv_path))


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """Fetch a string environment variable with optional default."""
    val = os.getenv(name)
    if val is None or val == "":
        return default
    return val


def get_int(name: str, default: int) -> int:
    """Fetch an integer environment variable with fallback default."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_float(name: str, default: float) -> float:
    """Fetch a float environment variable with fallback default."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def parse_list(name: str, default: Optional[List[str]] = None) -> List[str]:
    """
    Parse a comma-separated list from an env var into a list of strings.
    Trims whitespace and ignores empty entries.
    """
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default or []
    return [item.strip() for item in raw.split(",") if item.strip()]


def require(var_name: str, value: Optional[str]) -> str:
    """
    Ensure a required environment variable is present (non-empty).

    Raises:
        ValueError: if value is None/empty.
    """
    if value is None or value == "":
        raise ValueError(f"Missing required environment variable: {var_name}")
    return value


# -------------------------
# Provider Config (Env-based)
# -------------------------

# XE (FX rates)
XE_API_ACCOUNT_ID: Optional[str] = get_env("XE_API_ACCOUNT_ID")
XE_API_KEY: Optional[str] = get_env("XE_API_KEY")
XE_API_BASE_URL: str = (
    get_env("XE_API_BASE_URL", "https://xecdapi.xe.com") or "https://xecdapi.xe.com"
)  # typically unchanged

# CoinAPI (optional, example upstream)
COINAPI_KEY: Optional[str] = get_env("COINAPI_KEY")
COINAPI_BASE_URL: str = (
    get_env("COINAPI_BASE_URL", "https://rest.coinapi.io") or "https://rest.coinapi.io"
)

# Eldorado (optional; depends on access/documents)
ELDORADO_API_BASE_URL: str = (
    get_env("ELDORADO_API_BASE_URL", "https://api.eldorado.io/api")
    or "https://api.eldorado.io/api"
)

# -------------------------
# Runtime / Tuning
# -------------------------

REQUEST_TIMEOUT: float = get_float("REQUEST_TIMEOUT", 15.0)  # seconds
MAX_RETRIES: int = get_int("MAX_RETRIES", 3)
RETRY_SLEEP: float = get_float("RETRY_SLEEP", 5.0)  # seconds between retries

# -------------------------
# CLI / Example Defaults
# -------------------------

DEFAULT_ASSET: str = get_env("DEFAULT_ASSET", "USDT") or "USDT"
REF_FIAT: str = get_env("REF_FIAT", "USD") or "USD"
DEFAULT_FIATS: List[str] = parse_list("DEFAULT_FIATS", default=[])

# -------------------------
# Logging
# -------------------------

LOG_LEVEL: str = (get_env("LOG_LEVEL", "INFO") or "INFO").upper()


def asdict() -> Dict[str, Any]:
    """
    Return the current configuration as a dictionary (secrets are included here,
    so do not log/print in production).
    """
    return {
        # Providers
        "XE_API_ACCOUNT_ID": XE_API_ACCOUNT_ID,
        "XE_API_KEY": XE_API_KEY,
        "XE_API_BASE_URL": XE_API_BASE_URL,
        "COINAPI_KEY": COINAPI_KEY,
        "COINAPI_BASE_URL": COINAPI_BASE_URL,
        "ELDORADO_API_BASE_URL": ELDORADO_API_BASE_URL,
        # Runtime
        "REQUEST_TIMEOUT": REQUEST_TIMEOUT,
        "MAX_RETRIES": MAX_RETRIES,
        "RETRY_SLEEP": RETRY_SLEEP,
        # Defaults
        "DEFAULT_ASSET": DEFAULT_ASSET,
        "REF_FIAT": REF_FIAT,
        "DEFAULT_FIATS": DEFAULT_FIATS,
        # Logging
        "LOG_LEVEL": LOG_LEVEL,
    }
