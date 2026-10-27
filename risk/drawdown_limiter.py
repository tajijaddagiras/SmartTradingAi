"""
NexusTrade AI - Daily Drawdown Circuit Breaker
Protects capital by freezing trading when daily loss limit is reached.
Monitors both realized closed trade losses and current floating equity.
"""

from datetime import datetime, date
from typing import Optional
from config.settings import AppConfig, load_config
from mt5_bridge.connector import mt5_connector
from core.logger import logger


class DailyDrawdownLimiter:
    """Monitors daily drawdown and halts trading if loss threshold is breached."""

    def __init__(self, config: Optional[AppConfig] = None, connector=mt5_connector):
        self.config = config or load_config()
        self.connector = connector
        self._current_date: date = date.today()
        self._initial_day_equity: Optional[float] = None
        self._is_frozen: bool = False
        self._freeze_reason: str = ""

    def _sync_day(self, current_equity: float) -> None:
        """Resets daily baseline equity at midnight or initial start."""
        today = date.today()
        if self._initial_day_equity is None or today != self._current_date:
            self._current_date = today
            self._initial_day_equity = current_equity
            self._is_frozen = False
            self._freeze_reason = ""
            logger.info(
                f"[DrawdownLimiter] New trading day started ({today}). "
                f"Baseline day equity established: ${current_equity:,.2f}"
            )

    def check_drawdown(self) -> bool:
        """
        Calculates current daily drawdown.
        Returns True if trading is safe, False if daily limit is breached (FREEZE).
        """
        if self._is_frozen:
            return False

        try:
            summary = self.connector.get_account_summary()
        except Exception as e:
            logger.warning(f"[DrawdownLimiter] Could not fetch account info: {e}")
            return True

        current_equity = summary["equity"]
        self._sync_day(current_equity)

        if self._initial_day_equity is None or self._initial_day_equity <= 0:
            return True

        max_allowed_pct = self.config.risk.max_daily_drawdown_percent
        if max_allowed_pct <= 0:
            # 0.0 or negative means daily drawdown limit is disabled (Unlimited Mode)
            return True

        loss = self._initial_day_equity - current_equity
        drawdown_pct = (loss / self._initial_day_equity) * 100.0

        if drawdown_pct >= max_allowed_pct:
            self._is_frozen = True
            self._freeze_reason = (
                f"Daily Drawdown breach: {drawdown_pct:.2f}% loss "
                f"exceeded limit of {max_allowed_pct:.2f}% "
                f"(Baseline: ${self._initial_day_equity:,.2f}, Current: ${current_equity:,.2f})"
            )
            logger.critical(
                f"🚨 [CIRCUIT BREAKER TRIGGERED] {self._freeze_reason}. "
                f"Trading FROZEN until tomorrow 00:00."
            )
            return False

        return True

    @property
    def is_frozen(self) -> bool:
        return self._is_frozen

    @property
    def freeze_reason(self) -> str:
        return self._freeze_reason

    def reset_freeze(self, new_baseline: Optional[float] = None) -> None:
        """Manual administrative override to unfreeze trading and reset baseline."""
        self._is_frozen = False
        self._freeze_reason = ""
        if new_baseline is not None and new_baseline > 0:
            self._initial_day_equity = new_baseline
            logger.info(f"[DrawdownLimiter] Baseline reset to: ${new_baseline:,.2f}")
        else:
            try:
                summary = self.connector.get_account_summary()
                self._initial_day_equity = summary.get("equity", 0.0)
                logger.info(f"[DrawdownLimiter] Baseline reset to current equity: ${self._initial_day_equity:,.2f}")
            except Exception:
                pass
        logger.warning("[DrawdownLimiter] Trading manually unfrozen by user reset.")


# Global instance
drawdown_limiter = DailyDrawdownLimiter()
