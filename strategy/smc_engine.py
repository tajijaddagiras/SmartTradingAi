"""
NexusTrade AI - Smart Money Concept (SMC) & Volume Anomaly Engine
Detects Institutional Footprints: Order Blocks (OB) and Volume Spikes at S/R zones.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np


class SMCEngine:
    """Identifies institutional Order Blocks and Volume Anomalies."""

    @staticmethod
    def detect_volume_anomaly(
        df: pd.DataFrame,
        multiplier: float = 1.8,
        lookback_bars: int = 3
    ) -> Dict[str, Any]:
        """
        Checks if any of the recent N bars exhibited an institutional volume spike
        (Volume >= multiplier * Volume_MA).
        """
        if len(df) < 25 or "volume_ma" not in df.columns:
            return {"has_anomaly": False, "ratio": 1.0, "bar_index": None}

        recent = df.iloc[-lookback_bars:]
        anomalies = recent[recent["volume"] >= (recent["volume_ma"] * multiplier)]

        if not anomalies.empty:
            last_anomaly = anomalies.iloc[-1]
            ratio = float(last_anomaly["volume"] / last_anomaly["volume_ma"])
            return {
                "has_anomaly": True,
                "ratio": round(ratio, 2),
                "bar_time": last_anomaly["time"],
                "bar_volume": float(last_anomaly["volume"]),
                "baseline_volume": float(last_anomaly["volume_ma"]),
            }

        curr_ratio = float(df["volume"].iloc[-1] / df["volume_ma"].iloc[-1]) if df["volume_ma"].iloc[-1] > 0 else 1.0
        return {"has_anomaly": False, "ratio": round(curr_ratio, 2), "bar_time": None}

    @staticmethod
    def find_order_blocks(
        df: pd.DataFrame,
        lookback: int = 50,
        displacement_atr_mult: float = 1.3
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scans recent history for Bullish and Bearish Order Blocks (OB).
        An Order Block is the last opposite candle before an aggressive expansion / displacement move.
        """
        bullish_obs: List[Dict[str, Any]] = []
        bearish_obs: List[Dict[str, Any]] = []

        if len(df) < lookback or "atr" not in df.columns:
            return {"bullish_obs": bullish_obs, "bearish_obs": bearish_obs}

        subset = df.iloc[-lookback:].reset_index(drop=True)
        n = len(subset)

        for i in range(1, n - 2):
            atr_val = subset.loc[i, "atr"]
            if np.isnan(atr_val) or atr_val <= 0:
                continue

            open_i = subset.loc[i, "open"]
            close_i = subset.loc[i, "close"]
            high_i = subset.loc[i, "high"]
            low_i = subset.loc[i, "low"]

            # Next 1-2 bars displacement
            next_close = subset.loc[i + 1, "close"]
            displacement_up = (next_close - open_i) >= (displacement_atr_mult * atr_val)
            displacement_down = (open_i - next_close) >= (displacement_atr_mult * atr_val)

            # 1. Bullish Order Block: Bearish candle (close < open) followed by strong bullish displacement
            if close_i < open_i and displacement_up:
                bullish_obs.append({
                    "type": "BULLISH_OB",
                    "time": subset.loc[i, "time"],
                    "top": float(max(open_i, close_i)),
                    "bottom": float(low_i),
                    "index": i,
                })

            # 2. Bearish Order Block: Bullish candle (close > open) followed by strong bearish displacement
            if close_i > open_i and displacement_down:
                bearish_obs.append({
                    "type": "BEARISH_OB",
                    "time": subset.loc[i, "time"],
                    "top": float(high_i),
                    "bottom": float(min(open_i, close_i)),
                    "index": i,
                })

        return {
            "bullish_obs": bullish_obs,
            "bearish_obs": bearish_obs,
        }

    @staticmethod
    def is_price_in_ob(
        current_price: float,
        obs: List[Dict[str, Any]],
        tolerance_atr: float = 0.2,
        atr_val: float = 0.001
    ) -> Optional[Dict[str, Any]]:
        """
        Checks if current market price is mitigating / touching any valid unviolated Order Block zone.
        """
        for ob in reversed(obs):  # Check most recent first
            buffer = tolerance_atr * atr_val
            if (ob["bottom"] - buffer) <= current_price <= (ob["top"] + buffer):
                return ob
        return None


smc_engine = SMCEngine()
