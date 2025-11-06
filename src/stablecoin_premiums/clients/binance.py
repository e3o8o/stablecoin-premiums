"""
Binance P2P client for fetching and averaging USDT quotes against local fiat.

This module queries the Binance C2C (P2P) public endpoint to get BUY/SELL ads
for a given fiat and asset, filters for validity, and computes an average price
from the top ads.

Usage:
    from stablecoin_premiums.clients.binance import average_price

    # Average BUY price (user buys USDT)
    buy_avg = average_price(fiat="MXN", asset="USDT", trade_type="BUY")

    # Average SELL price (user sells USDT)
    sell_avg = average_price(fiat="MXN", asset="USDT", trade_type="SELL")

Notes:
- This uses a public, undocumented endpoint; stability is not guaranteed.
- Respect rate limits and the provider's terms of service.
- Tune timeouts/retries via environment (see stablecoin_premiums.config).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import requests  # type: ignore[import-untyped]

# Module-level type declarations
REQUEST_TIMEOUT: float
MAX_RETRIES: int
RETRY_SLEEP: float

try:
    # Optional import from the package config (preferred if available).
    from ..config import MAX_RETRIES, REQUEST_TIMEOUT, RETRY_SLEEP
except Exception:
    # Fallback defaults if package config isn't available.
    REQUEST_TIMEOUT = 15.0
    MAX_RETRIES = 3
    RETRY_SLEEP = 5.0


BINANCE_P2P_SEARCH_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"

# Minimal headers to avoid trivial blocking due to missing User-Agent, etc.
DEFAULT_HEADERS = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; stablecoin-premiums/0.1; +https://github.com/)",
}


def _valid_ad(ad: Dict[str, Any]) -> bool:
    """
    Basic validation of a single Binance P2P advertisement payload.

    Returns:
        True if the ad contains a positive price and sensible min/max trade limits.
    """
    try:
        adv = ad.get("adv", {})
        price = float(adv["price"])
        min_amt = float(adv.get("minSingleTransAmount", 0))
        max_amt = float(adv.get("maxSingleTransAmount", 1e18))

        if price <= 0:
            return False
        if min_amt < 0 or max_amt <= 0:
            return False
        if min_amt > max_amt:
            return False
        return True
    except Exception:
        return False


def _fetch_ads(
    fiat: str,
    asset: str,
    trade_type: str,
    rows: int = 20,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
    retry_sleep: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch raw advertisements from Binance P2P for the given fiat/asset/trade_type.

    Args:
        fiat: Fiat currency code used on Binance P2P (e.g., "MXN", "BRL").
        asset: Crypto asset code (e.g., "USDT").
        trade_type: "BUY" or "SELL".
        rows: Number of rows Binance should return (default 20).
        headers: Optional HTTP headers; falls back to DEFAULT_HEADERS.
        timeout: Request timeout (seconds); defaults to REQUEST_TIMEOUT.
        max_retries: Max request retries; defaults to MAX_RETRIES.
        retry_sleep: Seconds to sleep between retries; defaults to RETRY_SLEEP.

    Returns:
        A list of raw ads (dicts) as returned by Binance (empty on failure).
    """
    _headers = headers or DEFAULT_HEADERS
    _timeout = timeout if timeout is not None else REQUEST_TIMEOUT
    _retries = max_retries if max_retries is not None else MAX_RETRIES
    _sleep = retry_sleep if retry_sleep is not None else RETRY_SLEEP

    payload = {
        "fiat": fiat,
        "page": 1,
        "rows": rows,
        "asset": asset,
        "tradeType": trade_type,
        "payTypes": [],
        "countries": [],
    }

    for attempt in range(_retries):
        try:
            resp = requests.post(
                BINANCE_P2P_SEARCH_URL,
                headers=_headers,
                json=payload,
                timeout=_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", []) or []
        except requests.RequestException:
            if attempt < _retries - 1:
                time.sleep(_sleep)
            else:
                return []
        except Exception:
            # Unexpected shape or parsing error; treat as no data
            return []
    return []


def average_price(
    fiat: str,
    asset: str,
    trade_type: str,
    *,
    rows: int = 20,
    take_top: int = 5,
    average_last_n: int = 3,
    min_valid_ads: Optional[int] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
    retry_sleep: Optional[float] = None,
) -> Optional[float]:
    """
    Compute an average price from the top P2P ads after validation and sorting.

    The algorithm:
      1) Fetch up to `rows` ads for (fiat, asset, trade_type).
      2) Filter for basic validity (_valid_ad).
      3) Sort ascending by price.
      4) Take the top `take_top` ads.
      5) Average the "last" `average_last_n` entries among those top ads
         (i.e., a "trimmed" approach favoring the best quotes among valid top ads).

    Args:
        fiat: Binance P2P fiat code (e.g., "MXN", "BRL").
        asset: Asset ticker (e.g., "USDT").
        trade_type: "BUY" (user buys USDT) or "SELL" (user sells USDT).
        rows: Number of rows to request from the endpoint (default: 20).
        take_top: Consider only the best N ads (default: 5).
        average_last_n: Among those top N, average the last M (default: 3).
        min_valid_ads: If provided, abort and return None unless at least this many valid ads are found.
        headers: Optional override for HTTP headers.
        timeout: Request timeout in seconds.
        max_retries: Number of retries on network errors.
        retry_sleep: Delay between retries in seconds.

    Returns:
        The averaged price as a float, or None if insufficient/invalid data.
    """
    # Fetch ads
    ads = _fetch_ads(
        fiat=fiat,
        asset=asset,
        trade_type=trade_type,
        rows=rows,
        headers=headers,
        timeout=timeout,
        max_retries=max_retries,
        retry_sleep=retry_sleep,
    )
    if not ads:
        return None

    # Filter and sort by price
    valid_ads = [ad for ad in ads if _valid_ad(ad)]
    if min_valid_ads is not None and len(valid_ads) < min_valid_ads:
        return None

    try:
        valid_ads.sort(key=lambda a: float(a["adv"]["price"]))
    except Exception:
        return None

    # Select top subset
    top_ads = valid_ads[: max(take_top, 0)]
    if len(top_ads) < max(average_last_n, 1):
        return None

    # Extract prices and compute the trimmed average of the "last" average_last_n
    try:
        top_prices = [float(ad["adv"]["price"]) for ad in top_ads]
        # Example: top 5 ads -> average last 3: top_prices[-3:]
        to_average = top_prices[-average_last_n:]
        if not to_average:
            return None
        return sum(to_average) / float(len(to_average))
    except Exception:
        return None
