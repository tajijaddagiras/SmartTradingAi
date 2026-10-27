"""
NexusTrade AI - OS Anti-Sleep Daemon
Prevents Windows laptop/desktop from entering sleep or hibernation while active orders are open.
Uses Windows Win32 API SetThreadExecutionState.
"""

import sys
import platform
from core.logger import logger

# Win32 Execution Flags
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_AWAYMODE_REQUIRED = 0x00000040


class AntiSleepManager:
    """Manages OS power state to prevent premature sleep during active trades."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._is_active = False
        self._is_windows = platform.system().lower() == "windows"

        if not self._is_windows:
            logger.warning("AntiSleepManager: Non-Windows OS detected. Native Win32 power management is disabled.")

    def prevent_sleep(self) -> bool:
        """Lock system power state so computer stays awake."""
        if not self.enabled or not self._is_windows:
            return False

        if self._is_active:
            return True

        try:
            import ctypes
            # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
            flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
            res = ctypes.windll.kernel32.SetThreadExecutionState(flags)
            if res != 0:
                self._is_active = True
                logger.info("[AntiSleep] OS sleep locked: System will stay awake during open trades.")
                return True
            else:
                logger.error("[AntiSleep] Failed to set Win32 thread execution state.")
                return False
        except Exception as e:
            logger.error(f"[AntiSleep] Exception while enabling anti-sleep: {e}")
            return False

    def allow_sleep(self) -> bool:
        """Unlock system power state back to default OS power plan."""
        if not self._is_windows or not self._is_active:
            return True

        try:
            import ctypes
            res = ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            if res != 0:
                self._is_active = False
                logger.info("[AntiSleep] OS sleep unlocked: System power plan restored to normal.")
                return True
            else:
                logger.warning("[AntiSleep] Failed to restore normal thread execution state.")
                return False
        except Exception as e:
            logger.error(f"[AntiSleep] Exception while disabling anti-sleep: {e}")
            return False

    @property
    def is_active(self) -> bool:
        return self._is_active


# Singleton instance
anti_sleep_manager = AntiSleepManager()
