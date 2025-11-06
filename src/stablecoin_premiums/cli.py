#!/usr/bin/env python3
"""
CLI entrypoint for the stablecoin_premiums package.

Quickly fetch P2P stablecoin quotes (Binance), reference FX rates (XE),
and compute premiums/spreads for one or more fiat currencies.

Examples:
    # Default (MXN if no DEFAULT_FIATS provided in .env)
    python -m stablecoin_premiums.cli

    # Specify a single fiat
    python -m stablecoin_premiums.cli --fiats MXN

    # Multiple fiats (comma-separated or repeated)
    python -m stablecoin_premiums.cli --fiats MXN,BRL,ARS
    python -m stablecoin_premiums.cli --fiats MXN --fiats BRL --fiats ARS

    # Use a different asset or reference fiat
    python -m stablecoin_premiums.cli --asset USDT --ref-fiat USD

    # Pretty JSON output
    python -m stablecoin_premiums.cli --output json --pretty

    # CSV output
    python -m stablecoin_premiums.cli --output csv

Notes:
- Set XE_API_ACCOUNT_ID and XE_API_KEY (see .env.example) to get FX rates.
- You can set DEFAULT_FIATS in your .env to a comma-separated list (e.g., "MXN,BRL,ARS").
- Never commit your .env file.

License: MIT
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from typing import Any, Dict, List, Optional

from .clients.binance import average_price
from .clients.xe import fetch_fx_rate
from .compute import compute_premiums
from .config import (
    DEFAULT_ASSET,
    DEFAULT_FIATS,
    LOG_LEVEL,
    REF_FIAT,
    load_dotenv_if_present,
)


def _setup_logging(level: Optional[str] = None) -> None:
    lvl = (level or LOG_LEVEL or "INFO").upper()
    try:
        numeric = getattr(logging, lvl)
    except AttributeError:
        numeric = logging.INFO
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _parse_fiats(cli_fiats: List[str]) -> List[str]:
    """
    Merge CLI-provided fiats and DEFAULT_FIATS from env config into a list.
    Accepts repeated --fiats flags and/or a single comma-separated string.
    Falls back to ['MXN'] if none provided.
    """
    fiats: List[str] = []
    for entry in cli_fiats:
        if not entry:
            continue
        parts = [p.strip() for p in entry.split(",") if p.strip()]
        fiats.extend(parts)

    if not fiats and DEFAULT_FIATS:
        fiats = DEFAULT_FIATS[:]  # from env

    if not fiats:
        fiats = ["MXN"]

    # Deduplicate preserving order
    seen = set()
    ordered: List[str] = []
    for f in fiats:
        if f not in seen:
            ordered.append(f)
            seen.add(f)
    return ordered


def _collect_for_fiat(
    fiat: str,
    asset: str,
    ref_fiat: str,
    min_valid_ads: Optional[int] = None,
    decimals: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Fetch BUY/SELL P2P quotes and FX for a single fiat, then compute premiums.
    Returns a result dict with either computed fields or an 'error' key.
    """
    logger = logging.getLogger("stablecoin_premiums.cli")
    result: Dict[str, Any] = {"fiat": fiat, "asset": asset, "ref_fiat": ref_fiat}

    buy = average_price(fiat, asset, "BUY", min_valid_ads=min_valid_ads)
    sell = average_price(fiat, asset, "SELL", min_valid_ads=min_valid_ads)
    fx = fetch_fx_rate(fiat, ref_fiat)

    result["buy_rate"] = buy
    result["sell_rate"] = sell
    result["fx"] = fx

    if buy is None or sell is None:
        result["error"] = "insufficient_p2p_data"
        logger.debug("Insufficient P2P data for %s/%s", fiat, asset)
        return result

    if not fx:
        result["error"] = "insufficient_fx_data"
        logger.debug("Insufficient FX data for %s/%s", fiat, ref_fiat)
        return result

    try:
        premiums = compute_premiums(
            sell_rate=sell,
            buy_rate=buy,
            fx_bid=fx["bid"],
            fx_ask=fx["ask"],
            decimals=decimals,
        )
        result.update(premiums.to_dict())
        result["status"] = "ok"
    except Exception as exc:
        result["error"] = f"compute_error: {exc}"
        logger.debug("Compute error for %s: %s", fiat, exc)

    return result


