"""
NexusTrade AI - Triple-Confluence Reasoning Engine
Validates trade setups based on the intersection (confluence) of:
1. Market Structure (HH/HL or LH/LL & Dynamic S/R)
2. Volume Anomaly & Smart Money Concept Order Blocks (OB)
3. Technical Filters (EMA 50 Trend Alignment & ATR Volatility)
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import pandas as pd
from config.settings import AppConfig, load_config
from strategy.indicators import indicators
from strategy.market_structure import market_structure_analyzer
from strategy.smc_engine import smc_engine
from core.logger import logger


@dataclass
class TradeSignal:
    action: str              # "BUY", "SELL", or "HOLD"
    symbol: str
    price: float
    sl: float
    confluence_score: int    # e.g., 3 out of 3
    rationale: str
    structure_bias: str
    has_ob: bool
    has_volume_anomaly: bool
    ema_trend_aligned: bool
    structure_aligned: bool = False
    smc_aligned: bool = False


class ConfluenceEngine:
    """The central decision brain for NexusTrade AI."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()

    def evaluate(self, symbol: str, raw_df: pd.DataFrame) -> TradeSignal:
        """
        Evaluates candle data through the 3-factor confluence matrix.
        Returns a validated TradeSignal.
        """
        if len(raw_df) < 60:
            return TradeSignal(
                action="HOLD",
                symbol=symbol,
                price=0.0,
                sl=0.0,
                confluence_score=0,
                rationale="Insufficient candles for confluence analysis.",
                structure_bias="UNKNOWN",
                has_ob=False,
                has_volume_anomaly=False,
                ema_trend_aligned=False,
            )

        cfg = self.config.confluence

        # 1. Append Technical Indicators (EMA, ATR, Volume MA)
        df = indicators.append_all_indicators(
            raw_df,
            ema_period=cfg.ema_trend_period,
            atr_period=cfg.atr_period,
            volume_ma_period=cfg.volume_ma_period,
        )

        last_bar = df.iloc[-1]
        current_price = float(last_bar["close"])
        ema_val = float(last_bar["ema_trend"])
        atr_val = float(last_bar["atr"])

        # 2. Factor 1: Market Structure (Price Action)
        structure = market_structure_analyzer.analyze_structure(df, lookback=cfg.swing_lookback)
        bias = structure["bias"]

        # 3. Factor 2: SMC Order Blocks & Volume Anomaly
        obs = smc_engine.find_order_blocks(df)
        volume_check = smc_engine.detect_volume_anomaly(df, multiplier=cfg.volume_spike_multiplier)
        has_volume_anomaly = volume_check["has_anomaly"]

        # Check if price is currently inside an Order Block
        active_bullish_ob = smc_engine.is_price_in_ob(current_price, obs["bullish_obs"], atr_val=atr_val)
        active_bearish_ob = smc_engine.is_price_in_ob(current_price, obs["bearish_obs"], atr_val=atr_val)

        # 4. Factor 3: Technical Trend & Volatility Filter
        # Trend check: Price > EMA 50 for BUY, Price < EMA 50 for SELL
        ema_bullish = current_price > ema_val
        ema_bearish = current_price < ema_val

        # --- CONFLUENCE VALIDATION: BUY ---
        # 1. Structure must be BULLISH (or testing dynamic support)
        # 2. Bullish Order Block present OR high volume rejection at support
        # 3. Price above EMA 50
        # --- CONFLUENCE VALIDATION: BUY ---
        # Factor 1: Structure must be BULLISH (or testing dynamic support)
        f1_buy = (bias == "BULLISH") or bool(structure["support_level"] and abs(current_price - structure["support_level"]) <= 1.5 * atr_val)
        # Factor 2: Bullish Order Block present OR high volume rejection at demand
        f2_buy = bool(active_bullish_ob or (has_volume_anomaly and current_price > last_bar["open"]))
        # Factor 3: Price above EMA 50
        f3_buy = bool(ema_bullish)

        buy_reasons = []
        if f1_buy:
            buy_reasons.append(f"Structure: {bias} (Near Support: {structure['support_level']})")
        if f2_buy:
            ob_info = f"Bullish OB [{active_bullish_ob['bottom']:.5f} - {active_bullish_ob['top']:.5f}]" if active_bullish_ob else "Volume Spike At Demand"
            buy_reasons.append(f"SMC: {ob_info}")
        if f3_buy:
            buy_reasons.append(f"Trend: Price ({current_price:.5f}) > EMA{cfg.ema_trend_period} ({ema_val:.5f})")
        buy_score = int(f1_buy) + int(f2_buy) + int(f3_buy)

        # --- CONFLUENCE VALIDATION: SELL ---
        # Factor 1: Structure must be BEARISH (or testing dynamic resistance)
        f1_sell = (bias == "BEARISH") or bool(structure["resistance_level"] and abs(current_price - structure["resistance_level"]) <= 1.5 * atr_val)
        # Factor 2: Bearish Order Block present OR high volume rejection at supply
        f2_sell = bool(active_bearish_ob or (has_volume_anomaly and current_price < last_bar["open"]))
        # Factor 3: Price below EMA 50
        f3_sell = bool(ema_bearish)

        sell_reasons = []
        if f1_sell:
            sell_reasons.append(f"Structure: {bias} (Near Resistance: {structure['resistance_level']})")
        if f2_sell:
            ob_info = f"Bearish OB [{active_bearish_ob['bottom']:.5f} - {active_bearish_ob['top']:.5f}]" if active_bearish_ob else "Volume Spike At Supply"
            sell_reasons.append(f"SMC: {ob_info}")
        if f3_sell:
            sell_reasons.append(f"Trend: Price ({current_price:.5f}) < EMA{cfg.ema_trend_period} ({ema_val:.5f})")
        sell_score = int(f1_sell) + int(f2_sell) + int(f3_sell)

        # Decision threshold: Configurable minimum score (default 3, or 2 for aggressive/testing)
        cfg_active = load_config().confluence
        min_score = getattr(cfg_active, "min_confluence_score", 3)

        if buy_score >= min_score:
            # Calculate Server-Side Hard SL
            ref_low = active_bullish_ob["bottom"] if active_bullish_ob else (structure["support_level"] or current_price)
            hard_sl = ref_low - (cfg.atr_multiplier_sl * atr_val)

            rationale = " | ".join(buy_reasons)
            logger.info(f"🎯 [BUY CONFLUENCE CONFIRMED] {symbol} @ {current_price:.5f} | SL: {hard_sl:.5f} | {rationale}")
            return TradeSignal(
                action="BUY",
                symbol=symbol,
                price=current_price,
                sl=hard_sl,
                confluence_score=buy_score,
                rationale=rationale,
                structure_bias=bias,
                has_ob=bool(active_bullish_ob),
                has_volume_anomaly=has_volume_anomaly,
                ema_trend_aligned=f3_buy,
                structure_aligned=f1_buy,
                smc_aligned=f2_buy,
            )

        elif sell_score >= min_score:
            # Calculate Server-Side Hard SL
            ref_high = active_bearish_ob["top"] if active_bearish_ob else (structure["resistance_level"] or current_price)
            hard_sl = ref_high + (cfg.atr_multiplier_sl * atr_val)

            rationale = " | ".join(sell_reasons)
            logger.info(f"🎯 [SELL CONFLUENCE CONFIRMED] {symbol} @ {current_price:.5f} | SL: {hard_sl:.5f} | {rationale}")
            return TradeSignal(
                action="SELL",
                symbol=symbol,
                price=current_price,
                sl=hard_sl,
                confluence_score=sell_score,
                rationale=rationale,
                structure_bias=bias,
                has_ob=bool(active_bearish_ob),
                has_volume_anomaly=has_volume_anomaly,
                ema_trend_aligned=f3_sell,
                structure_aligned=f1_sell,
                smc_aligned=f2_sell,
            )

        # No full confluence -> HOLD
        # Determine dominant direction to ensure factor badges strictly match confluence score
        is_buy_dominant = (buy_score > sell_score) or (buy_score == sell_score and ema_bullish)
        if is_buy_dominant:
            best_score = buy_score
            struct_ok = f1_buy
            smc_ok = f2_buy
            ema_ok = f3_buy
        else:
            best_score = sell_score
            struct_ok = f1_sell
            smc_ok = f2_sell
            ema_ok = f3_sell

        return TradeSignal(
            action="HOLD",
            symbol=symbol,
            price=current_price,
            sl=0.0,
            confluence_score=best_score,
            rationale=f"Confluence incomplete (Buy: {buy_score}/3, Sell: {sell_score}/3)",
            structure_bias=bias,
            has_ob=bool(active_bullish_ob or active_bearish_ob),
            has_volume_anomaly=has_volume_anomaly,
            ema_trend_aligned=ema_ok,
            structure_aligned=struct_ok,
            smc_aligned=smc_ok,
        )


confluence_engine = ConfluenceEngine()
