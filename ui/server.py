"""
NexusTrade AI - Desktop UI Web-Bridge Backend
FastAPI server serving Zen Desktop Dashboard and REST API endpoints.
Controls bot lifecycle, settings configuration, live telemetry, and backtest runner.
"""

import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from config.settings import load_config, save_config, AppConfig
from mt5_bridge.connector import mt5_connector
from mt5_bridge.market_data import market_data_provider
from mt5_bridge.executor import order_executor
from risk.drawdown_limiter import drawdown_limiter
from risk.spread_guard import spread_guard
from core.anti_sleep import anti_sleep_manager
from strategy.confluence import confluence_engine
from backtest.backtest_runner import backtest_runner
from licensing.validator import license_validator
from strategy.indicators import indicators
from strategy.market_structure import market_structure_analyzer
from strategy.smc_engine import smc_engine
from core.engine import nexus_engine
from core.logger import logger
import pandas as pd
import numpy as np

app = FastAPI(title="NexusTrade AI Dashboard", version="1.0.0")

@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Thread control for background bot engine
bot_thread: Optional[threading.Thread] = None
is_bot_running: bool = False


def _bot_worker():
    global is_bot_running
    try:
        is_bot_running = True
        nexus_engine.config = load_config()
        nexus_engine.start()
    except Exception as e:
        logger.error(f"[UI Bot Worker] Error in bot loop: {e}")
    finally:
        is_bot_running = False


@app.get("/")
async def serve_index():
    """Serves the Zen Minimalist Desktop UI."""
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/status")
async def get_status() -> Dict[str, Any]:
    """Retrieves full system state, MT5 account telemetry, and safety indicators."""
    connected = mt5_connector.ensure_connected()
    account_data = {}
    if connected:
        try:
            account_data = mt5_connector.get_account_summary()
        except Exception:
            connected = False

    drawdown_limiter.check_drawdown()

    return {
        "bot_running": is_bot_running,
        "mt5_connected": connected,
        "account": account_data,
        "anti_sleep_active": anti_sleep_manager.is_active,
        "drawdown": {
            "is_frozen": drawdown_limiter.is_frozen,
            "freeze_reason": drawdown_limiter.freeze_reason,
            "max_allowed_pct": nexus_engine.config.risk.max_daily_drawdown_percent,
        },
        "mode": nexus_engine.config.system.mode,
        "timeframe": nexus_engine.config.trading.timeframe,
        "symbols": nexus_engine.config.trading.symbols,
    }


@app.get("/api/positions")
async def get_positions():
    """Returns currently open positions from MT5."""
    try:
        positions = order_executor.get_open_positions()
        return {"positions": positions}
    except Exception as e:
        return {"positions": [], "error": str(e)}


@app.get("/api/signals")
async def get_signals():
    """Scans configured symbols and returns live 3-factor confluence signals."""
    signals_list = []
    cfg = load_config()
    tf = cfg.trading.timeframe

    for symbol in cfg.trading.symbols:
        try:
            df = market_data_provider.get_candles(symbol, timeframe=tf, count=100)
            if not df.empty:
                sig = confluence_engine.evaluate(symbol, df)
                signals_list.append({
                    "symbol": symbol,
                    "action": sig.action,
                    "price": sig.price,
                    "sl": sig.sl,
                    "confluence_score": sig.confluence_score,
                    "structure_bias": sig.structure_bias,
                    "has_ob": sig.has_ob,
                    "has_volume_anomaly": sig.has_volume_anomaly,
                    "ema_trend_aligned": sig.ema_trend_aligned,
                    "structure_aligned": getattr(sig, "structure_aligned", False),
                    "smc_aligned": getattr(sig, "smc_aligned", False),
                    "target_score": getattr(cfg.confluence, "min_confluence_score", 3),
                    "rationale": sig.rationale,
                })
        except Exception as e:
            signals_list.append({
                "symbol": symbol,
                "action": "ERROR",
                "rationale": str(e),
                "confluence_score": 0,
            })

    return {"signals": signals_list}


