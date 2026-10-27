"""
NexusTrade AI - Historical Backtest Engine (Fase 1 Uji Kelayakan)
Simulates the Confluence Engine, Server-Side Hard SL, and Smart Trailing
on historical candle data without future lookahead bias.
"""

from typing import Optional, Dict, Any, List
import pandas as pd
from config.settings import AppConfig, load_config
from strategy.confluence import confluence_engine
from strategy.indicators import indicators
from backtest.metrics import metrics_calculator
from core.logger import logger


class BacktestRunner:
    """Simulates trading logic on historical OHLCV data."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()

    def run(
        self,
        symbol: str,
        df: pd.DataFrame,
        initial_capital: float = 10000.0,
        fixed_lot: float = 0.1,
        spread_points: int = 15,
        point: float = 0.00001,
        contract_size: float = 100000.0
    ) -> Dict[str, Any]:
        """
        Executes historical bar-by-bar simulation.
        """
        if len(df) < 100:
            raise ValueError("Insufficient candle history for backtesting (requires >= 100 bars).")

        cfg = self.config
        
        # Adjust contract size: Forex = 100,000 units, Gold (XAUUSD) = 100 oz
        symbol_upper = symbol.upper()
        if "XAU" in symbol_upper or "GOLD" in symbol_upper:
            contract_size = 100.0
            point = 0.01
            spread_cash = spread_points * point * contract_size * fixed_lot
        else:
            spread_cash = spread_points * point * contract_size * fixed_lot

        # Append indicators across dataset
        df = indicators.append_all_indicators(
            df,
            ema_period=cfg.confluence.ema_trend_period,
            atr_period=cfg.confluence.atr_period,
            volume_ma_period=cfg.confluence.volume_ma_period,
        )

        trades: List[Dict[str, Any]] = []
        active_trade: Optional[Dict[str, Any]] = None

        logger.info(f"Starting historical backtest for {symbol} on {len(df)} bars...")

        # Walk-forward iteration bar by bar
        for i in range(60, len(df)):
            curr_bar = df.iloc[i]
            high = curr_bar["high"]
            low = curr_bar["low"]
            close = curr_bar["close"]
            time_val = curr_bar["time"]

            # 1. Manage Active Position (Trailing Stop & Hard SL)
            if active_trade is not None:
                pos_type = active_trade["type"]
                current_sl = active_trade["sl"]
                open_price = active_trade["entry_price"]
                atr_val = curr_bar["atr"] if not pd.isna(curr_bar["atr"]) else 0.001

                # Check if Hard SL was hit during this bar
                sl_hit = False
                exit_price = current_sl

                if pos_type == "BUY":
                    if low <= current_sl:
                        sl_hit = True
                        exit_price = current_sl
                    else:
                        # Smart Trailing Stop update
                        activation_dist = cfg.smart_trailing.activation_atr_multiple * atr_val
                        trail_step_dist = cfg.smart_trailing.trail_step_atr_multiple * atr_val
                        if (close - open_price) >= activation_dist:
                            candidate_sl = close - trail_step_dist
                            if candidate_sl > current_sl:
                                active_trade["sl"] = candidate_sl

                elif pos_type == "SELL":
                    if high >= current_sl:
                        sl_hit = True
                        exit_price = current_sl
                    else:
                        # Smart Trailing Stop update
                        activation_dist = cfg.smart_trailing.activation_atr_multiple * atr_val
                        trail_step_dist = cfg.smart_trailing.trail_step_atr_multiple * atr_val
                        if (open_price - close) >= activation_dist:
                            candidate_sl = close + trail_step_dist
                            if candidate_sl < current_sl:
                                active_trade["sl"] = candidate_sl

                # Check dynamic exit (Volume Exhaustion)
                vol_ratio = (curr_bar["volume"] / curr_bar["volume_ma"]) if curr_bar["volume_ma"] > 0 else 1.0
                dynamic_exit = False
                if cfg.smart_trailing.dynamic_exit_volume_exhaustion and vol_ratio <= cfg.smart_trailing.volume_exhaustion_ratio:
                    if pos_type == "BUY" and (close - open_price) > 0:
                        dynamic_exit = True
                        exit_price = close
                    elif pos_type == "SELL" and (open_price - close) > 0:
                        dynamic_exit = True
                        exit_price = close

                # Close trade if triggered
                if sl_hit or dynamic_exit:
                    if pos_type == "BUY":
                        price_diff = exit_price - open_price
                    else:
                        price_diff = open_price - exit_price

                    gross_pnl = price_diff * contract_size * fixed_lot
                    net_pnl = gross_pnl - spread_cash

                    trades.append({
                        "symbol": symbol,
                        "type": pos_type,
                        "entry_time": active_trade["entry_time"],
                        "exit_time": time_val,
                        "entry_price": open_price,
                        "exit_price": exit_price,
                        "pnl": net_pnl,
                        "exit_reason": "SL_OR_TRAIL" if sl_hit else "DYNAMIC_EXIT_VOLUME",
                    })
                    active_trade = None
                    continue

            # 2. Look for New Entries if Flat
            if active_trade is None:
                historical_slice = df.iloc[: i + 1]
                signal = confluence_engine.evaluate(symbol, historical_slice)

                if signal.action in ("BUY", "SELL"):
                    entry_price = close + (spread_points * point if signal.action == "BUY" else 0.0)
                    active_trade = {
                        "symbol": symbol,
                        "type": signal.action,
                        "entry_price": entry_price,
                        "sl": signal.sl,
                        "entry_time": time_val,
                        "rationale": signal.rationale,
                    }

        # Calculate performance metrics
        results = metrics_calculator.calculate(trades, initial_capital=initial_capital)
        self._print_report(symbol, results)
        return results

    def _print_report(self, symbol: str, metrics: Dict[str, Any]) -> None:
        """Prints a clean institutional performance card."""
        logger.info("=" * 65)
        logger.info(f"   📊 BACKTEST RESULTS — {symbol}")
        logger.info("=" * 65)
        logger.info(f"   Initial Capital:     ${metrics['initial_capital']:,.2f}")
        logger.info(f"   Final Equity:        ${metrics['final_equity']:,.2f}")
        logger.info(f"   Net Profit:          ${metrics['net_profit']:,.2f} ({metrics['return_pct']}%)")
        logger.info(f"   Total Trades:        {metrics['total_trades']} (Wins: {metrics['win_count']}, Losses: {metrics['loss_count']})")
        logger.info(f"   Win Rate:            {metrics['win_rate']}%")
        logger.info(f"   Profit Factor:       {metrics['profit_factor']}")
        logger.info(f"   Max Drawdown:        ${metrics['max_drawdown_cash']:,.2f} ({metrics['max_drawdown_pct']}%)")
        logger.info(f"   Risk:Reward Ratio:   1:{metrics['risk_reward_ratio']}")
        logger.info(f"   Trade Expectancy:    ${metrics['expectancy']:,.2f} / trade")
        logger.info("=" * 65)


backtest_runner = BacktestRunner()
