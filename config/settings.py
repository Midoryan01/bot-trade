"""Config — only the fields a trader actually changes."""
from __future__ import annotations

from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # List fields stored as plain comma-separated strings so .env works naturally.
    # e.g. SYMBOL_PAIRS="BTC/USDT,ETH/USDT,SOL/USDT"
    symbol_pairs_str: str = "BTC/USDT,ETH/USDT,SOL/USDT"
    tp_rrr_str: str = "1.5,2.0,3.0"

    primary_timeframe: str = "1h"
    trigger_timeframe: str = "15m"
    signal_threshold: float = 0.70
    account_equity: float = 10_000.0
    risk_per_trade_pct: float = 0.01
    atr_sl_multiplier: float = 1.5
    rvol_threshold: float = 1.5
    cooldown_candles: int = 4
    state_dir: str = ".state"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Parsed at startup — use these in code, not the _str fields.
    symbol_pairs: list[str] = []
    tp_rrr: list[float] = []

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @field_validator("account_equity", "risk_per_trade_pct", "signal_threshold", mode="before")
    @classmethod
    def _empty_str_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @model_validator(mode="after")
    def _parse_lists(self) -> "Settings":
        if not self.symbol_pairs:
            self.symbol_pairs = [s.strip() for s in self.symbol_pairs_str.split(",")]
        if not self.tp_rrr:
            raw = self.tp_rrr_str.strip("[] ")
            self.tp_rrr = [float(x.strip()) for x in raw.split(",")]
        return self


settings = Settings()
