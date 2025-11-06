"""
stablecoin_premiums

Utilities for fetching P2P stablecoin quotes, reference FX rates, and computing
premiums/spreads across fiat markets.

This package is designed to be:
- Safe by default (no secrets in code; use environment variables)
- Extensible (plug additional providers under `clients/`)
- Notebook- and CLI-friendly

Quick usage:
    from stablecoin_premiums.clients.binance import average_price
    from stablecoin_premiums.clients.xe import fetch_fx_rate
    from stablecoin_premiums.compute import compute_premiums

    buy = average_price("MXN", "USDT", "BUY")
    sell = average_price("MXN", "USDT", "SELL")
    fx   = fetch_fx_rate("MXN", "USD")
    if buy and sell and fx:
        out = compute_premiums(sell, buy, fx["bid"], fx["ask"])
        print(out)

Environment:
- See `.env.example` for configuration. Use a local `.env` (never commit it).
- Consider `python-dotenv` in notebooks for convenience.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

__all__ = [
    "__version__",
    "compute_premiums",
    "setup_logging",
    "load_dotenv_if_present",
    "get_package_info",
]

__version__ = "0.1.0"


def setup_logging(level: Optional[str] = None) -> None:
    """
    Configure basic logging for the package.

    Args:
        level: Optional logging level string ("DEBUG", "INFO", "WARNING", "ERROR").
               If not provided, reads LOG_LEVEL from environment (default: INFO).
    """
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    try:
        numeric_level = getattr(logging, log_level)
    except AttributeError:
        numeric_level = logging.INFO  # Fallback
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def load_dotenv_if_present(dotenv_path: Optional[str] = None) -> bool:
    """
    Load environment variables from a .env file if python-dotenv is available.
    Returns True if a .env was successfully loaded; False otherwise.

    This does nothing (and returns False) if python-dotenv is not installed.

    Args:
        dotenv_path: Optional path to a specific .env file. If None, defaults to
                     searching for ".env" in the current working directory.

    Example:
        from stablecoin_premiums import load_dotenv_if_present, setup_logging
        load_dotenv_if_present()  # best-effort
        setup_logging()
    """
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return False

    return load_dotenv(dotenv_path)  # type: ignore[no-any-return]


def get_package_info() -> dict:
    """
    Return basic package metadata as a dictionary.
    """
    return {
        "name": "stablecoin_premiums",
        "version": __version__,
        "description": "P2P stablecoin quotes, FX rates, and premium computations.",
        "license": "MIT",
        "env_vars": [
            "XE_API_ACCOUNT_ID",
            "XE_API_KEY",
            "XE_API_BASE_URL",
            "COINAPI_KEY",
            "COINAPI_BASE_URL",
            "ELDORADO_API_BASE_URL",
            "REQUEST_TIMEOUT",
            "MAX_RETRIES",
            "RETRY_SLEEP",
            "LOG_LEVEL",
        ],
    }


# Convenience import(s)
try:
    from .compute import compute_premiums
except Exception:  # pragma: no cover - safe import guard
    # Import is best-effort to keep __init__ light-weight.
    # Users can still import directly from submodules.
    pass
