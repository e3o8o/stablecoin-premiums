"""
Optional Eldorado client stub.

This module provides a best-effort, optional adapter for an Eldorado-like
public pricing endpoint. Since provider APIs and schemas vary (and may change),
the functions here are intentionally conservative, focusing on:

- Reading a base URL from environment/config (no secrets in code).
- Minimal HTTP request scaffolding with timeouts.
- A small normalization helper that attempts to extract BUY/SELL quotes from
  a plausible nested JSON structure (see example below).
- Defensive error handling that returns None on failure.

You should adapt this stub to the actual provider documentation you have.

Example of a plausible payload this stub can parse:
{
  "SELL": {
    "TRON-USDT": {
      "FIAT-ARS": { "price": "1010.50" },
      "FIAT-VES": { "price": "40.25" }
    }
  },
  "BUY": {
    "TRON-USDT": {
      "FIAT-ARS": { "price": "990.00" },
      "FIAT-VES": { "price": "39.10" }
    }
  }
}

In that case:
- base_code could be "FIAT-ARS"
- asset_code could be "TRON-USDT"
- side is "BUY" or "SELL"

If your provider uses a different shape, update _extract_price() accordingly.

Environment variables (loaded via package config when available):
- ELDORADO_API_BASE_URL (default: https://api.eldorado.com)
- REQUEST_TIMEOUT (default: 15.0)

Usage:
    from stablecoin_premiums.clients.eldorado import fetch_quote

    q = fetch_quote(base_code="FIAT-ARS", asset_code="TRON-USDT", side="SELL")
    if q:
        print(q)  # {'base': 'FIAT-ARS', 'asset': 'TRON-USDT', 'side': 'SELL', 'price': 1010.5}

Notes:
- Respect provider TOS and rate limits.
- This module performs unauthenticated GET requests to a configurable path.
- If your provider requires authentication, add it here without hardcoding secrets.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional

import requests  # type: ignore[import-untyped]

# Module-level type declarations
ELDORADO_API_BASE_URL: str
REQUEST_TIMEOUT: float

# Try to use shared package config; gracefully fall back to environment.
try:
    from stablecoin_premiums.config import (  # type: ignore
        ELDORADO_API_BASE_URL as _PKG_ELDORADO_BASE,
    )
    from stablecoin_premiums.config import (
        REQUEST_TIMEOUT as _PKG_TIMEOUT,  # type: ignore
    )

    ELDORADO_API_BASE_URL = _PKG_ELDORADO_BASE or "https://api.eldorado.com"
    REQUEST_TIMEOUT = float(_PKG_TIMEOUT or 15.0)
except Exception:
    ELDORADO_API_BASE_URL = (
        os.getenv("ELDORADO_API_BASE_URL") or "https://api.eldorado.com"
    )
    REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT") or "15.0")

# Public exports
__all__ = [
    "ELDORADO_API_BASE_URL",
    "is_configured",
    "fetch_prices_raw",
    "fetch_quote",
    "fetch_all_quotes",
]


def is_configured() -> bool:
    """
    Returns True if a base URL appears configured; False otherwise.
    """
    return bool(ELDORADO_API_BASE_URL)


def _join_url(path: str) -> str:
    """
    Join base URL and path safely.
    """
    base = ELDORADO_API_BASE_URL.rstrip("/")
    if not path:
        return base
    if not path.startswith("/"):
        path = "/" + path
    return base + path


def fetch_prices_raw(
    path: str = "/prices", params: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Perform a GET request to the Eldorado pricing endpoint and return JSON.

    Args:
        path: URL path appended to ELDORADO_API_BASE_URL (default: "/prices").
        params: Optional query parameters.

    Returns:
        Parsed JSON dict on success; None on network/HTTP/parse errors.
    """
    if not is_configured():
        return None

    url = _join_url(path)
    try:
        resp = requests.get(url, params=params or {}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            return data
        # Some providers may return a list; adapt as needed.
        return None
    except requests.RequestException:
        return None
    except ValueError:
        # JSON parse error
        return None


def _extract_price(
    payload: Dict[str, Any],
    base_code: str,
    asset_code: str,
    side: str,
) -> Optional[float]:
    """
    Attempt to extract a float price from a plausible nested dict structure:

    Expected pattern (example):
        payload[side][asset_code][base_code]["price"] -> str|float

    Returns:
        float price if found and valid; None otherwise.
    """
    try:
        side_layer = payload.get(side)
        if not isinstance(side_layer, dict):
            return None
        asset_layer = side_layer.get(asset_code)
        if not isinstance(asset_layer, dict):
            return None
        base_layer = asset_layer.get(base_code)
        if not isinstance(base_layer, dict):
            return None
        raw_price = base_layer.get("price")
        if raw_price is None:
            return None
        return float(raw_price)
    except (TypeError, ValueError):
        return None


def fetch_quote(
    base_code: str,
    asset_code: str,
    side: str,
    *,
    path: str = "/prices",
    params: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Fetch a single quote (BUY or SELL) for a given base_code and asset_code.

    Args:
        base_code: Provider-specific fiat key (e.g., "FIAT-ARS").
        asset_code: Provider-specific asset pair (e.g., "TRON-USDT").
        side: "BUY" or "SELL".
        path: Optional endpoint path (default "/prices").
        params: Optional query parameters.

    Returns:
        Normalized dict: {"base": str, "asset": str, "side": str, "price": float}
        or None if not found/not parseable.
    """
    side = side.upper()
    if side not in {"BUY", "SELL"}:
        return None

    data = fetch_prices_raw(path=path, params=params)
    if not data:
        return None

    price = _extract_price(data, base_code=base_code, asset_code=asset_code, side=side)
    if price is None:
        return None

    return {"base": base_code, "asset": asset_code, "side": side, "price": price}


def fetch_all_quotes(
    base_codes: Iterable[str],
    asset_code: str,
    sides: Iterable[str] = ("BUY", "SELL"),
    *,
    path: str = "/prices",
    params: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch and normalize quotes for multiple bases and sides.

    Args:
        base_codes: Iterable of base codes (e.g., ["FIAT-ARS", "FIAT-VES"]).
        asset_code: Asset identifier (e.g., "TRON-USDT").
        sides: Iterable of sides to fetch (default: ("BUY", "SELL")).
        path: Optional endpoint path.
        params: Optional query parameters.

    Returns:
        A list of normalized quotes: [{"base","asset","side","price"}, ...]
        Skips entries that cannot be parsed.
    """
    results: List[Dict[str, Any]] = []
    data = fetch_prices_raw(path=path, params=params)
    if not data:
        return results

    sides_up = [s.upper() for s in sides if s]
    for base_code in base_codes:
        for side in sides_up:
            price = _extract_price(
                data, base_code=base_code, asset_code=asset_code, side=side
            )
            if price is not None:
                results.append(
                    {
                        "base": base_code,
                        "asset": asset_code,
                        "side": side,
                        "price": price,
                    }
                )
    return results
