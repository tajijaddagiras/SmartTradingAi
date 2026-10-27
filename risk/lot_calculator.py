"""
NexusTrade AI - Position & Lot Sizing Calculator
Calculates optimal position sizes based on capital risk % and Stop Loss distance.
Supports both Fixed Lot (for Phase 2/3 testing) and Dynamic Risk % allocation.
"""

from typing import Optional
from config.settings import AppConfig, load_config
from mt5_bridge.connector import mt5_connector
from mt5_bridge.market_data import market_data_provider
from core.logger import logger


class LotCalculator:
    """Calculates safe lot sizes adhering to capital preservation rules."""

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        connector=mt5_connector,
        market_data=market_data_provider
    ):
        self.config = config or load_config()
        self.connector = connector
        self.market_data = market_data

    def calculate_lot(
        self,
        symbol: str,
        entry_price: float,
        sl_price: float
    ) -> float:
        """
        Determines the lot size to trade based on configuration.
        """
        risk_cfg = self.config.risk

        # 1. Fixed Lot Mode (Micro lot testing)
        if risk_cfg.use_fixed_lot:
            return round(risk_cfg.fixed_lot_size, 2)

        # 2. Dynamic Equity Risk % Mode
        try:
            account = self.connector.get_account_summary()
            equity = account["equity"]
            specs = self.market_data.get_symbol_specs(symbol)
        except Exception as e:
            logger.warning(f"Could not compute dynamic lot size ({e}). Falling back to fixed lot.")
            return round(risk_cfg.fixed_lot_size, 2)

        point = specs["point"] or 0.00001
        contract_size = specs["trade_contract_size"] or 100000
        vol_min = specs["volume_min"]
        vol_max = specs["volume_max"]
        vol_step = specs["volume_step"] or 0.01

        # Distance to Stop Loss in points
        sl_distance_points = abs(entry_price - sl_price) / point
        if sl_distance_points <= 0:
            return vol_min

        # Maximum cash dollar amount we are willing to lose on this trade
        risk_amount = equity * (risk_cfg.risk_per_trade_percent / 100.0)

        # Value of 1 point per 1.0 standard lot
        point_value_per_lot = point * contract_size

        # Theoretical raw lot size
        raw_lot = risk_amount / (sl_distance_points * point_value_per_lot)

        # Normalize and constrain to broker bounds
        raw_lot = max(vol_min, min(vol_max, raw_lot))
        steps = round((raw_lot - vol_min) / vol_step)
        final_lot = vol_min + (steps * vol_step)

        logger.debug(
            f"[LotCalculator] Equity: ${equity:,.2f} | Risk: {risk_cfg.risk_per_trade_percent}% (${risk_amount:.2f}) "
            f"| SL Dist: {sl_distance_points:.1f} pts -> Lot: {final_lot:.2f}"
        )
        return round(final_lot, 2)


# Global instance
lot_calculator = LotCalculator()
