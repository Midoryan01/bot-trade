"""
Pipeline orchestrator.
Fail-safe: any exception in per-pair processing is caught and logged;
the pipeline continues to the next pair rather than crashing the whole run.
"""
from __future__ import annotations

# Bootstrap: add project root so `config.*` and `src.*` resolve when run as a script.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import time

from config.settings import settings
from src import fetcher, risk_manager, state_store, strategy, telegram_bot
from src.indicators import momentum, trend, volatility, volume
from src.logger import configure
from src.strategy import SignalResult

configure()
log = logging.getLogger(__name__)


def _apply_indicators(df):
    """Run the full indicator stack on a DataFrame; returns dropna'd copy."""
    trend.add_ema_stack(df)
    trend.add_adx(df)
    trend.add_supertrend(df)
    momentum.add_rsi(df)
    momentum.add_macd(df)
    momentum.add_stochrsi(df)
    volatility.add_atr(df)
    volatility.add_bollinger(df)
    volatility.add_keltner(df)
    volume.add_vwap(df)
    volume.add_obv(df)
    volume.add_rvol(df)
    return df.dropna()


def process_pair(symbol: str) -> SignalResult | None:
    log.info("Processing %s", symbol)

    # --- Fetch ---
    try:
        df_trigger = fetcher.fetch_ohlcv(symbol, settings.trigger_timeframe)
        df_primary = fetcher.fetch_ohlcv(symbol, settings.primary_timeframe)
    except Exception as exc:  # noqa: BLE001
        log.warning("Fetch failed for %s: %s — skipping cycle", symbol, exc)
        return None

    # --- Indicators ---
    df_trigger = _apply_indicators(df_trigger)
    df_primary = _apply_indicators(df_primary)

    if len(df_trigger) < 3 or len(df_primary) < 3:
        log.warning("Insufficient data for %s after indicator warmup — skipping", symbol)
        return None

    # --- Evaluate ---
    signal = strategy.evaluate(df_trigger, df_primary)
    log.info("%s → %s (score=%.2f, gainer_prob=%.0f%%)", symbol, signal.direction, signal.composite_score, signal.gainer_score * 100)

    if signal.direction == "NONE":
        # Check if we should invalidate an existing LONG (closed below EMA25)
        last = df_trigger.iloc[-1]
        for direction in ("LONG", "SHORT"):
            if not state_store.is_duplicate(symbol, settings.trigger_timeframe, direction, len(df_trigger)):
                continue
            if direction == "LONG" and last["close"] < last["ema_25"]:
                log.info("Invalidating LONG for %s", symbol)
                telegram_bot.send_invalidation(symbol, direction, last["close"], "Close < EMA25")
                state_store.clear_stale(symbol, settings.trigger_timeframe, direction)
        return signal

    candle_idx = len(df_trigger)

    if state_store.is_duplicate(symbol, settings.trigger_timeframe, signal.direction, candle_idx):
        log.info("Skipping duplicate signal for %s %s", symbol, signal.direction)
        return signal

    # --- Risk ---
    last = signal.last
    risk = risk_manager.calculate(last["close"], last["atr"], signal.direction)

    # --- Notify ---
    telegram_bot.send_entry_signal(
        symbol=symbol,
        signal=signal,
        risk=risk,
        trigger_tf=settings.trigger_timeframe,
        primary_tf=settings.primary_timeframe,
    )

    # --- Record ---
    state_store.record_signal(symbol, settings.trigger_timeframe, signal.direction, candle_idx)
    log.info("Signal emitted for %s %s", symbol, signal.direction)

    time.sleep(1.5)  # Telegram rate-limit buffer between pairs
    return signal


def main() -> None:
    log.info("=== Signal Engine START ===")
    log.info("Pairs: %s | Trigger TF: %s | Primary TF: %s | Threshold: %.2f",
             settings.symbol_pairs, settings.trigger_timeframe,
             settings.primary_timeframe, settings.signal_threshold)

    results = []
    for symbol in settings.symbol_pairs:
        try:
            res = process_pair(symbol)
            if res:
                results.append((symbol, res))
        except Exception:
            log.exception("Unhandled error for %s", symbol)

    # Top Gainer Radar (Koin dengan probabilitas gainer tertinggi >= 50%)
    high_potential = [(sym, sig) for sym, sig in results if sig.gainer_score >= 0.50]
    if high_potential:
        high_potential.sort(key=lambda x: x[1].gainer_score, reverse=True)
        log.info("Sending Top Gainer Radar for %d candidate(s)", len(high_potential))
        telegram_bot.send_gainer_radar(high_potential)

    log.info("=== Signal Engine END ===")


if __name__ == "__main__":
    main()
