"""
Unit tests for NexusTrade AI Confluence Reasoning Engine.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from strategy.indicators import indicators
from strategy.market_structure import market_structure_analyzer
from strategy.smc_engine import smc_engine
from strategy.confluence import confluence_engine


class TestConfluenceEngine(unittest.TestCase):

    def _generate_synthetic_candles(
        self,
        trend: str = "bullish",
        n: int = 150,
        base_price: float = 1.1000,
        point_scale: float = 1.0
    ) -> pd.DataFrame:
        """Generates realistic synthetic OHLCV bars for test validation."""
        np.random.seed(42)
        start_time = datetime(2026, 1, 1, 9, 0)
        times = [start_time + timedelta(minutes=15 * i) for i in range(n)]

        opens, highs, lows, closes, volumes = [], [], [], [], []

        for i in range(n):
            # Strong sinusoidal wave for clear swing cycles
            wave = (0.0030 * point_scale) * np.sin(i / 4.0)
            drift = ((0.00005 * point_scale) * i) if trend == "bullish" else ((-0.00005 * point_scale) * i if trend == "bearish" else 0.0)

            cur_base = base_price + drift + wave
            o = cur_base
            c = o + ((0.0005 * point_scale) * np.cos(i / 4.0))
            h = max(o, c) + abs(np.random.normal(0, 0.0002 * point_scale)) + (0.0002 * point_scale)
            l = min(o, c) - abs(np.random.normal(0, 0.0002 * point_scale)) - (0.0002 * point_scale)
            v = int(np.random.uniform(500, 1500))
            if i in (100, 120, 140):
                v = int(v * 3.5)  # 3.5x volume spike

            opens.append(o)
            highs.append(h)
            lows.append(l)
            closes.append(c)
            volumes.append(v)

        return pd.DataFrame({
            "time": times,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
            "tick_volume": volumes,
            "real_volume": volumes,
            "spread": [10] * n,
        })

    def test_indicators_calculation(self):
        df = self._generate_synthetic_candles("bullish", 100)
        df_ind = indicators.append_all_indicators(df, ema_period=50, atr_period=14, volume_ma_period=20)

        self.assertIn("ema_trend", df_ind.columns)
        self.assertIn("atr", df_ind.columns)
        self.assertIn("volume_ma", df_ind.columns)
        self.assertIn("rel_volume", df_ind.columns)
        self.assertFalse(df_ind["atr"].iloc[-1] <= 0)

    def test_market_structure_bullish(self):
        df = self._generate_synthetic_candles("bullish", 120)
        structure = market_structure_analyzer.analyze_structure(df, lookback=5)
        self.assertIn(structure["bias"], ["BULLISH", "RANGING"])
        self.assertIsNotNone(structure["support_level"])

    def test_smc_volume_anomaly(self):
        df = self._generate_synthetic_candles("bullish", 150)
        df = indicators.append_all_indicators(df)
        anomaly = smc_engine.detect_volume_anomaly(df, multiplier=1.8, lookback_bars=20)
        self.assertTrue(anomaly["has_anomaly"])

    def test_confluence_evaluation_has_hard_sl(self):
        df = self._generate_synthetic_candles("bullish", 150)
        signal = confluence_engine.evaluate("EURUSD", df)

        self.assertIn(signal.action, ["BUY", "SELL", "HOLD"])
        # If any actionable order is emitted, Hard SL MUST be present and valid
        if signal.action == "BUY":
            self.assertGreater(signal.sl, 0.0)
            self.assertLess(signal.sl, signal.price)
        elif signal.action == "SELL":
            self.assertGreater(signal.sl, 0.0)
            self.assertGreater(signal.sl, signal.price)


if __name__ == "__main__":
    unittest.main()
