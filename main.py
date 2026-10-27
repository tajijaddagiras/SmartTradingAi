"""
NexusTrade AI - Desktop Automated Trading System
Entry point for running locally on Windows/macOS.
Supports CLI autonomous engine, Web-Desktop Zen Dashboard, and Backtest modes.
"""

import sys
import argparse
from colorama import Fore, Style
from config.settings import load_config
from core.engine import nexus_engine
from mt5_bridge.connector import mt5_connector
from mt5_bridge.market_data import market_data_provider
from backtest.backtest_runner import backtest_runner
from core.logger import logger


BANNER = f"""
{Fore.CYAN}{Style.BRIGHT}
  ███╗   ██╗███████╗██╗   ██╗██╗   ██╗███████╗████████╗██████╗  █████╗ ██████╗ ███████╗
  ████╗  ██║██╔════╝╚██╗ ██╔╝██║   ██║██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝
  ██╔██╗ ██║█████╗   ╚████╔╝ ██║   ██║███████╗   ██║   ██████╔╝███████║██║  ██║█████╗  
  ██║╚██╗██║██╔══╝    ╚██╔╝  ██║   ██║╚════██║   ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝  
  ██║ ╚████║███████╗   ██║   ╚██████╔╝███████║   ██║   ██║  ██║██║  ██║██████╔╝███████╗
  ╚═╝  ╚═══╝╚══════╝   ╚═╝    ╚═════╝ ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝
                                  A I   T R A D I N G   E N G I N E
{Style.RESET_ALL}
  {Fore.GREEN}● Architecture:{Style.RESET_ALL} 100% Local Execution (No VPS Required)
  {Fore.GREEN}● Confluence:{Style.RESET_ALL}   Price Action (HH/HL) + SMC Order Blocks + Volume Anomaly + EMA/ATR
  {Fore.GREEN}● Safety:{Style.RESET_ALL}       Server-Side Hard SL + Anti-Sleep Daemon + Daily Drawdown Limiter
  {Fore.GREEN}● Exit System:{Style.RESET_ALL}  Dynamic Smart Trailing & Volume Exhaustion ('Let Profits Run')
  {Fore.GREEN}● Interface:{Style.RESET_ALL}    Zen Desktop Dashboard (http://127.0.0.1:8899)
---------------------------------------------------------------------------------------------
"""


def free_port_if_in_use(port: int = 8899) -> None:
    """Terminates any abandoned prior Python process listening on target port."""
    import socket, subprocess, os, time
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            in_use = (s.connect_ex(("127.0.0.1", port)) == 0)
        if in_use:
            out = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True).decode()
            for line in out.strip().splitlines():
                parts = line.split()
                if len(parts) >= 5 and "LISTENING" in parts:
                    pid = int(parts[-1])
                    if pid != os.getpid():
                        logger.info(f"Port {port} is occupied by prior instance (PID {pid}). Freeing port...")
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                        time.sleep(1)
    except Exception as e:
        logger.warning(f"Could not automatically free port {port}: {e}")


def main():
    parser = argparse.ArgumentParser(description="NexusTrade AI Automated Trading System")
    parser.add_argument("--ui", "--dashboard", action="store_true", help="Launch the Zen Desktop Web Dashboard on http://127.0.0.1:8899")
    parser.add_argument("--flat-now", action="store_true", help="Instantly liquidate all open positions (Flat Before Close)")
    parser.add_argument("--status", action="store_true", help="Check MT5 terminal connection and account summary")
    parser.add_argument("--backtest", action="store_true", help="Execute historical strategy simulation")
    parser.add_argument("--symbol", type=str, default="EURUSD", help="Symbol for backtest (default: EURUSD)")
    parser.add_argument("--bars", type=int, default=500, help="Number of historical candles for backtest (default: 500)")
    parser.add_argument("--port", type=int, default=8899, help="Port for the UI dashboard (default: 8899)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host interface for the UI dashboard (default: 0.0.0.0)")
    args = parser.parse_args()

    print(BANNER)

    cfg = load_config()

    # Mode 1: UI Dashboard Mode
    if args.ui:
        free_port_if_in_use(args.port)
        from ui.server import start_ui_server
        logger.info(f"Starting Zen Desktop Dashboard at http://{args.host}:{args.port}...")
        start_ui_server(host=args.host, port=args.port)
        return

    # Mode 2: Emergency Flat All
    if args.flat_now:
        logger.warning("Initiating emergency liquidation request...")
        if mt5_connector.initialize():
            nexus_engine.emergency_flat()
            mt5_connector.shutdown()
        return

    # Mode 3: Terminal Status
    if args.status:
        logger.info("Testing MT5 connection and retrieving account status...")
        if mt5_connector.initialize():
            summary = mt5_connector.get_account_summary()
            logger.info(f"Account: #{summary['login']} ({summary['server']})")
            logger.info(f"Balance: ${summary['balance']:,.2f} | Equity: ${summary['equity']:,.2f}")
            logger.info(f"Mode: {summary['trade_mode']} | Leverage: 1:{summary['leverage']}")
            mt5_connector.shutdown()
        return

    # Mode 4: CLI Backtest Simulation
    if args.backtest:
        logger.info(f"Running historical backtest on {args.symbol} ({args.bars} bars)...")
        # Try fetching real data from MT5 first
        df = None
        if mt5_connector.initialize():
            df = market_data_provider.get_candles(args.symbol, timeframe=cfg.trading.timeframe, count=args.bars)
            mt5_connector.shutdown()

        if df is None or df.empty or len(df) < 100:
            logger.warning("MT5 disconnected or data unavailable. Falling back to synthetic market cycles...")
            from tests.test_confluence import TestConfluenceEngine
            tc = TestConfluenceEngine()
            df = tc._generate_synthetic_candles("bullish", args.bars)

        backtest_runner.run(
            symbol=args.symbol,
            df=df,
            initial_capital=10000.0,
            fixed_lot=cfg.risk.fixed_lot_size,
        )
        return

    # Mode 5: Autonomous Engine Mode (Default)
    try:
        nexus_engine.start()
    except KeyboardInterrupt:
        logger.info("Program interrupted by user. Shutting down...")
        nexus_engine.stop()


if __name__ == "__main__":
    main()
