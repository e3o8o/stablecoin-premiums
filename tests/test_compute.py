"""Tests for stablecoin_premiums.compute module."""

import pytest
from stablecoin_premiums.compute import (
    Premiums,
    compute_premium,
    compute_premiums,
    compute_spread,
)


class TestPremiums:
    """Test Premiums dataclass."""

    def test_premiums_creation(self):
        """Test Premiums dataclass can be created with valid values."""
        premiums = Premiums(
            stablecoin_sell_premium=10.5,
            stablecoin_buy_premium=9.2,
            stablecoin_buy_sell_spread=-1.3,
        )
        assert premiums.stablecoin_sell_premium == 10.5
        assert premiums.stablecoin_buy_premium == 9.2
        assert premiums.stablecoin_buy_sell_spread == -1.3

    def test_to_dict(self):
        """Test to_dict method returns correct dictionary."""
        premiums = Premiums(
            stablecoin_sell_premium=10.5,
            stablecoin_buy_premium=9.2,
            stablecoin_buy_sell_spread=-1.3,
        )
        result = premiums.to_dict()
        expected = {
            "stablecoin_sell_premium": 10.5,
            "stablecoin_buy_premium": 9.2,
            "stablecoin_buy_sell_spread": -1.3,
        }
        assert result == expected


class TestComputePremium:
    """Test compute_premium function."""

    def test_compute_premium_positive_values(self):
        """Test compute_premium with positive values."""
        result = compute_premium(18.95, 17.12)
        expected = (18.95 / 17.12 - 1) * 100
        assert result == pytest.approx(expected)

    def test_compute_premium_zero_denominator(self):
        """Test compute_premium raises ValueError with zero denominator."""
        with pytest.raises(ValueError, match="denominator_rate must be > 0"):
            compute_premium(18.95, 0.0)

    def test_compute_premium_negative_numerator(self):
        """Test compute_premium raises ValueError with negative numerator."""
        with pytest.raises(ValueError, match="numerator_rate must be > 0"):
            compute_premium(-18.95, 17.12)

    def test_compute_premium_negative_denominator(self):
        """Test compute_premium raises ValueError with negative denominator."""
        with pytest.raises(ValueError, match="denominator_rate must be > 0"):
            compute_premium(18.95, -17.12)


class TestComputeSpread:
    """Test compute_spread function."""

    def test_compute_spread_positive_values(self):
        """Test compute_spread with positive values."""
        result = compute_spread(18.70, 18.95)
        expected = ((18.70 - 18.95) / 18.95) * 100
        assert result == pytest.approx(expected)

    def test_compute_spread_zero_sell_rate(self):
        """Test compute_spread raises ValueError with zero sell rate."""
        with pytest.raises(ValueError, match="sell_rate must be > 0"):
            compute_spread(18.70, 0.0)

    def test_compute_spread_negative_buy_rate(self):
        """Test compute_spread raises ValueError with negative buy rate."""
        with pytest.raises(ValueError, match="buy_rate must be > 0"):
            compute_spread(-18.70, 18.95)

    def test_compute_spread_negative_sell_rate(self):
        """Test compute_spread raises ValueError with negative sell rate."""
        with pytest.raises(ValueError, match="sell_rate must be > 0"):
            compute_spread(18.70, -18.95)


class TestComputePremiums:
    """Test compute_premiums function."""

    def test_compute_premiums_valid_inputs(self):
        """Test compute_premiums with valid inputs."""
        result = compute_premiums(
            sell_rate=18.95,
            buy_rate=18.70,
            fx_bid=17.12,
            fx_ask=17.12,
        )
        assert isinstance(result, Premiums)
        assert result.stablecoin_sell_premium == pytest.approx(10.69364161849711)
        assert result.stablecoin_buy_premium == pytest.approx(9.243697478991614)
        assert result.stablecoin_buy_sell_spread == pytest.approx(-1.3184584178498851)

    def test_compute_premiums_with_rounding(self):
        """Test compute_premiums with decimal rounding."""
        result = compute_premiums(
            sell_rate=18.95,
            buy_rate=18.70,
            fx_bid=17.12,
            fx_ask=17.12,
            decimals=2,
        )
        assert result.stablecoin_sell_premium == pytest.approx(10.69)
        assert result.stablecoin_buy_premium == pytest.approx(9.24)
        assert result.stablecoin_buy_sell_spread == pytest.approx(-1.32)

    def test_compute_premiums_zero_sell_rate(self):
        """Test compute_premiums raises ValueError with zero sell rate."""
        with pytest.raises(ValueError, match="sell_rate must be > 0"):
            compute_premiums(
                sell_rate=0.0,
                buy_rate=18.70,
                fx_bid=17.12,
                fx_ask=17.12,
            )

    def test_compute_premiums_negative_fx_bid(self):
        """Test compute_premiums raises ValueError with negative fx_bid."""
        with pytest.raises(ValueError, match="fx_bid must be > 0"):
            compute_premiums(
                sell_rate=18.95,
                buy_rate=18.70,
                fx_bid=-17.12,
                fx_ask=17.12,
            )
