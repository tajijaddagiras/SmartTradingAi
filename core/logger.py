"""
NexusTrade AI - Centralized Logging System
Provides colored terminal output and rotated file logs for audit trails.
Categorizes logs into System, Trades, and Errors.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


# Reconfigure stdout to UTF-8 on Windows if supported
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class ColoredFormatter(logging.Formatter):
    """Custom formatter adding color to console output."""
    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelno, Fore.WHITE)
        time_str = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        prefix = f"{Style.DIM}[{time_str}]{Style.RESET_ALL} {color}[{record.levelname:<7}]{Style.RESET_ALL}"
        message = record.getMessage()
        return f"{prefix} {message}"


def setup_logger(name: str = "NexusTrade") -> logging.Logger:
    """Configures and returns the central logger."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # 1. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)

    # 2. Main System File Handler (Rotating)
    system_log = LOGS_DIR / "system.log"
    file_handler = RotatingFileHandler(
        system_log, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)-7s] [%(name)s:%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    # 3. Error-only File Handler
    error_log = LOGS_DIR / "error.log"
    err_handler = RotatingFileHandler(
        error_log, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    err_handler.setLevel(logging.ERROR)
    err_handler.setFormatter(file_fmt)
    logger.addHandler(err_handler)

    return logger


def log_trade(
    symbol: str,
    action: str,
    lot: float,
    price: float,
    sl: float,
    ticket: int,
    rationale: str
) -> None:
    """Specialized trade journal logger for auditing every trade decision."""
    trades_log = LOGS_DIR / "trades.log"
    trades_logger = logging.getLogger("NexusTrade_Trades")
    if not trades_logger.handlers:
        trades_logger.setLevel(logging.INFO)
        th = RotatingFileHandler(
            trades_log, maxBytes=10 * 1024 * 1024, backupCount=10, encoding="utf-8"
        )
        th.setFormatter(
            logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )
        trades_logger.addHandler(th)

    msg = (
        f"TICKET #{ticket} | {action.upper()} {lot:.2f} {symbol} @ {price:.5f} | "
        f"HARD_SL: {sl:.5f} | RATIONALE: {rationale}"
    )
    trades_logger.info(msg)
    setup_logger().info(f"{Fore.MAGENTA}TRADE LOGGED:{Style.RESET_ALL} {msg}")


logger = setup_logger()
