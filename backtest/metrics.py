"""
NexusTrade AI - Quantitative Backtest Performance Metrics
Calculates Win Rate, Profit Factor, Max Drawdown, Sharpe Ratio, and Expectancy.
"""

from typing import List, Dict, Any
import numpy as np


class PerformanceMetrics:
    """Calculates quantitative performance analytics on trade history."""

    @staticmethod
    def calculate(trades: List[Dict[str, Any]], initial_capital: float = 10000.0) -> Dict[str, Any]:
        """
        Computes all standard institutional backtest metrics.
        Each trade dict must contain: 'pnl', 'entry_price', 'exit_price', 'action', 'symbol'.
        """
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "net_profit": 0.0,
                "profit_factor": 0.0,
                "max_drawdown_pct": 0.0,
                "max_drawdown_cash": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "risk_reward_ratio": 0.0,
                "expectancy": 0.0,
                "final_equity": initial_capital,
            }

        total_trades = len(trades)
        pnls = [t["pnl"] for t in trades]

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        total_win = sum(wins)
        total_loss = abs(sum(losses))

        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total_trades) * 100.0 if total_trades > 0 else 0.0

        net_profit = sum(pnls)
        profit_factor = (total_win / total_loss) if total_loss > 0 else (999.0 if total_win > 0 else 0.0)

        avg_win = (total_win / win_count) if win_count > 0 else 0.0
        avg_loss = (total_loss / loss_count) if loss_count > 0 else 0.0
        rr_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0.0

        # Expectancy: (Win Rate * Avg Win) - (Loss Rate * Avg Loss)
        win_prob = win_rate / 100.0
        loss_prob = (100.0 - win_rate) / 100.0
        expectancy = (win_prob * avg_win) - (loss_prob * avg_loss)

        # Equity Curve and Max Drawdown calculation
        equity = initial_capital
        equity_curve = [initial_capital]
        peak = initial_capital
        max_dd_cash = 0.0
        max_dd_pct = 0.0

        for pnl in pnls:
            equity += pnl
            equity_curve.append(equity)
            if equity > peak:
                peak = equity
            dd_cash = peak - equity
            dd_pct = (dd_cash / peak) * 100.0 if peak > 0 else 0.0
            if dd_cash > max_dd_cash:
                max_dd_cash = dd_cash
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct

        return {
            "initial_capital": initial_capital,
            "final_equity": round(equity, 2),
            "net_profit": round(net_profit, 2),
            "return_pct": round((net_profit / initial_capital) * 100.0, 2),
            "total_trades": total_trades,
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown_cash": round(max_dd_cash, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "risk_reward_ratio": round(rr_ratio, 2),
            "expectancy": round(expectancy, 2),
        }


metrics_calculator = PerformanceMetrics()
