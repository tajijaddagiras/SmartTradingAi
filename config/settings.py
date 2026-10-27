"""
NexusTrade AI - Configuration Loader & Validator
Validates all user inputs, risk thresholds, and parameters using Pydantic.
"""

from pathlib import Path
from typing import List, Optional, Literal
import json
from pydantic import BaseModel, Field, field_validator


class SystemConfig(BaseModel):
    mode: Literal["demo", "live"] = Field(default="demo", description="Trading mode: demo or live")
    loop_interval_seconds: int = Field(default=15, ge=1, le=300, description="Main loop poll interval in seconds")
    log_level: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR")


class MT5Config(BaseModel):
    account: Optional[int] = Field(default=None, description="MT5 Account number (optional if terminal already logged in)")
    password: Optional[str] = Field(default=None, description="MT5 Account password")
    server: Optional[str] = Field(default=None, description="Broker server name")
    timeout_ms: int = Field(default=60000, ge=5000, description="Connection timeout in milliseconds")
    path: Optional[str] = Field(default=None, description="Custom path to terminal64.exe if needed")


class TradingConfig(BaseModel):
    symbols: List[str] = Field(default=["EURUSD", "GBPUSD", "XAUUSD"], min_length=1, description="Traded pairs")
    timeframe: str = Field(default="M15", description="Primary analysis timeframe: M1, M5, M15, M30, H1, H4, D1")
    magic_number: int = Field(default=889900, ge=1, description="Unique identifier for bot orders")

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, v: List[str]) -> List[str]:
        cleaned = [s.strip().upper() for s in v if s.strip()]
        if not cleaned:
            raise ValueError("Traded symbols list cannot be empty.")
        return cleaned


class RiskConfig(BaseModel):
    use_fixed_lot: bool = Field(default=True, description="True for fixed lot size, False for % equity risk calculation")
    fixed_lot_size: float = Field(default=0.01, ge=0.01, le=10.0, description="Fixed lot size (default 0.01 for micro/safety)")
    risk_per_trade_percent: float = Field(default=1.0, ge=0.1, le=5.0, description="Risk percentage per trade based on SL")
    max_daily_drawdown_percent: float = Field(default=3.0, ge=0.0, le=50.0, description="Max daily drawdown before freeze (0.0 to disable)")
    max_open_positions: int = Field(default=6, ge=1, le=20, description="Max total concurrent positions")
    max_layers_per_symbol: int = Field(default=3, ge=1, le=5, description="Max concurrent layer positions allowed on a single symbol")
    min_layer_distance_atr: float = Field(default=0.0, ge=0.0, le=3.0, description="Minimum price distance in ATR multiples between layers (0.0 for immediate full-layer execution)")
    max_spread_points: int = Field(default=35, ge=5, le=200, description="Max allowed spread in points before entry is blocked")


class ConfluenceConfig(BaseModel):
    min_confluence_score: int = Field(default=3, ge=1, le=3, description="Minimum score to trigger trade (2 for aggressive/testing, 3 for strict)")
    ema_trend_period: int = Field(default=50, ge=5, le=500, description="Trend filter EMA period")
    atr_period: int = Field(default=14, ge=5, le=100, description="ATR period for volatility filter")
    atr_multiplier_sl: float = Field(default=1.5, ge=0.5, le=5.0, description="ATR multiplier for hard stop loss distance")
    volume_ma_period: int = Field(default=20, ge=5, le=100, description="Moving average period for baseline volume")
    volume_spike_multiplier: float = Field(default=1.8, ge=1.1, le=5.0, description="Anomaly multiplier for institutional volume")
    swing_lookback: int = Field(default=10, ge=3, le=50, description="Bar lookback for swing high / low detection")


class SmartTrailingConfig(BaseModel):
    enabled: bool = Field(default=True, description="Enable smart dynamic trailing stop")
    activation_atr_multiple: float = Field(default=1.0, ge=0.3, le=5.0, description="ATR multiple profit required before trailing activates")
    trail_step_atr_multiple: float = Field(default=0.5, ge=0.1, le=2.0, description="ATR distance for trailing step")
    dynamic_exit_volume_exhaustion: bool = Field(default=True, description="Close trade early if volume exhausts at key level")
    volume_exhaustion_ratio: float = Field(default=0.45, ge=0.1, le=0.8, description="Volume ratio threshold indicating exhaustion")


class AntiSleepConfig(BaseModel):
    enabled: bool = Field(default=True, description="Prevent Windows OS from entering sleep while active orders exist")


class LicensingConfig(BaseModel):
    license_key: str = Field(default="NEXUS-TRIAL-2026", description="User license key")
    api_endpoint: str = Field(default="https://api.nexustrade.ai/v1/verify", description="License verification endpoint")


class AppConfig(BaseModel):
    system: SystemConfig = Field(default_factory=SystemConfig)
    mt5: MT5Config = Field(default_factory=MT5Config)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    confluence: ConfluenceConfig = Field(default_factory=ConfluenceConfig)
    smart_trailing: SmartTrailingConfig = Field(default_factory=SmartTrailingConfig)
    anti_sleep: AntiSleepConfig = Field(default_factory=AntiSleepConfig)
    licensing: LicensingConfig = Field(default_factory=LicensingConfig)


CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


def load_config(path: Optional[Path] = None) -> AppConfig:
    """Load and validate configuration from JSON file."""
    target_path = path or CONFIG_PATH
    if not target_path.exists():
        default_cfg = AppConfig()
        save_config(default_cfg, target_path)
        return default_cfg

    with open(target_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return AppConfig.model_validate(data)


def save_config(cfg: AppConfig, path: Optional[Path] = None) -> None:
    """Persist validated configuration to JSON file."""
    target_path = path or CONFIG_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(cfg.model_dump(), f, indent=2)


if __name__ == "__main__":
    cfg = load_config()
    print("Configuration loaded successfully!")
    print(f"Mode: {cfg.system.mode}, Symbols: {cfg.trading.symbols}")