@app.get("/api/chart")
async def get_chart_data(symbol: str = "EURUSD", timeframe: str = "M15", count: int = 180):
    """
    Returns candlestick bars, volume histogram, EMA 50 line,
    Order Blocks, S/R levels, signal markers, and active position lines.
    """
    cfg = load_config()
    df = None
    try:
        df = market_data_provider.get_candles(symbol, timeframe=timeframe, count=count)
    except Exception as e:
        logger.info(f"[UI Chart] Fallback to synthetic cycle candles: {e}")

    if df is None or df.empty:
        # Determine symbol-specific baseline price
        sym_upper = symbol.upper()
        base_price = 1.1000
        point_scale = 1.0
        if "XAU" in sym_upper or "GOLD" in sym_upper:
            base_price = 4018.0
            point_scale = 15.0
        elif "GBP" in sym_upper:
            base_price = 1.3300
            point_scale = 1.0
        elif "JPY" in sym_upper:
            base_price = 155.00
            point_scale = 50.0

        from tests.test_confluence import TestConfluenceEngine
        tc = TestConfluenceEngine()
        df = tc._generate_synthetic_candles("bullish", max(55, count), base_price=base_price, point_scale=point_scale)

    # Append indicators: EMA 50, ATR 14, Volume MA
    df = indicators.append_all_indicators(
        df,
        ema_period=cfg.confluence.ema_trend_period,
        atr_period=cfg.confluence.atr_period,
        volume_ma_period=cfg.confluence.volume_ma_period
    )

    structure = market_structure_analyzer.analyze_structure(df, lookback=cfg.confluence.swing_lookback)
    obs = smc_engine.find_order_blocks(df)

    candles = []
    volumes = []
    ema_line = []
    markers = []

    # Format timestamps into integer epoch seconds (handles datetime64[us] in pandas 3+)
    if pd.api.types.is_datetime64_any_dtype(df["time"]):
        timestamps = df["time"].apply(lambda x: int(x.timestamp()))
    else:
        timestamps = df["time"].astype(int)

    for i in range(len(df)):
        row = df.iloc[i]
        t = int(timestamps.iloc[i])
        o = float(row["open"])
        h = float(row["high"])
        l = float(row["low"])
        c = float(row["close"])
        v = float(row["volume"])
        ema = float(row["ema_trend"]) if not np.isnan(row["ema_trend"]) else None

        candles.append({
            "time": t,
            "open": round(o, 5),
            "high": round(h, 5),
            "low": round(l, 5),
            "close": round(c, 5)
        })

        vol_color = "rgba(16, 185, 129, 0.22)" if c >= o else "rgba(244, 63, 94, 0.22)"
        volumes.append({"time": t, "value": v, "color": vol_color})

        if ema is not None and i >= (cfg.confluence.ema_trend_period - 1):
            ema_line.append({"time": t, "value": round(ema, 5)})

    # Calculate real-time confluence signal marker
    sig = confluence_engine.evaluate(symbol, df)
    latest_t = int(timestamps.iloc[-1])

    target_score = getattr(cfg.confluence, "min_confluence_score", 3)
    if sig.action == "BUY":
        markers.append({
            "time": latest_t,
            "position": "belowBar",
            "color": "#10b981",
            "shape": "arrowUp",
            "text": f"BUY {sig.confluence_score}/{target_score} ({sig.price:.5f})",
        })
    elif sig.action == "SELL":
        markers.append({
            "time": latest_t,
            "position": "aboveBar",
            "color": "#f43f5e",
            "shape": "arrowDown",
            "text": f"SELL {sig.confluence_score}/{target_score} ({sig.price:.5f})",
        })

    # Active positions for this specific symbol
    positions = order_executor.get_open_positions(symbol=symbol)

    # Fetch live tick data for quick-trade bar
    current_tick = {}
    try:
        t = market_data_provider.get_current_tick(symbol)
        current_tick = {
            "bid": t["bid"],
            "ask": t["ask"],
            "spread_points": t["spread_points"]
        }
    except Exception:
        if candles:
            last_c = candles[-1]["close"]
            current_tick = {"bid": last_c, "ask": last_c, "spread_points": 20}

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "candles": candles,
        "volume": volumes,
        "ema": ema_line,
        "markers": markers,
        "support": structure.get("support_level"),
        "resistance": structure.get("resistance_level"),
        "order_blocks": {
            "bullish": obs.get("bullish_obs", [])[-3:],
            "bearish": obs.get("bearish_obs", [])[-3:],
        },
        "active_positions": positions,
        "current_tick": current_tick,
        "latest_signal": {
            "action": sig.action,
            "score": sig.confluence_score,
            "rationale": sig.rationale,
            "bias": sig.structure_bias
        }
    }


