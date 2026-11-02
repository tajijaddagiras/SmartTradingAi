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
    tp: Optional[float] = None
    mtf_info: Optional[Dict[str, Any]] = None


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

            # Calculate Server-Side Take Profit (TP)
            sl_distance = abs(current_price - hard_sl)
            res_target = structure.get("resistance_level")
            if res_target and (res_target - current_price) >= (1.5 * sl_distance):
                take_profit = res_target
            else:
                take_profit = current_price + (2.0 * sl_distance)

            rationale = " | ".join(buy_reasons)
            logger.info(f"🎯 [BUY CONFLUENCE CONFIRMED] {symbol} @ {current_price:.5f} | SL: {hard_sl:.5f} | TP: {take_profit:.5f} | {rationale}")
            return TradeSignal(
                action="BUY",
                symbol=symbol,
                price=current_price,
                sl=hard_sl,
                tp=take_profit,
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

            # Calculate Server-Side Take Profit (TP)
            sl_distance = abs(hard_sl - current_price)
            sup_target = structure.get("support_level")
            if sup_target and (current_price - sup_target) >= (1.5 * sl_distance):
                take_profit = sup_target
            else:
                take_profit = current_price - (2.0 * sl_distance)

            rationale = " | ".join(sell_reasons)
            logger.info(f"🎯 [SELL CONFLUENCE CONFIRMED] {symbol} @ {current_price:.5f} | SL: {hard_sl:.5f} | TP: {take_profit:.5f} | {rationale}")
            return TradeSignal(
                action="SELL",
                symbol=symbol,
                price=current_price,
                sl=hard_sl,
                tp=take_profit,
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
            tp=0.0,
            confluence_score=best_score,
            rationale=f"Confluence incomplete (Buy: {buy_score}/3, Sell: {sell_score}/3)",
            structure_bias=bias,
            has_ob=bool(active_bullish_ob or active_bearish_ob),
            has_volume_anomaly=has_volume_anomaly,
            ema_trend_aligned=ema_ok,
            structure_aligned=struct_ok,
            smc_aligned=smc_ok,
        )

    @staticmethod
    def detect_candlestick_pattern(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyzes the last 2-3 candles for institutional price action patterns:
        - Bullish/Bearish Pin Bar (Rejection Wick)
        - Bullish/Bearish Engulfing
        """
        if len(df) < 3:
            return {"pattern": "NONE", "bias": "NEUTRAL", "rejection": False}

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        c_open, c_high, c_low, c_close = float(curr["open"]), float(curr["high"]), float(curr["low"]), float(curr["close"])
        p_open, p_close = float(prev["open"]), float(prev["close"])

        total_range = c_high - c_low
        if total_range <= 0:
            return {"pattern": "NONE", "bias": "NEUTRAL", "rejection": False}

        body = abs(c_close - c_open)
        upper_wick = c_high - max(c_close, c_open)
        lower_wick = min(c_close, c_open) - c_low

        # 1. Bullish Pin Bar / Hammer (Long lower wick rejection at support)
        if lower_wick >= 1.8 * body and upper_wick <= 0.4 * body:
            return {"pattern": "BULLISH_PIN_BAR", "bias": "BULLISH", "rejection": True, "detail": "Strong Lower Wick Rejection"}

        # 2. Bearish Pin Bar / Shooting Star (Long upper wick rejection at resistance)
        if upper_wick >= 1.8 * body and lower_wick <= 0.4 * body:
            return {"pattern": "BEARISH_PIN_BAR", "bias": "BEARISH", "rejection": True, "detail": "Strong Upper Wick Rejection"}

        # 3. Bullish Engulfing (Current green body engulfs previous red body)
        if c_close > c_open and p_close < p_open and c_close > p_open and c_open < p_close:
            return {"pattern": "BULLISH_ENGULFING", "bias": "BULLISH", "rejection": False, "detail": "Full Bullish Engulfing"}

        # 4. Bearish Engulfing (Current red body engulfs previous green body)
        if c_close < c_open and p_close > p_open and c_close < p_open and c_open > p_close:
            return {"pattern": "BEARISH_ENGULFING", "bias": "BEARISH", "rejection": False, "detail": "Full Bearish Engulfing"}

        return {"pattern": "NORMAL_CANDLE", "bias": "NEUTRAL", "rejection": False}

    def evaluate_multi_timeframe(self, symbol: str) -> TradeSignal:
        """
        Performs Deep Multi-Timeframe Analysis across H4 (Macro), H1 (Structure), and M15/M5 (Trigger).
        Ensures the bot does not trade counter-trend against the macro trend.
        """
        from mt5_bridge.market_data import market_data_provider

        # 1. Fetch H4 (Macro Trend)
        h4_df = market_data_provider.get_candles(symbol, timeframe="H4", count=100)
        # 2. Fetch H1 (Structure)
        h1_df = market_data_provider.get_candles(symbol, timeframe="H1", count=150)
        # 3. Fetch M15 (Micro Entry & Candle Confirmation)
        m15_df = market_data_provider.get_candles(symbol, timeframe="M15", count=150)

        if h1_df.empty or len(h1_df) < 50:
            return TradeSignal(
                action="HOLD", symbol=symbol, price=0.0, sl=0.0, tp=0.0, confluence_score=0,
                rationale="Insufficient MTF data from broker.", structure_bias="UNKNOWN",
                has_ob=False, has_volume_anomaly=False, ema_trend_aligned=False
            )

        # Baseline single evaluation on primary H1
        base_signal = self.evaluate(symbol, h1_df)

        mtf_info: Dict[str, Any] = {
            "h4_bias": "NEUTRAL",
            "h1_bias": base_signal.structure_bias,
            "m15_pattern": "NONE",
            "mtf_aligned": False
        }

        # Check H4 Macro
        if not h4_df.empty and len(h4_df) >= 50:
            h4_ind = indicators.append_all_indicators(h4_df, ema_period=50)
            last_h4 = h4_ind.iloc[-1]
            h4_close = float(last_h4["close"])
            h4_ema = float(last_h4["ema_trend"])
            h4_bias = "BULLISH" if h4_close > h4_ema else "BEARISH"
            mtf_info["h4_bias"] = h4_bias

            # If base signal conflicts with H4 macro trend -> Downgrade signal to protect capital!
            if base_signal.action == "BUY" and h4_bias == "BEARISH":
                base_signal.action = "HOLD"
                base_signal.confluence_score = max(0, base_signal.confluence_score - 1)
                base_signal.rationale += " [MTF GUARD: Blocked by H4 Macro Downtrend]"
            elif base_signal.action == "SELL" and h4_bias == "BULLISH":
                base_signal.action = "HOLD"
                base_signal.confluence_score = max(0, base_signal.confluence_score - 1)
                base_signal.rationale += " [MTF GUARD: Blocked by H4 Macro Uptrend]"

        # Check M15 Micro Candlestick Trigger
        if not m15_df.empty:
            m15_pat = self.detect_candlestick_pattern(m15_df)
            mtf_info["m15_pattern"] = m15_pat["pattern"]
            if m15_pat["rejection"]:
                base_signal.rationale += f" | M15 Candle: {m15_pat['pattern']} ({m15_pat['detail']})"

        # Check if fully aligned
        if base_signal.action in ("BUY", "SELL") and mtf_info["h4_bias"] == ( "BULLISH" if base_signal.action == "BUY" else "BEARISH"):
            mtf_info["mtf_aligned"] = True
            base_signal.rationale = f"⭐ [MTF ALIGNED 4H+1H+15M] {base_signal.rationale}"

        base_signal.mtf_info = mtf_info
        return base_signal


confluence_engine = ConfluenceEngine()
