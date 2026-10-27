"""
NexusTrade AI - Spread & Liquidity Guard
Filters out hazardous market entries during abnormal spread widening,
news volatility spikes, or rollover illiquidity periods.
"""

from typing import Optional
from config.settings import AppConfig, load_config
from mt5_bridge.market_data import market_data_provider
from core.logger import logger


class SpreadGuard:
    """Verifies that current spread is within safe thresholds before entry."""

    def __init__(self, config: Optional[AppConfig] = None, market_data=market_data_provider):
        self.config = config or load_config()
        self.market_data = market_data

    @property
    def active_config(self) -> AppConfig:
        return self.config or load_config()

    def get_max_allowed_spread(self, symbol: str) -> int:
        """
        Returns appropriate max spread threshold based on asset class.
        Gold (XAUUSD) points are measured in $0.01 cents per ounce, where normal retail spread
        is 30-55 points ($0.30-$0.55). Forex pairs typically have 10-25 points (1.0-2.5 pips).
        """
        base_max = self.active_config.risk.max_spread_points
        sym_upper = symbol.upper()
        if "XAU" in sym_upper or "GOLD" in sym_upper:
            return max(base_max, 75)
        if "BTC" in sym_upper or "CRYPTO" in sym_upper:
            return max(base_max, 200)
        return base_max

    def is_spread_safe(self, symbol: str) -> bool:
        """
        Returns True if current spread is acceptable, False if spread is too wide.
        """
        try:
            tick = self.market_data.get_current_tick(symbol)
            spread_points = tick["spread_points"]
        except Exception as e:
            logger.warning(f"[SpreadGuard] Failed to retrieve tick for {symbol}: {e}")
            return False

        max_allowed = self.get_max_allowed_spread(symbol)
        if spread_points > max_allowed:
            logger.warning(
                f"[SpreadGuard] ⛔ Entry blocked for {symbol}! "
                f"Spread is {spread_points} points (Max allowed: {max_allowed} points). "
                f"Likely news volatility spike or low liquidity."
            )
            return False

        return True


# Global instance
spread_guard = SpreadGuard()
