"""
NexusTrade AI - Order Execution Engine
Enforces Mandatory Server-Side Hard Stop Loss, Order Sizing, Position Modification,
and Emergency 'Flat Before Close' executions.
"""

from typing import Optional, List, Dict, Any
import MetaTrader5 as mt5
from config.settings import AppConfig, load_config
from mt5_bridge.connector import mt5_connector
from core.logger import logger, log_trade


class OrderExecutor:
    """Executes trades, modifies stops, and handles emergency liquidation on MT5."""

    def __init__(self, config: Optional[AppConfig] = None, connector=mt5_connector):
        self.config = config or load_config()
        self.connector = connector
        self.last_error_message: Optional[str] = None

    def _get_filling_type(self, symbol: str) -> int:
        """Determines supported order filling mode for the symbol."""
        info = mt5.symbol_info(symbol)
        if info is None:
            return mt5.ORDER_FILLING_IOC

        filling_mode = info.filling_mode
        # In MetaTrader 5 API, filling_mode bitmask: bit 0 (1) = FOK, bit 1 (2) = IOC
        if filling_mode & 1:
            return mt5.ORDER_FILLING_FOK
        elif filling_mode & 2:
            return mt5.ORDER_FILLING_IOC
        return mt5.ORDER_FILLING_RETURN

    def _normalize_lot(self, symbol: str, lot: float) -> float:
        """Rounds lot size to broker volume step and bounds within min/max lot."""
        info = mt5.symbol_info(symbol)
        if info is None:
            return round(lot, 2)

        vol_min = info.volume_min
        vol_max = info.volume_max
        vol_step = info.volume_step or 0.01

        # Clamp to bounds
        lot = max(vol_min, min(vol_max, lot))

        # Align to step
        steps = round((lot - vol_min) / vol_step)
        normalized = vol_min + (steps * vol_step)
        return round(normalized, 2)

    def open_order(
        self,
        symbol: str,
        action: str,
        lot: float,
        sl: float,
        tp: Optional[float] = None,
        rationale: str = ""
    ) -> Optional[int]:
        """
        Executes a market order with MANDATORY Server-Side Hard Stop Loss.
        Returns order ticket integer on success, or None on failure.
        """
        if not self.connector.ensure_connected():
            logger.error("Order rejected: MT5 is disconnected.")
            return None

        # --- MANDATORY HARD STOP LOSS INTEGRITY CHECK ---
        if sl is None or sl <= 0.0:
            logger.critical(
                f"[SAFETY REJECTION] Order on {symbol} aborted! "
                f"PRD Rule Violation: Server-Side Hard Stop Loss is mandatory."
            )
            return None

        action_upper = action.strip().upper()
        if action_upper not in ("BUY", "SELL"):
            logger.error(f"Invalid order action: {action}. Must be BUY or SELL.")
            return None

        sym_info = mt5.symbol_info(symbol)
        if sym_info is None:
            logger.error(f"Cannot open order: Symbol {symbol} not found.")
            return None

        digits = sym_info.digits
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logger.error(f"Cannot open order: Failed to get current tick for {symbol}.")
            return None

        normalized_lot = self._normalize_lot(symbol, lot)
        sl_rounded = round(sl, digits)
        tp_rounded = round(tp, digits) if tp is not None and tp > 0 else 0.0

        if action_upper == "BUY":
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
            if sl_rounded >= price:
                logger.error(f"Invalid BUY Hard SL ({sl_rounded}) must be below Ask price ({price}).")
                return None
        else:
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
            if sl_rounded <= price:
                logger.error(f"Invalid SELL Hard SL ({sl_rounded}) must be above Bid price ({price}).")
                return None

        filling = self._get_filling_type(symbol)
        magic = self.config.trading.magic_number

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": normalized_lot,
            "type": order_type,
            "price": price,
            "sl": sl_rounded,
            "tp": tp_rounded,
            "deviation": 20,
            "magic": magic,
            "comment": "NexusTrade AI",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling,
        }

        logger.info(
            f"Sending {action_upper} order: {normalized_lot} {symbol} @ {price:.{digits}f} "
            f"| HARD_SL: {sl_rounded:.{digits}f} | TP: {tp_rounded:.{digits}f}..."
        )

        result = mt5.order_send(request)
        if result is None:
            err_code, err_desc = mt5.last_error()
            self.last_error_message = f"order_send gagal tanpa respon dari MT5: {err_desc} (Code {err_code})"
            logger.error(f"order_send failed without response: Code {err_code} - {err_desc}")
            return None

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            ret_comment = result.comment or ""
            if result.retcode == 10027 or "AutoTrading disabled" in ret_comment:
                friendly_msg = (
                    "Tombol 'Algo Trading' di aplikasi MetaTrader 5 laptop/PC Anda sedang MATI (Merah). "
                    "Harap klik tombol 'Algo Trading' di toolbar atas MetaTrader 5 (sampai tombolnya jadi HIJAU) "
                    "agar order dapat masuk ke broker."
                )
            elif result.retcode == 10014:
                friendly_msg = "Volume lot tidak valid untuk akun/broker ini (terlalu kecil/besar)."
            elif result.retcode == 10018:
                friendly_msg = "Pasar saat ini sedang tutup (Market Closed)."
            elif result.retcode == 10019:
                friendly_msg = "Saldo atau Free Margin akun tidak mencukupi untuk membuka transaksi ini."
            else:
                friendly_msg = f"Order ditolak oleh broker MT5: {ret_comment} (Retcode {result.retcode})"

            self.last_error_message = friendly_msg
            logger.error(
                f"Order failed! Retcode: {result.retcode} ({result.comment}) | "
                f"Request: {action_upper} {normalized_lot} {symbol} @ {price}"
            )
            return None

        self.last_error_message = None
        ticket = result.order
        logger.info(f"Order #{ticket} executed successfully @ {result.price:.{digits}f}!")

        # Log to trade journal
        log_trade(
            symbol=symbol,
            action=action_upper,
            lot=normalized_lot,
            price=result.price,
            sl=sl_rounded,
            ticket=ticket,
            rationale=rationale
        )

        return ticket

    def modify_sl(self, ticket: int, new_sl: float) -> bool:
        """
        Modifies the Stop Loss of an open position on the MT5 broker server.
        Used by Smart Trailing Stop engine.
        """
        if not self.connector.ensure_connected():
            return False

        position = mt5.positions_get(ticket=ticket)
        if not position:
            logger.warning(f"Cannot modify SL: Position #{ticket} not found or already closed.")
            return False

        pos = position[0]
        sym_info = mt5.symbol_info(pos.symbol)
        digits = sym_info.digits if sym_info else 5
        new_sl_rounded = round(new_sl, digits)

        # Skip modification if negligible difference
        if abs(pos.sl - new_sl_rounded) < (sym_info.point if sym_info else 0.00001):
            return True

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": pos.symbol,
            "sl": new_sl_rounded,
            "tp": pos.tp,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            retcode = result.retcode if result else "None"
            comment = result.comment if result else "No response"
            logger.warning(f"Failed to modify SL for position #{ticket}: Code {retcode} - {comment}")
            return False

        logger.info(f"[Smart Trailing] Position #{ticket} SL updated: {pos.sl:.{digits}f} -> {new_sl_rounded:.{digits}f}")
        return True

    def close_position(self, ticket: int, reason: str = "Standard Close") -> bool:
        """Closes a specific open position using market order."""
        if not self.connector.ensure_connected():
            return False

        position = mt5.positions_get(ticket=ticket)
        if not position:
            logger.warning(f"Cannot close position #{ticket}: Position does not exist.")
            return False

        pos = position[0]
        symbol = pos.symbol
        digits = mt5.symbol_info(symbol).digits if mt5.symbol_info(symbol) else 5
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logger.error(f"Failed to get tick to close position #{ticket}.")
            return False

        # Opposite order type for closing
        if pos.type == mt5.ORDER_TYPE_BUY:
            close_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            close_type = mt5.ORDER_TYPE_BUY
            price = tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": symbol,
            "volume": pos.volume,
            "type": close_type,
            "price": price,
            "deviation": 25,
            "magic": self.config.trading.magic_number,
            "comment": f"Close: {reason}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._get_filling_type(symbol),
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            comment = result.comment if result else "No response"
            logger.error(f"Failed to close position #{ticket}: {comment}")
            return False

        logger.info(f"Position #{ticket} ({symbol}) closed successfully @ {price:.{digits}f} | Reason: {reason}")
        return True

    def close_all_positions(self, symbol: Optional[str] = None, reason: str = "Flat Before Close") -> List[int]:
        """
        Emergency 'Flat Before Close': Instantly liquidates all open positions.
        Returns list of closed tickets.
        """
        closed_tickets: List[int] = []
        positions = self.get_open_positions(symbol=symbol)

        if not positions:
            logger.info("No open positions to close.")
            return closed_tickets

        logger.warning(f"[EMERGENCY CLOSE ALL] Closing {len(positions)} open positions. Reason: {reason}")
        for pos in positions:
            ticket = pos["ticket"]
            if self.close_position(ticket, reason=reason):
                closed_tickets.append(ticket)

        logger.info(f"Close All completed. Total positions closed: {len(closed_tickets)}/{len(positions)}")
        return closed_tickets

    def get_open_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves currently open positions filtered by magic number and optional symbol."""
        if not self.connector.ensure_connected():
            return []

        magic = self.config.trading.magic_number
        kwargs = {}
        if symbol:
            kwargs["symbol"] = symbol

        raw_positions = mt5.positions_get(**kwargs)
        if raw_positions is None:
            return []

        results = []
        for p in raw_positions:
            # Filter by bot magic number if configured
            if magic and p.magic != magic:
                continue

            results.append({
                "ticket": p.ticket,
                "symbol": p.symbol,
                "type": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
                "volume": p.volume,
                "price_open": p.price_open,
                "sl": p.sl,
                "tp": p.tp,
                "price_current": p.price_current,
                "profit": p.profit,
                "swap": p.swap,
                "time": p.time,
                "magic": p.magic,
                "comment": p.comment,
            })

        return results

    def get_history_deals(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves recently closed trade deals from MT5 history."""
        if not self.connector.ensure_connected():
            return []
        import datetime
        now = datetime.datetime.now()
        # Look ahead 2 days to account for any broker server timezone ahead of local time
        end_time = now + datetime.timedelta(days=2)
        start_time = now - datetime.timedelta(days=30)
        deals = mt5.history_deals_get(start_time, end_time)
        if deals is None:
            return []

        results = []
        for d in reversed(deals):
            # Only include actual closed trade exits (DEAL_ENTRY_OUT or non-zero profit deals)
            if d.symbol and (d.entry in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY) or d.profit != 0.0):
                # In MT5 closing deals (DEAL_ENTRY_OUT), the deal operation is opposite the position direction
                # (e.g., DEAL_TYPE_BUY closes a SELL position, DEAL_TYPE_SELL closes a BUY position)
                pos_type = "SELL" if d.type == mt5.DEAL_TYPE_BUY else "BUY"
                results.append({
                    "ticket": d.ticket,
                    "order": d.order,
                    "symbol": d.symbol,
                    "type": pos_type,
                    "volume": d.volume,
                    "price": d.price,
                    "profit": d.profit,
                    "time": d.time,
                    "comment": d.comment
                })
                if len(results) >= limit:
                    break
        return results


# Global executor instance
order_executor = OrderExecutor()
