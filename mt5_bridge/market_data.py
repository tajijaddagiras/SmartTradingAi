"""
NexusTrade AI - MT5 Market Data Engine
Fetches historical candles (OHLCV), real-time ticks, and symbol specifications.
Converts raw MT5 structs into clean, typed Pandas DataFrames.
"""

import time
from typing import Optional, Dict, Any
import pandas as pd
import MetaTrader5 as mt5
from mt5_bridge.connector import mt5_connector
from core.logger import logger


TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}


class MarketDataProvider:
    """Provides market data ingestion from MT5 terminal into Pandas DataFrames."""

    def __init__(self, connector=mt5_connector):
        self.connector = connector

    def get_timeframe_constant(self, tf_str: str) -> int:
        """Converts string timeframe representation to MT5 constant."""
        tf = tf_str.upper().strip()
        if tf not in TIMEFRAME_MAP:
            raise ValueError(f"Unsupported timeframe: {tf_str}. Must be one of {list(TIMEFRAME_MAP.keys())}")
        return TIMEFRAME_MAP[tf]

    def get_candles(self, symbol: str, timeframe: str = "M15", count: int = 300) -> pd.DataFrame:
        """
        Fetches historical OHLCV candles as a Pandas DataFrame.
        Columns: ['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']
        """
        if not self.connector.ensure_connected():
            raise ConnectionError("MT5 disconnected while requesting candles.")

        if not self.connector.verify_symbol(symbol):
            raise ValueError(f"Symbol '{symbol}' is invalid or cannot be selected.")

        tf_const = self.get_timeframe_constant(timeframe)
        rates = None
        for attempt in range(3):
            rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, count)
            if rates is not None and len(rates) > 0:
                break
            time.sleep(0.2)

        if rates is None or len(rates) == 0:
            err_code, err_desc = mt5.last_error()
            logger.error(f"Failed to fetch rates for {symbol} ({timeframe}): Code {err_code} - {err_desc}")
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        # Ensure standard volume column: use real_volume if available, otherwise tick_volume
        df["volume"] = df["real_volume"] if (df["real_volume"] > 0).any() else df["tick_volume"]
        return df

    def get_current_tick(self, symbol: str) -> Dict[str, Any]:
        """Returns the latest Bid, Ask, Spread, and Last price for a symbol."""
        if not self.connector.ensure_connected():
            raise ConnectionError("MT5 disconnected while requesting tick.")

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            err_code, err_desc = mt5.last_error()
            raise RuntimeError(f"Failed to fetch tick for {symbol}: Code {err_code} - {err_desc}")

        sym_info = mt5.symbol_info(symbol)
        point = sym_info.point if sym_info else 0.00001
        spread_points = int(round((tick.ask - tick.bid) / point)) if point > 0 else 0

        return {
            "symbol": symbol,
            "bid": tick.bid,
            "ask": tick.ask,
            "last": tick.last,
            "spread_points": spread_points,
            "time": pd.to_datetime(tick.time, unit="s"),
            "volume": tick.volume,
        }

    def get_symbol_specs(self, symbol: str) -> Dict[str, Any]:
        """Returns trading specifications for a symbol (digits, point, lot step, min/max lot)."""
        if not self.connector.ensure_connected():
            raise ConnectionError("MT5 disconnected while requesting symbol specs.")

        info = mt5.symbol_info(symbol)
        if info is None:
            raise ValueError(f"Cannot get specs for symbol: {symbol}")

        return {
            "symbol": symbol,
            "digits": info.digits,
            "point": info.point,
            "spread": info.spread,
            "volume_min": info.volume_min,
            "volume_max": info.volume_max,
            "volume_step": info.volume_step,
            "trade_contract_size": info.trade_contract_size,
        }


# Global instance
market_data_provider = MarketDataProvider()
