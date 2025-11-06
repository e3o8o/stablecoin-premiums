# 1000WordsCrypto/stablecoin-premiums/src/stablecoin_premiums/clients/coinapi.py
"""
Optional CoinAPI client stub.

This module provides a minimal adapter for CoinAPI.io to fetch reference
exchange rates that can be used alongside P2P quotes to compute premiums.

It is implemented defensively:
- No secrets are hardcoded; it reads credentials from environment variables
  or optional package config if available.
- All network errors return None rather than raising, so callers can handle
  missing data gracefully.
- Endpoints are limited to the most common public REST paths.

Environment variables (loaded via optional package config when present):
    COINAPI_KEY
    COINAPI_BASE_URL (default: https://rest.coinapi.io)
    REQUEST_TIMEOUT (default: 15.0 seconds)

CoinAPI docs:
    https://docs.coinapi.io/

Example usage:
    from stablecoin_premiums.clients.coinapi import get_exchange_rate

    # Reference FX pair (e.g., USD -> MXN)
    rate = get_exchange_rate("USD", "MXN")
    if rate is not None:
        print("USD/MXN:", rate)

Notes:
- Respect provider Terms of Service and rate limits.
- For additional endpoints (OHLCV, order books, symbols), add dedicated
  functions here following the same safety pattern.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests  # type: ignore[import-untyped]

# Module-level type declarations
COINAPI_BASE_URL: str
COINAPI_KEY: Optional[str]
REQUEST_TIMEOUT: float

# Attempt to use shared package config first; otherwise fall back to raw env.
try:
    from stablecoin_premiums.config import (  # type: ignore
        COINAPI_BASE_URL as _PKG_COINAPI_BASE,
    )
    from stablecoin_premiums.config import (  # type: ignore
        COINAPI_KEY as _PKG_COINAPI_KEY,
    )
    from stablecoin_premiums.config import (  # type: ignore
        REQUEST_TIMEOUT as _PKG_TIMEOUT,
    )

    COINAPI_BASE_URL = _PKG_COINAPI_BASE or "https://rest.coinapi.io"
    COINAPI_KEY = _PKG_COINAPI_KEY
    REQUEST_TIMEOUT = float(_PKG_TIMEOUT or 15.0)
except Exception:
    COINAPI_BASE_URL = os.getenv("COINAPI_BASE_URL") or "https://rest.coinapi.io"
    COINAPI_KEY = os.getenv("COINAPI_KEY")
    REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT") or "15.0")

__all__ = [
    "COINAPI_BASE_URL",
    "is_configured",
    "get_exchange_rate",
    "get_symbol_rate",
]


def is_configured() -> bool:
    """
    Returns True if an API key appears configured; False otherwise.
    """
    return bool(COINAPI_KEY)


def _headers() -> Dict[str, str]:
    """
    Build request headers with API key if configured.
    """
    hdrs = {
        "Accept": "application/json",
        "User-Agent": "stablecoin-premiums/0.1 (+https://github.com/)",
    }
    if COINAPI_KEY:
        hdrs["X-CoinAPI-Key"] = str(COINAPI_KEY)
    return hdrs


def get_exchange_rate(
    asset_base: str,
    asset_quote: str,
    *,
    time: Optional[str] = None,
    invert: bool = False,
    extra_params: Optional[Dict[str, Any]] = None,
) -> Optional[float]:
    """
    Fetch a reference exchange rate from CoinAPI:
        GET /v1/exchangerate/{asset_id_base}/{asset_id_quote}

    Args:
        asset_base: Base asset code (e.g., "USD", "BTC").
        asset_quote: Quote asset code (e.g., "MXN", "USDT").
        time: Optional specific timestamp (RFC 3339) for historical rates.
        invert: If True, returns 1 / rate (quote/base) if rate > 0.
        extra_params: Additional query parameters to pass through.

    Returns:
        float rate on success; None on error or if not configured.

    Notes:
        - For historical queries, set `time="2025-10-01T00:00:00"`, etc.
        - Rate shape in response: {"asset_id_base":"USD", "asset_id_quote":"MXN", "rate": 17.12, ...}
    """
    if not is_configured():
        return None

    url = f"{COINAPI_BASE_URL.rstrip('/')}/v1/exchangerate/{asset_base}/{asset_quote}"
    params: Dict[str, Any] = {}
    if time:
        params["time"] = time
    if extra_params:
        params.update(extra_params)

    try:
        resp = requests.get(
            url, headers=_headers(), params=params, timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        j = resp.json()
        rate = _safe_float(j.get("rate"))
        if rate is None or rate <= 0:
            return None
        if invert:
            return 1.0 / rate if rate > 0 else None
        return rate
    except requests.RequestException:
        return None
    except ValueError:
        return None


def get_symbol_rate(
    symbol_id: str,
    *,
    time: Optional[str] = None,
    invert: bool = False,
    extra_params: Optional[Dict[str, Any]] = None,
) -> Optional[float]:
    """
    Fetch a symbol-specific rate (if supported or mapped) via CoinAPI.
    Some integrations identify pairs via symbol_id (e.g., "BITSTAMP_SPOT_BTC_USD").

    Canonical CoinAPI path for symbols often differs (e.g., /v1/exchangerate/{base}/{quote}),
    but this helper keeps a separate method in case you implement a custom mapping layer
    or a proxy that supports symbol_id directly.

    If you do not use symbol-oriented endpoints, prefer `get_exchange_rate()`.

    Args:
        symbol_id: Provider symbol identifier (e.g., "BINANCE_SPOT_BTC_USDT").
        time: Optional RFC 3339 time for historical rate.
        invert: If True, return 1/rate.
        extra_params: Additional query parameters.

    Returns:
        float rate on success; None on error or if not configured.
    """
    # By default CoinAPI expects base/quote path; if you maintain a proxy that
    # maps symbol_id -> base/quote, resolve it here first. For now, we call a
    # hypothetical path and return None on failure.
    if not is_configured():
        return None

    # Hypothetical endpoint; adapt if you maintain a proxy for symbol-based queries.
    url = f"{COINAPI_BASE_URL.rstrip('/')}/v1/exchangerate/{symbol_id}"
    params: Dict[str, Any] = {}
    if time:
        params["time"] = time
    if extra_params:
        params.update(extra_params)

    try:
        resp = requests.get(
            url, headers=_headers(), params=params, timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        j = resp.json()
        # Try common keys
        rate = _safe_float(j.get("rate"))
        if rate is None or rate <= 0:
            return None
        if invert:
            return 1.0 / rate if rate > 0 else None
        return rate
    except requests.RequestException:
        return None
    except ValueError:
        return None


def _safe_float(val: Any) -> Optional[float]:
    """Convert to float or return None on failure."""
    try:
        if val is None:
            return None
        return float(val)
    except (TypeError, ValueError):
        return None