@app.get("/api/config")
async def get_configuration():
    """Returns current configuration."""
    return load_config().model_dump()


@app.post("/api/config")
async def update_configuration(new_cfg: Dict[str, Any]):
    """Saves updated configuration after Pydantic schema validation."""
    try:
        validated = AppConfig.model_validate(new_cfg)
        save_config(validated)
        nexus_engine.config = validated
        confluence_engine.config = validated
        spread_guard.config = validated
        logger.info("[UI] Configuration updated and reloaded successfully.")
        return {"success": True, "message": "Settings saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class QuickSyncPayload(BaseModel):
    symbols: Optional[List[str]] = None
    timeframe: Optional[str] = None


@app.post("/api/trading/quick-sync")
async def quick_sync(payload: QuickSyncPayload):
    """Instantly updates active trading symbols and timeframe from the Chart toolbar."""
    cfg = load_config()
    changed = False
    if payload.symbols is not None and len(payload.symbols) > 0:
        cfg.trading.symbols = [s.strip().upper() for s in payload.symbols if s.strip()]
        changed = True
    if payload.timeframe is not None and payload.timeframe.strip():
        cfg.trading.timeframe = payload.timeframe.strip().upper()
        changed = True
    if changed:
        save_config(cfg)
        nexus_engine.config = cfg
        order_executor.config = cfg
        confluence_engine.config = cfg
        spread_guard.config = cfg
        logger.info(f"[QuickSync] Synchronized from Chart: symbols={cfg.trading.symbols}, timeframe={cfg.trading.timeframe}")
    return {"success": True, "symbols": cfg.trading.symbols, "timeframe": cfg.trading.timeframe}


_usd_idr_cache = {"rate": 18090.0, "updated_at": 0.0}


@app.get("/api/currency/usd-idr")
async def get_live_usd_idr_rate():
    """
    Fetches real-time live USD to IDR market exchange rate.
    Caches for 5 minutes to avoid external API rate limiting while maintaining live rates.
    """
    global _usd_idr_cache
    now = time.time()
    if now - _usd_idr_cache["updated_at"] < 300 and _usd_idr_cache["rate"] > 10000:
        return {"success": True, "rate": _usd_idr_cache["rate"], "cached": True}

    import json
    import urllib.request

    # 1. Primary Public Rate API (Open Exchange Rates / ER-API)
    try:
        req = urllib.request.Request(
            "https://open.er-api.com/v6/latest/USD",
            headers={"User-Agent": "NexusTrade/1.0"}
        )
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode())
            idr_val = float(data["rates"]["IDR"])
            _usd_idr_cache = {"rate": round(idr_val, 2), "updated_at": now}
            logger.info(f"[LiveCurrency] Fetched live USD/IDR rate: {_usd_idr_cache['rate']}")
            return {"success": True, "rate": round(idr_val, 2), "source": "open-er-api"}
    except Exception as e:
        logger.warning(f"[LiveCurrency] Primary API error: {e}")

    # 2. Secondary Public Rate API
    try:
        req = urllib.request.Request(
            "https://api.exchangerate-api.com/v4/latest/USD",
            headers={"User-Agent": "NexusTrade/1.0"}
        )
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode())
            idr_val = float(data["rates"]["IDR"])
            _usd_idr_cache = {"rate": round(idr_val, 2), "updated_at": now}
            logger.info(f"[LiveCurrency] Fetched live USD/IDR from secondary API: {_usd_idr_cache['rate']}")
            return {"success": True, "rate": round(idr_val, 2), "source": "exchangerate-api"}
    except Exception as e2:
        logger.warning(f"[LiveCurrency] Secondary API error: {e2}")

    return {"success": True, "rate": _usd_idr_cache["rate"], "source": "fallback"}


