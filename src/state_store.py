"""
Signal dedup / cooldown store.
Persists to a JSON file under .state/ (cached by GitHub Actions between runs).
ponytail: JSON file — upgrade to SQLite only if concurrent writes are needed.
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

from config.settings import settings

_STATE_FILE = Path(settings.state_dir) / "signal_state.json"


def _load() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save(state: dict) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _key(symbol: str, timeframe: str, direction: str) -> str:
    return f"{symbol}|{timeframe}|{direction}"


def is_duplicate(symbol: str, timeframe: str, direction: str, candle_index: int) -> bool:
    """
    Returns True if a signal for this (symbol, timeframe, direction) was already
    emitted within the last `cooldown_candles` candles.
    """
    state = _load()
    k = _key(symbol, timeframe, direction)
    if k not in state:
        return False
    last_candle = state[k]["last_candle_index"]
    return (candle_index - last_candle) < settings.cooldown_candles


def record_signal(symbol: str, timeframe: str, direction: str, candle_index: int) -> None:
    state = _load()
    k = _key(symbol, timeframe, direction)
    state[k] = {
        "last_candle_index": candle_index,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    _save(state)


def clear_stale(symbol: str, timeframe: str, direction: str) -> None:
    """Remove entry when setup is invalidated (price closed below EMA25)."""
    state = _load()
    k = _key(symbol, timeframe, direction)
    state.pop(k, None)
    _save(state)
