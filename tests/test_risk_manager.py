"""
Unit tests for NexusTrade AI Risk Management, Circuit Breaker, Anti-Sleep, and Licensing.
"""

import unittest
from unittest.mock import MagicMock
from risk.drawdown_limiter import DailyDrawdownLimiter
from risk.lot_calculator import LotCalculator
from risk.spread_guard import SpreadGuard
from core.anti_sleep import anti_sleep_manager
from licensing.validator import license_validator
from config.settings import AppConfig


class TestRiskAndSafetyLayer(unittest.TestCase):

    def setUp(self):
        self.config = AppConfig()

    def test_drawdown_limiter_freeze(self):
        """Tests that a 3.5% equity drop triggers the daily circuit breaker."""
        mock_connector = MagicMock()
        # Baseline equity: $10,000
        mock_connector.get_account_summary.side_effect = [
            {"equity": 10000.0, "balance": 10000.0},
            {"equity": 9600.0, "balance": 10000.0},  # 4.0% loss -> Should Freeze!
        ]

        limiter = DailyDrawdownLimiter(config=self.config, connector=mock_connector)
        # 1st check sets baseline
        safe_1 = limiter.check_drawdown()
        self.assertTrue(safe_1)
        self.assertFalse(limiter.is_frozen)

        # 2nd check evaluates 4% loss against 3% limit
        safe_2 = limiter.check_drawdown()
        self.assertFalse(safe_2)
        self.assertTrue(limiter.is_frozen)
        self.assertIn("Daily Drawdown breach", limiter.freeze_reason)

    def test_lot_calculator_fixed_mode(self):
        """Tests fixed lot sizing."""
        calc = LotCalculator(config=self.config)
        lot = calc.calculate_lot("EURUSD", 1.1000, 1.0950)
        self.assertEqual(lot, 0.01)

    def test_spread_guard_blocks_excessive_spread(self):
        """Tests that spread exceeding limit is rejected."""
        mock_market_data = MagicMock()
        # Limit is 35 points; simulate news spike with 50 points
        mock_market_data.get_current_tick.return_value = {"spread_points": 50}

        guard = SpreadGuard(config=self.config, market_data=mock_market_data)
        safe = guard.is_spread_safe("EURUSD")
        self.assertFalse(safe)

    def test_anti_sleep_lifecycle(self):
        """Tests Win32 Anti-Sleep activation and deactivation."""
        res_lock = anti_sleep_manager.prevent_sleep()
        self.assertTrue(res_lock)
        self.assertTrue(anti_sleep_manager.is_active)

        res_unlock = anti_sleep_manager.allow_sleep()
        self.assertTrue(res_unlock)
        self.assertFalse(anti_sleep_manager.is_active)

    def test_licensing_hardware_fingerprint(self):
        """Tests that hardware fingerprint is deterministic and trial key works."""
        hw_id_1 = license_validator.get_hardware_fingerprint()
        hw_id_2 = license_validator.get_hardware_fingerprint()
        self.assertEqual(hw_id_1, hw_id_2)
        self.assertEqual(len(hw_id_1), 32)

        trial_check = license_validator.verify_license("NEXUS-TRIAL-2026")
        self.assertTrue(trial_check["valid"])
        self.assertEqual(trial_check["tier"], "TRIAL")


if __name__ == "__main__":
    unittest.main()