def _print_json(rows: List[Dict[str, Any]], pretty: bool) -> None:
    if pretty:
        json.dump(rows, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        json.dump(rows, sys.stdout, separators=(",", ":"), ensure_ascii=False)
        sys.stdout.write("\n")


def _print_csv(rows: List[Dict[str, Any]]) -> None:
    """
    Print a CSV with stable columns. If some fields are missing in rows,
    the CSV will still include the full header, leaving blanks as needed.
    """
    # Define a stable header
    fieldnames = [
        "fiat",
        "asset",
        "ref_fiat",
        "sell_rate",
        "buy_rate",
        "fx.bid",
        "fx.ask",
        "stablecoin_sell_premium",
        "stablecoin_buy_premium",
        "stablecoin_buy_sell_spread",
        "status",
        "error",
    ]
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()

    for r in rows:
        row = {
            "fiat": r.get("fiat"),
            "asset": r.get("asset"),
            "ref_fiat": r.get("ref_fiat"),
            "sell_rate": r.get("sell_rate"),
            "buy_rate": r.get("buy_rate"),
            "fx.bid": (r.get("fx") or {}).get("bid")
            if isinstance(r.get("fx"), dict)
            else None,
            "fx.ask": (r.get("fx") or {}).get("ask")
            if isinstance(r.get("fx"), dict)
            else None,
            "stablecoin_sell_premium": r.get("stablecoin_sell_premium"),
            "stablecoin_buy_premium": r.get("stablecoin_buy_premium"),
            "stablecoin_buy_sell_spread": r.get("stablecoin_buy_sell_spread"),
            "status": r.get("status"),
            "error": r.get("error"),
        }
        writer.writerow(row)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="stablecoin-premiums",
        description="Fetch P2P quotes and FX rates to compute stablecoin premiums.",
    )
    parser.add_argument(
        "--fiats",
        action="append",
        default=[],
        help="Fiat codes (comma-separated or repeated). Defaults to DEFAULT_FIATS or MXN.",
    )
    parser.add_argument(
        "--asset",
        default=DEFAULT_ASSET or "USDT",
        help=f"Stablecoin asset (default: {DEFAULT_ASSET or 'USDT'})",
    )
    parser.add_argument(
        "--ref-fiat",
        default=REF_FIAT or "USD",
        help=f"Reference fiat for FX (default: {REF_FIAT or 'USD'})",
    )
    parser.add_argument(
        "--min-valid-ads",
        type=int,
        default=None,
        help="Require at least this many valid P2P ads; otherwise mark insufficient data.",
    )
    parser.add_argument(
        "--decimals",
        type=int,
        default=None,
        help="Round computed outputs to this many decimals.",
    )
    parser.add_argument(
        "--output",
        choices=["json", "csv"],
        default="json",
        help="Output format (default: json).",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    parser.add_argument(
        "--dotenv",
        action="store_true",
        help="Attempt to load a local .env before running.",
    )
    parser.add_argument(
        "--log-level",
        default=LOG_LEVEL or "INFO",
        help=f"Logging level (default: {LOG_LEVEL or 'INFO'})",
    )

    args = parser.parse_args(argv)

    if args.dotenv:
        # Best-effort .env load; ignore if python-dotenv not installed.
        load_dotenv_if_present()

    _setup_logging(args.log_level)

    fiats = _parse_fiats(args.fiats)
    rows: List[Dict[str, Any]] = []
    for fiat in fiats:
        rows.append(
            _collect_for_fiat(
                fiat=fiat,
                asset=args.asset,
                ref_fiat=args.ref_fiat,
                min_valid_ads=args.min_valid_ads,
                decimals=args.decimals,
            )
        )

    if args.output == "json":
        _print_json(rows, pretty=args.pretty)
    else:
        _print_csv(rows)

    # Return non-zero if any row had an error
    any_error = any(r.get("error") for r in rows)
    return 1 if any_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