@app.get("/api/trading/tick")
async def get_trading_tick(symbol: str = "EURUSD"):
    """Returns real-time tick (bid, ask, spread) for Quick Trade Bar."""
    try:
        t = market_data_provider.get_current_tick(symbol)
        return {
            "success": True,
            "symbol": symbol,
            "bid": t["bid"],
            "ask": t["ask"],
            "spread": t["spread_points"]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


class MT5AccountPayload(BaseModel):
    account: int
    password: str
    server: str


@app.post("/api/mt5/switch-account")
async def switch_mt5_account(payload: MT5AccountPayload):
    """
    Dynamically authenticates and switches active MT5 trading account (Demo or Real/Live).
    Instantly updates balance, mode, and equity telemetry across the entire app.
    """
    try:
        res = mt5_connector.switch_account(payload.account, payload.password, payload.server)
        if not res.get("success"):
            raise HTTPException(status_code=400, detail=res.get("error", "Gagal menghubungkan akun MT5."))

        # Reset drawdown baseline for new account equity
        drawdown_limiter.reset_freeze()
        nexus_engine.config = load_config()
        order_executor.config = nexus_engine.config
        confluence_engine.config = nexus_engine.config
        spread_guard.config = nexus_engine.config

        return res
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API Switch Account] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class ManualOrderPayload(BaseModel):
    symbol: str
    action: str
    lot: float = 0.01


