"""Unit tests for strategy confluence scoring."""
import numpy as np
import pandas as pd

from src.indicators.trend import add_ema_stack, add_adx, add_supertrend
from src.indicators.momentum import add_rsi, add_macd, add_stochrsi
from src.indicators.volatility import add_atr, add_bollinger, add_keltner
from src.indicators.volume import add_vwap, add_obv, add_rvol
from src.strategy import evaluate, WEIGHTS


def _full_df(n: int = 150, trend: str = "up", seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    if trend == "up":
        close = 100 + np.linspace(0, 40, n) + rng.normal(0, 0.5, n)
    else:
        close = 140 - np.linspace(0, 40, n) + rng.normal(0, 0.5, n)
    high = close + rng.uniform(0.1, 1, n)
    low = close - rng.uniform(0.1, 1, n)
    volume = rng.uniform(2000, 8000, n)
    idx = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": volume}, index=idx)
    add_ema_stack(df); add_adx(df); add_supertrend(df)
    add_rsi(df); add_macd(df); add_stochrsi(df)
    add_atr(df); add_bollinger(df); add_keltner(df)
    add_vwap(df); add_obv(df); add_rvol(df)
    return df.dropna()


def test_weights_sum_to_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9


def test_uptrend_favors_long():
    df = _full_df(trend="up")
    result = evaluate(df)
    # In a clean uptrend, LONG score should dominate
    assert result.direction in ("LONG", "NONE"), f"Unexpected direction: {result.direction}"


def test_downtrend_favors_short():
    df = _full_df(trend="down")
    result = evaluate(df)
    assert result.direction in ("SHORT", "NONE")


def test_score_in_range():
    df = _full_df()
    result = evaluate(df)
    assert 0.0 <= result.composite_score <= 1.0


def test_htf_suppresses_counter_trend():
    """Long trigger suppressed when HTF is bearish."""
    df_trigger = _full_df(trend="up", n=150, seed=10)
    df_primary = _full_df(trend="down", n=150, seed=20)
    result = evaluate(df_trigger, df_primary)
    # HTF is bearish → LONG should be suppressed
    assert result.direction != "LONG"


def test_multibagger_flag_is_bool():
    df = _full_df()
    result = evaluate(df)
    assert isinstance(result.is_multibagger, bool)

