"""
NexusTrade AI - Smart Trailing & Dynamic Exit Engine
Implements 'Let Profits Run' philosophy:
- No rigid Take Profit; trails SL dynamically along ATR or Swing zones.
- Dynamic Exit: Closes position early if Volume Exhaustion or Structural Break occurs.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
from config.settings import AppConfig, load_config
from mt5_bridge.executor import order_executor
from mt5_bridge.market_data import market_data_provider
from strategy.indicators import indicators
from strategy.market_structure import market_structure_analyzer
from core.logger import logger


class SmartTrailingManager:
    """Manages active trades with dynamic trailing stops and early exhaustion exits."""

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        executor=order_executor,
        market_data=market_data_provider
    ):
        self.config = config or load_config()
        self.executor = executor
        self.market_data = market_data

    def check_dynamic_exit(
        self,
        position: Dict[str, Any],
        df: pd.DataFrame
    ) -> bool:
        """
        Evaluates whether an open position should be closed early due to:
        1. Volume Exhaustion (volume drying up during trend extension).
        2. Structural Break against the trade exceeding ATR tolerance.
        Returns True if position was dynamically closed, False otherwise.
        """
        trail_cfg = self.config.smart_trailing
        if not trail_cfg.dynamic_exit_volume_exhaustion or len(df) < 30:
            return False

        last_bar = df.iloc[-1]
        prev_bar = df.iloc[-2]
        current_volume = float(last_bar["volume"])
        avg_volume = float(last_bar["volume_ma"]) if "volume_ma" in df.columns else 1.0
        atr_val = float(last_bar["atr"]) if "atr" in df.columns else 0.001

        ticket = position["ticket"]
        pos_type = position["type"]
        pos_profit = position["profit"]

        # Only trigger dynamic exit if position is already in profit or breakeven
        if pos_profit <= 0:
            return False

        # --- 1. Volume Exhaustion Check ---
        # If price pushed to a new local high/low but volume collapsed (< ratio * baseline)
        vol_ratio = (current_volume / avg_volume) if avg_volume > 0 else 1.0
        if vol_ratio <= trail_cfg.volume_exhaustion_ratio:
            # Check if pushing extreme
            if pos_type == "BUY" and last_bar["high"] >= prev_bar["high"]:
                reason = f"Dynamic Exit: Volume Exhaustion ({vol_ratio:.2f}x of avg volume at local high)"
                logger.warning(f"⚡ [DYNAMIC EXIT] Closing #{ticket} ({position['symbol']}): {reason}")
                return self.executor.close_position(ticket, reason=reason)

            elif pos_type == "SELL" and last_bar["low"] <= prev_bar["low"]:
                reason = f"Dynamic Exit: Volume Exhaustion ({vol_ratio:.2f}x of avg volume at local low)"
                logger.warning(f"⚡ [DYNAMIC EXIT] Closing #{ticket} ({position['symbol']}): {reason}")
                return self.executor.close_position(ticket, reason=reason)

        # --- 2. Structural Break Check ---
        structure = market_structure_analyzer.analyze_structure(df, lookback=self.config.confluence.swing_lookback)
        current_price = position["price_current"]

        if pos_type == "BUY":
            # If structure shifted to BEARISH or breached support by > 0.8 * ATR
            if structure["bias"] == "BEARISH" and structure["support_level"]:
                if current_price < (structure["support_level"] - (0.8 * atr_val)):
                    reason = f"Dynamic Exit: Bullish Structure Broken into Bearish ({current_price:.5f} < {structure['support_level']:.5f})"
                    logger.warning(f"⚡ [DYNAMIC EXIT] Closing #{ticket} ({position['symbol']}): {reason}")
                    return self.executor.close_position(ticket, reason=reason)

        elif pos_type == "SELL":
            # If structure shifted to BULLISH or breached resistance by > 0.8 * ATR
            if structure["bias"] == "BULLISH" and structure["resistance_level"]:
                if current_price > (structure["resistance_level"] + (0.8 * atr_val)):
                    reason = f"Dynamic Exit: Bearish Structure Broken into Bullish ({current_price:.5f} > {structure['resistance_level']:.5f})"
                    logger.warning(f"⚡ [DYNAMIC EXIT] Closing #{ticket} ({position['symbol']}): {reason}")
                    return self.executor.close_position(ticket, reason=reason)

        return False

    def update_trailing_stop(
        self,
        position: Dict[str, Any],
        df: pd.DataFrame
    ) -> bool:
        """
        Calculates and modifies server-side trailing stop for an open position.
        Rule: Stop Loss ONLY moves closer to profit; NEVER widens.
        """
        trail_cfg = self.config.smart_trailing
        if not trail_cfg.enabled or len(df) < 20:
            return False

        last_bar = df.iloc[-1]
        atr_val = float(last_bar["atr"]) if "atr" in df.columns else 0.001
        if atr_val <= 0:
            return False

        ticket = position["ticket"]
        pos_type = position["type"]
        open_price = position["price_open"]
        current_price = position["price_current"]
        current_sl = position["sl"]

        activation_dist = trail_cfg.activation_atr_multiple * atr_val
        trail_step_dist = trail_cfg.trail_step_atr_multiple * atr_val

        if pos_type == "BUY":
            profit_dist = current_price - open_price
            # Check if profit exceeded activation threshold
            if profit_dist >= activation_dist:
                candidate_sl = current_price - trail_step_dist
                # Only raise Stop Loss (lock in more profit)
                if candidate_sl > current_sl + (0.1 * atr_val):
                    return self.executor.modify_sl(ticket, candidate_sl)

        elif pos_type == "SELL":
            profit_dist = open_price - current_price
            # Check if profit exceeded activation threshold
            if profit_dist >= activation_dist:
                candidate_sl = current_price + trail_step_dist
                # Only lower Stop Loss (lock in more profit)
                if current_sl == 0.0 or candidate_sl < current_sl - (0.1 * atr_val):
                    return self.executor.modify_sl(ticket, candidate_sl)

        return False

    def process_open_positions(self) -> None:
        """
        Main inspection loop for all active positions:
        Runs Dynamic Exit checks and Smart Trailing SL updates.
        """
        positions = self.executor.get_open_positions()
        if not positions:
            return

        timeframe = self.config.trading.timeframe
        for pos in positions:
            symbol = pos["symbol"]
            try:
                raw_df = self.market_data.get_candles(symbol, timeframe=timeframe, count=100)
                if raw_df.empty:
                    continue

                df = indicators.append_all_indicators(
                    raw_df,
                    ema_period=self.config.confluence.ema_trend_period,
                    atr_period=self.config.confluence.atr_period,
                    volume_ma_period=self.config.confluence.volume_ma_period
                )

                # 1. First check if dynamic exit condition is met
                closed_early = self.check_dynamic_exit(pos, df)
                if closed_early:
                    continue

                # 2. Otherwise update smart trailing stop
                self.update_trailing_stop(pos, df)

            except Exception as e:
                logger.error(f"[SmartTrailing] Error processing position #{pos['ticket']} ({symbol}): {e}")


smart_trailing_manager = SmartTrailingManager()
