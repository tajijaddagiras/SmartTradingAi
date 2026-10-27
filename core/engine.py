"""
NexusTrade AI - Core Engine Orchestrator
Coordinates MT5 heartbeat, Anti-Sleep power locking, Daily Drawdown Circuit Breaker,
Confluence Reasoning, Position Sizing, and Smart Trailing execution loops.
"""

import time
import signal
import sys
from typing import Optional
from config.settings import AppConfig, load_config
from mt5_bridge.connector import mt5_connector
from mt5_bridge.market_data import market_data_provider
from mt5_bridge.executor import order_executor
from risk.drawdown_limiter import drawdown_limiter
from risk.lot_calculator import lot_calculator
from risk.spread_guard import spread_guard
from strategy.confluence import confluence_engine
from strategy.smart_trailing import smart_trailing_manager
from core.anti_sleep import anti_sleep_manager
from core.logger import logger


class NexusTradeEngine:
    """The central runtime engine running locally on the user's computer."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()
        self.running = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Hooks system termination signals for graceful, safe shutdown."""
        def handler(sig, frame):
            logger.warning("\nShutdown signal received. Stopping NexusTrade AI gracefully...")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def start(self) -> None:
        """Launches the automated trading engine loop."""
        self.config = load_config()
        logger.info("=" * 60)
        logger.info("   🚀 Starting NexusTrade AI Engine (Local Autonomous Mode)")
        logger.info(f"   Mode: {self.config.system.mode.upper()} | Timeframe: {self.config.trading.timeframe}")
        logger.info(f"   Symbols: {', '.join(self.config.trading.symbols)}")
        logger.info(f"   Max Daily Drawdown: {self.config.risk.max_daily_drawdown_percent}%")
        logger.info(f"   Server-Side Hard SL: MANDATORY ENFORCED")
        logger.info("=" * 60)

        # 1. Connect to MT5
        if not mt5_connector.initialize():
            logger.critical("Engine startup failed: Could not connect to MetaTrader 5.")
            return

        self.running = True
        loop_interval = self.config.system.loop_interval_seconds

        try:
            while self.running:
                self._run_iteration()
                time.sleep(loop_interval)
        except Exception as e:
            logger.critical(f"Unhandled exception in core engine loop: {e}", exc_info=True)
        finally:
            self.stop()

    def _run_iteration(self) -> None:
        """Executes a single cycle of the trading system."""
        # Step 0: Dynamically reload latest configuration for real-time symbol sync
        self.config = load_config()

        # Step 1: Ensure MT5 connection is active
        if not mt5_connector.ensure_connected():
            logger.warning("Waiting for MT5 connection to restore...")
            return

        # Step 2: Check Daily Drawdown Circuit Breaker
        is_safe = drawdown_limiter.check_drawdown()
        if not is_safe:
            logger.warning(f"Trading halted today: {drawdown_limiter.freeze_reason}")
            # Still process existing positions for trailing/exits, but do not scan for new trades
            self._manage_active_positions()
            return

        # Step 3: Manage Active Trades (Dynamic Exit + Smart Trailing)
        open_positions = self._manage_active_positions()

        # Step 4: Handle Anti-Sleep OS Daemon
        if open_positions:
            anti_sleep_manager.prevent_sleep()
        else:
            anti_sleep_manager.allow_sleep()

        # Step 5: Check Max Concurrent Positions Limit
        max_positions = self.config.risk.max_open_positions
        if len(open_positions) >= max_positions:
            logger.debug(f"Position limit reached ({len(open_positions)}/{max_positions}). Skipping new entries.")
            return

        # Step 6: Scan pairs for intelligent layering & 3-Factor Confluence
        max_layers = getattr(self.config.risk, "max_layers_per_symbol", 3)
        for symbol in self.config.trading.symbols:
            # Check how many layers are already open on this specific symbol
            symbol_positions = [p for p in open_positions if p["symbol"] == symbol]
            if len(symbol_positions) >= max_layers:
                continue

            # Check if total open positions would exceed max allowed
            if len(open_positions) >= max_positions:
                break

            try:
                self._scan_symbol_setup(symbol, symbol_positions)
            except Exception as e:
                logger.error(f"Error scanning setup for {symbol}: {e}", exc_info=True)

    def _manage_active_positions(self) -> list:
        """Updates trailing stops and dynamic exits for all active trades."""
        positions = order_executor.get_open_positions()
        if positions:
            smart_trailing_manager.process_open_positions()
        return positions

    def _scan_symbol_setup(self, symbol: str, existing_positions: Optional[list] = None) -> None:
        """Evaluates a single pair for institutional entry confluence and intelligent layering."""
        existing_positions = existing_positions or []

        # 1. Spread Check
        if not spread_guard.is_spread_safe(symbol):
            return

        # 2. Fetch Candle Data
        tf = self.config.trading.timeframe
        raw_df = market_data_provider.get_candles(symbol, timeframe=tf, count=250)
        if raw_df.empty:
            return

        # 3. Evaluate 3-Factor Confluence Matrix
        signal = confluence_engine.evaluate(symbol, raw_df)
        if signal.action not in ("BUY", "SELL"):
            return

        # 4. Intelligent Trader Layering Guard (Smart Spacing & Auto-Reversal)
        if existing_positions:
            existing_type = existing_positions[0]["type"]
            if signal.action != existing_type:
                logger.info(
                    f"🔄 [AUTO-REVERSAL] {symbol} active {existing_type} layer conflicts with fresh {signal.action} confluence! "
                    f"Auto-liquidating {len(existing_positions)} opposite {existing_type} positions before flipping to {signal.action}..."
                )
                order_executor.close_all_positions(symbol=symbol, reason=f"Auto-Reversal {existing_type} -> {signal.action}")
                time.sleep(0.5)
                existing_positions = []
            else:
                # B. Smart Price Distance Spacing: Only enforced if min_dist_atr > 0
                min_dist_atr = getattr(self.config.risk, "min_layer_distance_atr", 0.0)
                if min_dist_atr > 0:
                    atr_val = 0.0010
                    if "atr" in raw_df.columns and not raw_df["atr"].dropna().empty:
                        atr_val = float(raw_df["atr"].dropna().iloc[-1])

                    min_required_dist = min_dist_atr * atr_val
                    closest_dist = min(abs(signal.price - p["price_open"]) for p in existing_positions)
                    if closest_dist < min_required_dist:
                        logger.debug(
                            f"[LayerGuard] {symbol} Layer skipped: Current price {signal.price:.5f} "
                            f"is too close ({closest_dist:.5f}) to an existing layer. Min required distance: {min_required_dist:.5f}."
                        )
                        return

        max_layers = getattr(self.config.risk, "max_layers_per_symbol", 3)
        layers_needed = max_layers - len(existing_positions)
        if layers_needed <= 0:
            return

        all_open = order_executor.get_open_positions()
        available_slots = max(0, self.config.risk.max_open_positions - len(all_open))
        to_open = min(layers_needed, available_slots)
        if to_open <= 0:
            return

        # 5. Calculate Risk-Adjusted Lot Size
        lot = lot_calculator.calculate_lot(symbol, signal.price, signal.sl)

        # 6. Execute Orders for all configured layers
        for i in range(to_open):
            curr_layer = len(existing_positions) + i + 1
            rationale_with_layer = f"Layer {curr_layer}/{max_layers} | {signal.rationale}"
            ticket = order_executor.open_order(
                symbol=symbol,
                action=signal.action,
                lot=lot,
                sl=signal.sl,
                rationale=rationale_with_layer
            )
            if ticket:
                logger.info(
                    f"✨ Layer #{curr_layer}/{max_layers} (Trade #{ticket}) initiated on {symbol} "
                    f"({signal.action}) @ {signal.price:.5f} based on active confluence!"
                )

    def emergency_flat(self) -> None:
        """Manually trigger emergency liquidation of all positions."""
        logger.warning("[EMERGENCY] Triggering Flat Before Close...")
        order_executor.close_all_positions(reason="Manual Emergency Flat")
        anti_sleep_manager.allow_sleep()

    def stop(self, disconnect_mt5: bool = False) -> None:
        """Gracefully halts the engine loop and restores OS power management."""
        self.running = False
        anti_sleep_manager.allow_sleep()
        if disconnect_mt5:
            mt5_connector.shutdown()
        logger.info("NexusTrade AI engine loop has stopped.")


nexus_engine = NexusTradeEngine()
