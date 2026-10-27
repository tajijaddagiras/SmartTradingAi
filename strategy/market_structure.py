"""
NexusTrade AI - Market Structure & Price Action Analyzer
Identifies Swing Highs, Swing Lows, Trend Structure (HH/HL vs LH/LL),
and Dynamic Support & Resistance levels.
"""

from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np


class MarketStructureAnalyzer:
    """Analyzes Price Action and Market Structure without lagging indicators."""

    @staticmethod
    def find_swings(df: pd.DataFrame, lookback: int = 5) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Detects Swing Highs and Swing Lows based on local extremes with lookback window.
        Returns: (swing_highs, swing_lows)
        """
        highs: List[Dict[str, Any]] = []
        lows: List[Dict[str, Any]] = []

        n = len(df)
        if n < (lookback * 2 + 1):
            return highs, lows

        high_series = df["high"].values
        low_series = df["low"].values
        time_series = df["time"].values

        for i in range(lookback, n - lookback):
            current_high = high_series[i]
            current_low = low_series[i]

            # Check if local peak
            is_peak = True
            for j in range(i - lookback, i + lookback + 1):
                if j < i and high_series[j] >= current_high:
                    is_peak = False
                    break
                elif j > i and high_series[j] > current_high:
                    is_peak = False
                    break

            if is_peak:
                highs.append({
                    "index": i,
                    "time": time_series[i],
                    "price": float(current_high)
                })

            # Check if local trough
            is_trough = True
            for j in range(i - lookback, i + lookback + 1):
                if j < i and low_series[j] <= current_low:
                    is_trough = False
                    break
                elif j > i and low_series[j] < current_low:
                    is_trough = False
                    break

            if is_trough:
                lows.append({
                    "index": i,
                    "time": time_series[i],
                    "price": float(current_low)
                })

        return highs, lows

    @staticmethod
    def analyze_structure(df: pd.DataFrame, lookback: int = 5) -> Dict[str, Any]:
        """
        Determines current structural bias: BULLISH, BEARISH, or RANGING.
        Maps dynamic Support and Resistance zones.
        """
        highs, lows = MarketStructureAnalyzer.find_swings(df, lookback=lookback)

        if len(highs) < 2 or len(lows) < 2:
            return {
                "bias": "NEUTRAL",
                "last_swing_high": None,
                "last_swing_low": None,
                "support_level": None,
                "resistance_level": None,
                "details": "Insufficient swings to confirm structure."
            }

        last_sh = highs[-1]["price"]
        prev_sh = highs[-2]["price"]
        last_sl = lows[-1]["price"]
        prev_sl = lows[-2]["price"]

        is_higher_high = last_sh > prev_sh
        is_higher_low = last_sl > prev_sl
        is_lower_high = last_sh < prev_sh
        is_lower_low = last_sl < prev_sl

        if is_higher_high and is_higher_low:
            bias = "BULLISH"
            details = f"Bullish Structure: Higher High ({last_sh:.5f} > {prev_sh:.5f}) & Higher Low ({last_sl:.5f} > {prev_sl:.5f})"
        elif is_lower_high and is_lower_low:
            bias = "BEARISH"
            details = f"Bearish Structure: Lower High ({last_sh:.5f} < {prev_sh:.5f}) & Lower Low ({last_sl:.5f} < {prev_sl:.5f})"
        else:
            bias = "RANGING"
            details = f"Ranging / Transition: Mixed swings (SH: {last_sh:.5f}, SL: {last_sl:.5f})"

        return {
            "bias": bias,
            "last_swing_high": last_sh,
            "prev_swing_high": prev_sh,
            "last_swing_low": last_sl,
            "prev_swing_low": prev_sl,
            "support_level": last_sl,
            "resistance_level": last_sh,
            "details": details
        }


market_structure_analyzer = MarketStructureAnalyzer()
