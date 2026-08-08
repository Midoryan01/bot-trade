"""Unit tests for indicator math — no network, no mocks needed."""
import numpy as np
import pandas as pd
import pytest

from src.indicators.trend import add_ema_stack, add_adx
from src.indicators.momentum import add_rsi, add_macd
from src.indicators.volatility import add_atr, add_bollinger, add_keltner, is_bb_kc_squeeze
from src.indicators.volume import add_rvol


def _make_df(n: int = 100, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high = close + rng.uniform(0, 2, n)
    low = close - rng.uniform(0, 2, n)
    volume = rng.uniform(1000, 5000, n)
    idx = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": volume}, index=idx)


def test_ema_columns():
    df = add_ema_stack(_make_df(), [15, 25, 50])
    for col in ["ema_15", "ema_25", "ema_50"]:
        assert col in df.columns
    assert df["ema_15"].notna().any()


def test_adx_columns():
    df = add_adx(_make_df())
    for col in ["adx", "dmp", "dmn"]:
        assert col in df.columns


def test_rsi_bounds():
    df = add_rsi(_make_df())
    rsi = df["rsi"].dropna()
    assert ((rsi >= 0) & (rsi <= 100)).all(), "RSI must be 0–100"


def test_macd_columns():
    df = add_macd(_make_df())
    for col in ["macd", "macd_signal", "macd_hist"]:
        assert col in df.columns


def test_atr_positive():
    df = add_atr(_make_df())
    assert (df["atr"].dropna() > 0).all(), "ATR must be positive"


def test_rvol_positive():
    df = add_rvol(_make_df())
    assert (df["rvol"].dropna() > 0).all()


def test_bb_kc_squeeze_returns_series():
    df = _make_df(150)
    add_bollinger(df)
    add_keltner(df)
    df.dropna(inplace=True)
    squeeze = is_bb_kc_squeeze(df)
    assert isinstance(squeeze, pd.Series)
    assert squeeze.dtype == bool
