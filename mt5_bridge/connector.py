"""
NexusTrade AI - MT5 Connection Manager & Watchdog
Handles initialization, account authentication, heartbeat, and reconnection logic.
"""

from typing import Optional, Dict, Any
import MetaTrader5 as mt5
from config.settings import AppConfig, load_config, save_config
from core.logger import logger


class MT5Connector:
    """Manages the connection lifecycle between NexusTrade AI and MetaTrader 5."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()
        self._is_initialized = False

    def initialize(self) -> bool:
        """Initializes connection to MT5 terminal."""
        mt5_cfg = self.config.mt5
        init_kwargs = {}

        if mt5_cfg.path:
            init_kwargs["path"] = mt5_cfg.path
        if mt5_cfg.timeout_ms:
            init_kwargs["timeout"] = mt5_cfg.timeout_ms

        logger.info("Initializing MetaTrader 5 connection...")
        if not mt5.initialize(**init_kwargs):
            err_code, err_desc = mt5.last_error()
            logger.error(f"MT5 initialize failed: Code {err_code} - {err_desc}")
            return False

        # If credentials provided, attempt explicit login
        if mt5_cfg.account and mt5_cfg.password and mt5_cfg.server:
            logger.info(f"Authenticating to MT5 account {mt5_cfg.account} on server {mt5_cfg.server}...")
            logged_in = mt5.login(
                login=mt5_cfg.account,
                password=mt5_cfg.password,
                server=mt5_cfg.server,
                timeout=mt5_cfg.timeout_ms
            )
            if not logged_in:
                err_code, err_desc = mt5.last_error()
                logger.error(f"MT5 login failed: Code {err_code} - {err_desc}")
                mt5.shutdown()
                return False

        account_info = mt5.account_info()
        if account_info is None:
            logger.error("Connected to MT5, but failed to retrieve account_info.")
            mt5.shutdown()
            return False

        self._is_initialized = True
        logger.info(
            f"MT5 Connected successfully! Account: #{account_info.login} "
            f"({account_info.server}) | Balance: ${account_info.balance:,.2f} "
            f"| Equity: ${account_info.equity:,.2f} | Leverage: 1:{account_info.leverage}"
        )
        return True

    def is_connected(self) -> bool:
        """Verifies if terminal connection and broker ping are alive."""
        if not self._is_initialized:
            return False
        terminal_info = mt5.terminal_info()
        if terminal_info is None or not terminal_info.connected:
            return False
        return True

    def ensure_connected(self) -> bool:
        """Watchdog: verifies connection and reconnects automatically if dropped."""
        if self.is_connected():
            return True

        logger.warning("MT5 connection dropped or not ready. Attempting reconnect...")
        self.shutdown()
        return self.initialize()

    def get_account_summary(self) -> Dict[str, Any]:
        """Returns structured dictionary of account financial metrics."""
        if not self.ensure_connected():
            raise ConnectionError("Cannot get account summary: MT5 is disconnected.")

        acc = mt5.account_info()
        if acc is None:
            raise RuntimeError("Failed to fetch MT5 account info.")

        ti = mt5.terminal_info()
        trade_allowed = bool(ti.trade_allowed) if ti is not None else True

        return {
            "login": acc.login,
            "server": acc.server,
            "currency": acc.currency,
            "balance": acc.balance,
            "equity": acc.equity,
            "margin": acc.margin,
            "margin_free": acc.margin_free,
            "margin_level": acc.margin_level,
            "profit": acc.profit,
            "trade_mode": "DEMO" if acc.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO else "REAL",
            "leverage": acc.leverage,
            "trade_allowed": trade_allowed,
        }

    def verify_symbol(self, symbol: str) -> bool:
        """Ensures symbol exists in broker specs and is selected in Market Watch."""
        if not self.ensure_connected():
            return False

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.error(f"Symbol '{symbol}' not found on MT5 broker server.")
            return False

        if not symbol_info.visible:
            logger.info(f"Symbol '{symbol}' not visible in Market Watch. Selecting...")
            if not mt5.symbol_select(symbol, True):
                logger.error(f"Failed to add symbol '{symbol}' to Market Watch.")
                return False

        return True

    def switch_account(self, account: int, password: str, server: str) -> Dict[str, Any]:
        """Switches active MT5 trading account dynamically (Demo or Live/Real)."""
        if not self.ensure_connected():
            if not self.initialize():
                return {"success": False, "error": "Terminal MetaTrader 5 tidak dapat dihubungi. Pastikan aplikasi MT5 terbuka di komputer Anda."}

        server_clean = server.strip()
        account_int = int(account)
        password_clean = password.strip()

        logger.info(f"Mengalihkan akun MT5 ke #{account_int} pada server {server_clean}...")
        logged_in = mt5.login(
            login=account_int,
            password=password_clean,
            server=server_clean,
            timeout=30000
        )
        if not logged_in:
            err_code, err_desc = mt5.last_error()
            logger.error(f"Gagal login ke akun MT5 #{account_int}: Code {err_code} - {err_desc}")
            err_msg = f"Gagal login ke akun #{account_int} di server '{server_clean}'. Pastikan Nomor Akun, Password, dan Server Broker tepat (Kode MT5: {err_code} - {err_desc})."
            return {"success": False, "error": err_msg}

        acc = mt5.account_info()
        if acc is None:
            return {"success": False, "error": "Login berhasil tetapi gagal mengambil informasi akun dari broker."}

        self._is_initialized = True
        trade_mode_str = "REAL" if acc.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO else "DEMO"

        # Update and persist app configuration
        self.config = load_config()
        self.config.mt5.account = account_int
        self.config.mt5.password = password_clean
        self.config.mt5.server = server_clean
        self.config.system.mode = "live" if trade_mode_str == "REAL" else "demo"
        save_config(self.config)

        logger.info(
            f"✅ MT5 Berhasil dialihkan! Akun: #{acc.login} ({acc.server}) | "
            f"Mode: {trade_mode_str} | Saldo: ${acc.balance:,.2f} | Leverage: 1:{acc.leverage}"
        )

        return {
            "success": True,
            "login": acc.login,
            "server": acc.server,
            "balance": acc.balance,
            "equity": acc.equity,
            "currency": acc.currency,
            "trade_mode": trade_mode_str,
            "message": f"Berhasil terhubung ke akun {trade_mode_str} #{acc.login} ({acc.server})! Saldo: ${acc.balance:,.2f}"
        }

    def shutdown(self) -> None:
        """Gracefully disconnects from MT5 terminal."""
        if self._is_initialized:
            mt5.shutdown()
            self._is_initialized = False
            logger.info("MT5 connection closed gracefully.")


# Global connector instance
mt5_connector = MT5Connector()
