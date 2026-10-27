"""
NexusTrade AI - Technical Indicator Calculator
Provides vectorized calculations for EMA, ATR, Volume Moving Average, and Relative Volume.
"""

import pandas as pd
import numpy as np


class TechnicalIndicators:
    """Calculates quantitative indicators on OHLCV DataFrames."""

    @staticmethod
    def calculate_ema(df: pd.DataFrame, period: int = 50, column: str = "close") -> pd.Series:
        """Calculates Exponential Moving Average (EMA)."""
        return df[column].ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculates Average True Range (ATR).
        Measures market volatility to distinguish noise from genuine directional moves.
        """
        high = df["high"]
        low = df["low"]
        close_prev = df["close"].shift(1)

        tr1 = high - low
        tr2 = (high - close_prev).abs()
        tr3 = (low - close_prev).abs()

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        # Wilder's Smoothing / RMA for ATR
        atr = true_range.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
        return atr

    @staticmethod
    def calculate_volume_ma(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculates Simple Moving Average of Volume."""
        return df["volume"].rolling(window=period).mean()

    @staticmethod
    def append_all_indicators(
        df: pd.DataFrame,
        ema_period: int = 50,
        atr_period: int = 14,
        volume_ma_period: int = 20
    ) -> pd.DataFrame:
        """Appends all required confluence indicators to the candle dataframe."""
        df = df.copy()
        df["ema_trend"] = TechnicalIndicators.calculate_ema(df, period=ema_period)
        df["atr"] = TechnicalIndicators.calculate_atr(df, period=atr_period)
        df["volume_ma"] = TechnicalIndicators.calculate_volume_ma(df, period=volume_ma_period)
        df["rel_volume"] = df["volume"] / df["volume_ma"].replace(0, np.nan)
        return df


indicators = TechnicalIndicators()
