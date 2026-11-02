"""
NexusTrade AI - MetaTrader 5 Cross-Platform Stub / Mock Engine
Provides full API compatibility on Linux/macOS environments where native MT5 is absent.
Enables running the Zen Desktop Dashboard on remote Linux VPS without crashing.
"""

import time
import random
import numpy as np

# Timeframe Constants
TIMEFRAME_M1 = 1
TIMEFRAME_M5 = 5
TIMEFRAME_M15 = 15
TIMEFRAME_M30 = 30
TIMEFRAME_H1 = 60
TIMEFRAME_H4 = 240
TIMEFRAME_D1 = 1440

# Account Trade Modes
ACCOUNT_TRADE_MODE_DEMO = 0
ACCOUNT_TRADE_MODE_CONTEST = 1
ACCOUNT_TRADE_MODE_REAL = 2

# Order Types
ORDER_TYPE_BUY = 0
ORDER_TYPE_SELL = 1

# Order Filling
ORDER_FILLING_FOK = 0
ORDER_FILLING_IOC = 1
ORDER_FILLING_RETURN = 2

# Order Time
ORDER_TIME_GTC = 0

# Trade Actions & Retcodes
TRADE_ACTION_DEAL = 1
TRADE_ACTION_SLTP = 6
TRADE_RETCODE_DONE = 10009

# Deal Constants
DEAL_ENTRY_OUT = 1
DEAL_ENTRY_OUT_BY = 2
DEAL_TYPE_BUY = 0
DEAL_TYPE_SELL = 1

class Struct:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def _asdict(self):
        return self.__dict__
    def __getattr__(self, name):
        return self.__dict__.get(name, None)

_is_connected = True
_active_positions = []
_ticket_counter = 77100

def initialize(**kwargs):
    global _is_connected
    _is_connected = True
    return True

def shutdown():
    global _is_connected
    _is_connected = False
    return True

def last_error():
    return (1, "Success")

def terminal_info():
    return Struct(connected=True, trade_allowed=True, name="NexusTrade VPS Simulated MT5 Terminal")

def account_info():
    balance = 10540.25
    floating = sum(p.profit for p in _active_positions) if _active_positions else 0.0
    return Struct(
        login=889900,
        server="NexusTrade-Demo",
        balance=balance,
        equity=balance + floating,
        trade_mode=0, # Demo
        leverage=100,
        currency="USD",
        profit=floating,
        margin=100.0,
        margin_free=balance - 100.0,
        margin_level=1000.0,
    )

def login(login, password=None, server=None):
    return True

def symbol_info(symbol):
    digits = 3 if "JPY" in symbol else (2 if "XAU" in symbol else 5)
    point = 0.001 if "JPY" in symbol else (0.01 if "XAU" in symbol else 0.00001)
    return Struct(
        name=symbol,
        visible=True,
        digits=digits,
        point=point,
        trade_mode=4, # Full access
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01,
        filling_mode=2,
    )

def symbol_select(symbol, enable=True):
    return True

def symbol_info_tick(symbol):
    digits = 3 if "JPY" in symbol else (2 if "XAU" in symbol else 5)
    base_price = 160.25 if "JPY" in symbol else (2350.50 if "XAU" in symbol else 1.0850)
    jitter = (random.random() - 0.5) * (0.0004 if digits == 5 else 0.2)
    bid = round(base_price + jitter, digits)
    spread = 15 if digits == 5 else 25
    point = 0.00001 if digits == 5 else (0.001 if digits == 3 else 0.01)
    ask = round(bid + (spread * point), digits)
    return Struct(
        time=int(time.time()),
        bid=bid,
        ask=ask,
        last=bid,
        volume=120,
    )

def copy_rates_from_pos(symbol, timeframe, start_pos, count):
    digits = 3 if "JPY" in symbol else (2 if "XAU" in symbol else 5)
    base = 160.25 if "JPY" in symbol else (2350.50 if "XAU" in symbol else 1.0850)
    step_sec = timeframe * 60
    now = int(time.time())

    # Build numpy structured array matching MT5 copy_rates_from_pos format
    dtype = [
        ('time', 'i8'), ('open', 'f8'), ('high', 'f8'), ('low', 'f8'),
        ('close', 'f8'), ('tick_volume', 'i8'), ('spread', 'i4'), ('real_volume', 'i8')
    ]
    data = np.zeros(count, dtype=dtype)
    curr = base
    vol_base = 250

    for i in range(count):
        t = now - ((count - i) * step_sec)
        chg = (random.random() - 0.49) * (0.0008 if digits == 5 else 0.4)
        o = curr
        c = o + chg
        h = max(o, c) + abs(random.random() * (0.0005 if digits == 5 else 0.2))
        l = min(o, c) - abs(random.random() * (0.0005 if digits == 5 else 0.2))
        curr = c
        v = int(vol_base + (random.random() * 200))
        data[i] = (t, round(o, digits), round(h, digits), round(l, digits), round(c, digits), v, 12, v)

    return data

def order_send(request):
    global _ticket_counter
    action = request.get("action")
    if action == TRADE_ACTION_DEAL:
        _ticket_counter += 1
        pos = Struct(
            ticket=_ticket_counter,
            symbol=request.get("symbol", "EURUSD"),
            type=request.get("type", ORDER_TYPE_BUY),
            volume=request.get("volume", 0.01),
            price_open=request.get("price", 1.0850),
            price_current=request.get("price", 1.0850),
            sl=request.get("sl", 0.0),
            tp=request.get("tp", 0.0),
            profit=random.uniform(-5.0, 15.0),
            magic=request.get("magic", 889900),
            comment=request.get("comment", ""),
            time=int(time.time())
        )
        _active_positions.append(pos)
        return Struct(retcode=TRADE_RETCODE_DONE, order=_ticket_counter, comment="Request executed")

    elif action == TRADE_ACTION_SLTP:
        ticket = request.get("position")
        for p in _active_positions:
            if p.ticket == ticket:
                p.sl = request.get("sl", p.sl)
                p.tp = request.get("tp", p.tp)
                return Struct(retcode=TRADE_RETCODE_DONE, comment="SL/TP modified")
        return Struct(retcode=TRADE_RETCODE_DONE, comment="Simulated SL/TP modified")

    return Struct(retcode=TRADE_RETCODE_DONE, comment="Success")

def positions_get(symbol=None, ticket=None):
    if ticket:
        return [p for p in _active_positions if p.ticket == ticket]
    if symbol:
        return [p for p in _active_positions if p.symbol == symbol]
    return list(_active_positions)

def history_deals_get(date_from=None, date_to=None):
    return []