@app.post("/api/trading/manual-order")
async def execute_manual_order(payload: ManualOrderPayload):
    """
    Executes a manual market order from the Quick Trade Bar.
    Automatically assigns institutional Stop Loss calculated from ATR / Market Structure.
    """
    action = payload.action.upper().strip()
    if action not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="Action must be BUY or SELL")

    symbol = payload.symbol.upper().strip()
    lot = max(0.01, float(payload.lot))

    # 1. Spread Check
    if not spread_guard.is_spread_safe(symbol):
        raise HTTPException(status_code=400, detail=f"Spread terlalu lebar untuk {symbol}. Order ditahan demi keamanan modal.")

    # 2. Get latest tick & candles for Stop Loss computation
    cfg = load_config()
    tf = cfg.trading.timeframe
    raw_df = market_data_provider.get_candles(symbol, timeframe=tf, count=120)

    try:
        tick = market_data_provider.get_current_tick(symbol)
        price = tick["ask"] if action == "BUY" else tick["bid"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengambil harga tick {symbol}: {e}")

    # Compute Smart Institutional Stop Loss
    sl = 0.0
    if not raw_df.empty:
        df_ind = indicators.append_all_indicators(raw_df, atr_period=cfg.confluence.atr_period)
        atr_val = float(df_ind["atr"].dropna().iloc[-1]) if "atr" in df_ind.columns and not df_ind["atr"].dropna().empty else 0.0015
        struct = market_structure_analyzer.analyze_structure(raw_df, lookback=cfg.confluence.swing_lookback)

        if action == "BUY":
            sup = struct.get("support_level")
            if sup and sup < price:
                sl = sup - (0.5 * atr_val)
            else:
                sl = price - (1.5 * atr_val)
        else: # SELL
            res = struct.get("resistance_level")
            if res and res > price:
                sl = res + (0.5 * atr_val)
            else:
                sl = price + (1.5 * atr_val)
    else:
        digits = 5 if ("XAU" not in symbol and "JPY" not in symbol) else 2
        offset = 0.0020 if digits == 5 else 2.50
        sl = (price - offset) if action == "BUY" else (price + offset)

    # 3. Open Order via OrderExecutor
    ticket = order_executor.open_order(
        symbol=symbol,
        action=action,
        lot=lot,
        sl=sl,
        rationale="Manual Quick Trade"
    )

    if not ticket:
        err_detail = getattr(order_executor, "last_error_message", None) or "MetaTrader 5 gagal mengeksekusi order manual."
        raise HTTPException(status_code=400, detail=err_detail)

    anti_sleep_manager.prevent_sleep()

    return {
        "success": True,
        "ticket": ticket,
        "symbol": symbol,
        "action": action,
        "lot": lot,
        "price": price,
        "sl": sl,
        "message": f"Posisi {action} {lot:.2f} {symbol} berhasil dibuka @ {price} (Hard SL: {sl:.5f})"
    }


@app.post("/api/bot/start")
async def start_bot():
    """Starts the trading bot in a background thread."""
    global bot_thread, is_bot_running
    if is_bot_running:
        return {"success": True, "message": "Bot is already running."}

    bot_thread = threading.Thread(target=_bot_worker, daemon=True)
    bot_thread.start()
    return {"success": True, "message": "NexusTrade AI engine started."}


@app.post("/api/bot/stop")
async def stop_bot():
    """Stops the trading bot gracefully without dropping MT5 connection."""
    nexus_engine.stop(disconnect_mt5=False)
    return {"success": True, "message": "NexusTrade AI engine stopping..."}


@app.post("/api/drawdown/reset")
async def reset_drawdown():
    """Resets the circuit breaker freeze and syncs baseline to current equity."""
    drawdown_limiter.reset_freeze()
    return {"success": True, "message": "Proteksi drawdown harian berhasil di-reset. Bot dapat dijalankan kembali."}


@app.post("/api/bot/flat")
async def emergency_flat():
    """Liquidates all open positions immediately (Flat Before Close)."""
    closed = order_executor.close_all_positions(reason="UI Emergency Flat")
    anti_sleep_manager.allow_sleep()
    return {"success": True, "closed_tickets": closed}


@app.post("/api/positions/{ticket}/close")
async def close_single_position(ticket: int):
    """Liquidates a single active position manually from the UI."""
    success = order_executor.close_position(ticket, reason="UI Manual Close")
    return {"success": success, "ticket": ticket}


@app.get("/api/history")
async def get_closed_history(limit: int = 100):
    """Returns closed trade deals from MT5 history."""
    history = order_executor.get_history_deals(limit=limit)
    return {"history": history}


@app.post("/api/license/verify")
async def verify_license():
    """Verifies license and returns hardware fingerprint."""
    result = license_validator.verify_license()
    return result


class BacktestRequest(BaseModel):
    symbol: str = "EURUSD"
    bars: int = 400


@app.post("/api/backtest")
async def run_backtest(req: BacktestRequest):
    """Executes backtest on historical data and returns institutional analytics."""
    try:
        cfg = load_config()
        tf = cfg.trading.timeframe
        df = None
        # Attempt to get real historical data from MT5 if available
        try:
            df = market_data_provider.get_candles(req.symbol, timeframe=tf, count=req.bars)
        except Exception as conn_err:
            logger.info(f"[UI Backtest] MT5 not connected ({conn_err}). Generating realistic cycle data for backtest simulation.")

        if df is None or df.empty or len(df) < 100:
            from tests.test_confluence import TestConfluenceEngine
            tc = TestConfluenceEngine()
            df = tc._generate_synthetic_candles("bullish", req.bars)

        results = backtest_runner.run(
            symbol=req.symbol,
            df=df,
            initial_capital=10000.0,
            fixed_lot=cfg.risk.fixed_lot_size,
        )
        return {"success": True, "metrics": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@app.get("/api/logs")
async def get_logs():
    """Returns recent log lines from trades and system logs."""
    logs_dir = Path(__file__).resolve().parent.parent / "logs"
    trades_log = logs_dir / "trades.log"
    system_log = logs_dir / "system.log"

    def read_tail(p: Path, lines=30):
        if not p.exists():
            return []
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return [line.strip() for line in f.readlines()[-lines:] if line.strip()]

    return {
        "trades": read_tail(trades_log, 30),
        "system": read_tail(system_log, 30),
    }


def start_ui_server(host: str = "127.0.0.1", port: int = 8899):
    """Runs the FastAPI server using Uvicorn."""
    import uvicorn
    logger.info(f"🌐 Launching NexusTrade Zen UI at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    start_ui_server()
