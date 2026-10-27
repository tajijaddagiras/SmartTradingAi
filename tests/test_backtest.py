"""
Unit tests for NexusTrade AI Historical Backtest Engine.
"""

import unittest
from backtest.backtest_runner import backtest_runner
from tests.test_confluence import TestConfluenceEngine


class TestBacktestEngine(unittest.TestCase):

    def test_backtest_runner_execution(self):
        generator = TestConfluenceEngine()
        df = generator._generate_synthetic_candles("bullish", 300)

        results = backtest_runner.run(
            symbol="EURUSD",
            df=df,
            initial_capital=10000.0,
            fixed_lot=0.01,
            spread_points=15,
        )

        self.assertIn("initial_capital", results)
        self.assertIn("final_equity", results)
        self.assertIn("win_rate", results)
        self.assertIn("profit_factor", results)
        self.assertIn("max_drawdown_pct", results)
        self.assertEqual(results["initial_capital"], 10000.0)


if __name__ == "__main__":
    unittest.main()
