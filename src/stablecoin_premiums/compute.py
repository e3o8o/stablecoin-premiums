"""
Premium computation utilities for stablecoin_premiums.

This module provides small, well-documented helpers to compute:
- Stablecoin sell premium vs. reference FX bid
- Stablecoin buy premium vs. reference FX ask
- Buy–sell spread between P2P quotes

All functions operate on plain floats and return either floats or a typed
container. Inputs are assumed to be quoted in the same fiat units.

Definitions
-----------
Let:
- sell_rate: the price at which a user SELLS the stablecoin (i.e., obtains fiat)
- buy_rate:  the price at which a user BUYS the stablecoin (i.e., pays fiat)
- fx_bid:    reference bid rate for fiat (e.g., USD->local) used for SELL comparison
- fx_ask:    reference ask rate for fiat (e.g., USD->local) used for BUY comparison

Then:
    stablecoin_sell_premium (%) = ((sell_rate / fx_bid) - 1) * 100
    stablecoin_buy_premium  (%) = ((buy_rate  / fx_ask) - 1) * 100
    stablecoin_buy_sell_spread (%) = ((buy_rate - sell_rate) / sell_rate) * 100

Safety
------
- All inputs must be positive real numbers. Zero or negative values raise ValueError.
- Use `decimals` in `compute_premiums` to round outputs or leave as full-precision floats.

Example
-------
    from stablecoin_premiums.compute import compute_premiums

    res = compute_premiums(sell_rate=18.95, buy_rate=18.70, fx_bid=17.12, fx_ask=17.12)
    print(res.to_dict())
    # {
    #   'stablecoin_sell_premium': 10.69364161849711,
    #   'stablecoin_buy_premium': 9.243697478991614,
    #   'stablecoin_buy_sell_spread': -1.3184584178498851
    # }

License
-------
MIT
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

__all__ = [
    "Premiums",
    "compute_premium",
    "compute_spread",
    "compute_premiums",
]


@dataclass(frozen=True)
class Premiums:
    """
    Container for premium and spread outputs.

    Attributes:
        stablecoin_sell_premium: Premium (%) comparing sell_rate to fx_bid.
        stablecoin_buy_premium:  Premium (%) comparing buy_rate to fx_ask.
        stablecoin_buy_sell_spread: Relative spread (%) from sell to buy.
    """

    stablecoin_sell_premium: float
    stablecoin_buy_premium: float
    stablecoin_buy_sell_spread: float

    def to_dict(self) -> dict:
        """Return a plain dict representation of the premiums."""
        return asdict(self)


def _validate_positive(name: str, value: float) -> None:
    """
    Ensure `value` is a positive float.

    Raises:
        ValueError: if value is None, not a number, or <= 0.
    """
    if value is None:
        raise ValueError(f"{name} must not be None")
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    if v <= 0:
        raise ValueError(f"{name} must be > 0; got {v}")


def compute_premium(numerator_rate: float, denominator_rate: float) -> float:
    """
    Compute premium percentage as ((numerator_rate / denominator_rate) - 1) * 100.

    Args:
        numerator_rate: Observed market rate (e.g., P2P sell or buy quote).
        denominator_rate: Reference rate (e.g., FX bid/ask).

    Returns:
        Premium as a percentage (float), not rounded.

    Raises:
        ValueError: if any input is non-positive.
    """
    _validate_positive("numerator_rate", numerator_rate)
    _validate_positive("denominator_rate", denominator_rate)
    return (numerator_rate / denominator_rate - 1.0) * 100.0


def compute_spread(buy_rate: float, sell_rate: float) -> float:
    """
    Compute the relative buy–sell spread as ((buy_rate - sell_rate) / sell_rate) * 100.

    Args:
        buy_rate: Price at which a user BUYS the stablecoin.
        sell_rate: Price at which a user SELLS the stablecoin.

    Returns:
        Spread percentage (float), not rounded.

    Raises:
        ValueError: if any input is non-positive.
    """
    _validate_positive("buy_rate", buy_rate)
    _validate_positive("sell_rate", sell_rate)
    return ((buy_rate - sell_rate) / sell_rate) * 100.0


def _maybe_round(value: float, decimals: Optional[int]) -> float:
    """
    Round `value` to `decimals` if provided, else return as-is.
    """
    if decimals is None:
        return value
    return round(value, int(decimals))


def compute_premiums(
    *,
    sell_rate: float,
    buy_rate: float,
    fx_bid: float,
    fx_ask: float,
    decimals: Optional[int] = None,
) -> Premiums:
    """
    Compute stablecoin premiums vs. reference FX and the buy–sell spread.

    Args:
        sell_rate: Stablecoin SELL quote in fiat units (user receives fiat).
        buy_rate: Stablecoin BUY quote in fiat units (user pays fiat).
        fx_bid: Reference FX bid rate (e.g., USD->local) for SELL comparison.
        fx_ask: Reference FX ask rate (e.g., USD->local) for BUY comparison.
        decimals: Optional number of decimal places to round outputs.

    Returns:
        Premiums: dataclass with three percentage metrics.

    Raises:
        ValueError: if any input is non-positive.
    """
    # Validate inputs
    _validate_positive("sell_rate", sell_rate)
    _validate_positive("buy_rate", buy_rate)
    _validate_positive("fx_bid", fx_bid)
    _validate_positive("fx_ask", fx_ask)

    # Compute raw metrics
    sell_premium = compute_premium(sell_rate, fx_bid)
    buy_premium = compute_premium(buy_rate, fx_ask)
    spread = compute_spread(buy_rate, sell_rate)

    # Optional rounding
    sell_premium = _maybe_round(sell_premium, decimals)
    buy_premium = _maybe_round(buy_premium, decimals)
    spread = _maybe_round(spread, decimals)

    return Premiums(
        stablecoin_sell_premium=sell_premium,
        stablecoin_buy_premium=buy_premium,
        stablecoin_buy_sell_spread=spread,
    )
