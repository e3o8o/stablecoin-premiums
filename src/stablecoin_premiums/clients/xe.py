"""
XE FX client for fetching reference FX rates (mid, with bid/ask mapped to mid if only mid is available).

This module reads XE API credentials from environment variables or an optional
package config if present. It queries the `convert_from` endpoint to obtain a
reference conversion rate between a reference fiat (e.g., USD) and a target fiat
(e.g., MXN). Many XE plans return only the "mid" rate; in that case, this client
maps both bid and ask to the mid for downstream convenience.

Environment variables:
    XE_API_ACCOUNT_ID
    XE_API_KEY
    XE_API_BASE_URL (default: https://xecdapi.xe.com)

Optional runtime knobs (if package config is unavailable, defaults apply):
    REQUEST_TIMEOUT (default: 15.0 seconds)

Example:
    from stablecoin_premiums.clients.xe import fetch_fx_rate

    # Convert from USD to MXN reference:
    fx = fetch_fx_rate(base="MXN", ref_fiat="USD")
    if fx:
        print(fx)  # {"mid": 17.12, "bid": 17.12, "ask": 17.12}

Notes:
- You must supply valid XE API credentials. If credentials are missing or invalid,
  the function returns None.
- Respect the provider's terms of service and rate limits.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests  # type: ignore[import-untyped]

# Module-level type declarations
XE_API_ACCOUNT_ID: Optional[str]
XE_API_KEY: Optional[str]
XE_API_BASE_URL: str
REQUEST_TIMEOUT: float

# Attempt to read shared config if available; otherwise, fall back to env/defaults.
try:
    # Prefer package-level config if present.
    from stablecoin_premiums.config import (
        REQUEST_TIMEOUT as _PKG_REQUEST_TIMEOUT,
    )
    from stablecoin_premiums.config import (  # type: ignore
        XE_API_ACCOUNT_ID as _PKG_XE_ID,
    )
    from stablecoin_premiums.config import (
        XE_API_BASE_URL as _PKG_XE_BASE_URL,
    )
    from stablecoin_premiums.config import (
        XE_API_KEY as _PKG_XE_KEY,
    )

    XE_API_ACCOUNT_ID = _PKG_XE_ID
    XE_API_KEY = _PKG_XE_KEY
    XE_API_BASE_URL = _PKG_XE_BASE_URL or "https://xecdapi.xe.com"
    REQUEST_TIMEOUT = float(_PKG_REQUEST_TIMEOUT or 15.0)
except Exception:
    # Fallback to environment variables if package config isn't available.
    XE_API_ACCOUNT_ID = os.getenv("XE_API_ACCOUNT_ID")
    XE_API_KEY = os.getenv("XE_API_KEY")
    XE_API_BASE_URL = os.getenv("XE_API_BASE_URL") or "https://xecdapi.xe.com"
    REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT") or "15.0")

# Public exports
__all__ = ["fetch_fx_rate", "is_configured", "XE_API_BASE_URL"]


def is_configured() -> bool:
    """
    Returns True if XE credentials appear configured in the current environment;
    False otherwise.
    """
    return bool(XE_API_ACCOUNT_ID and XE_API_KEY)


def fetch_fx_rate(
    base: str, ref_fiat: str, *, amount: float = 1.0, decimal_places: int = 6
) -> Optional[Dict[str, float]]:
    """
    Fetch FX rate from XE's convert_from API.

    Args:
        base: The target fiat currency code (e.g., "MXN").
              Interpreted as "convert FROM ref_fiat TO base".
        ref_fiat: The reference fiat currency code (e.g., "USD").
        amount: Reference amount to convert (default: 1.0).
        decimal_places: Number of decimal places for XE response (default: 6).

    Returns:
        A dict with keys:
            {
              "mid": <float>,
              "bid": <float>,  # equals mid if bid/ask not available
              "ask": <float>   # equals mid if bid/ask not available
            }
        or None on error / missing configuration.

    Notes:
        - Many XE plans return only "mid". This client maps bid/ask to mid.
        - Errors (network/format/auth) return None.
    """
    if not is_configured():
        return None

    endpoint = f"{XE_API_BASE_URL}/v1/convert_from.json"
    params: Dict[str, Any] = {
        "from": ref_fiat,
        "to": base,
        "amount": amount,
        "decimal_places": decimal_places,
    }

    try:
        resp = requests.get(
            endpoint,
            params=params,
            auth=(str(XE_API_ACCOUNT_ID), str(XE_API_KEY)),
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()

        # Expected shape: {"to": [{"quotecurrency": "<BASE>", "mid": <float>, ...}], ...}
        rows = payload.get("to") or []
        if not rows or not isinstance(rows, list):
            return None

        row = rows[0]
        mid = _safe_float(row.get("mid"))
        if mid is None:
            return None

        # If XE plan does not provide bid/offer in the response, map both to mid.
        bid = _safe_float(row.get("bid"))
        ask = _safe_float(row.get("ask"))
        bid = bid if bid is not None else mid
        ask = ask if ask is not None else mid

        return {"mid": mid, "bid": bid, "ask": ask}
    except requests.RequestException:
        return None
    except (ValueError, TypeError):
        return None


def _safe_float(val: Any) -> Optional[float]:
    """Try to convert to float, returning None on failure."""
    try:
        if val is None:
            return None
        return float(val)
    except (ValueError, TypeError):
        return None
