"""Trend indicators: EMA stack, ADX, Supertrend."""
from __future__ import annotations

import pandas as pd
import pandas_ta as ta


def add_ema_stack(df: pd.DataFrame, periods: list[int] = (15, 25, 50)) -> pd.DataFrame:
    """Add EMA columns: ema_15, ema_25, ema_50 (or whatever periods are given)."""
    for p in periods:
        df[f"ema_{p}"] = ta.ema(df["close"], length=p)
    return df


def add_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Add adx, dmp (DI+), dmn (DI-) columns."""
    adx = ta.adx(df["high"], df["low"], df["close"], length=period)
    if adx is not None:
        df["adx"] = adx[f"ADX_{period}"]
        df["dmp"] = adx[f"DMP_{period}"]
        df["dmn"] = adx[f"DMN_{period}"]
    return df


def add_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
    """Add supertrend direction column: 1 = bullish, -1 = bearish."""
    st = ta.supertrend(df["high"], df["low"], df["close"], length=period, multiplier=multiplier)
    if st is not None:
        col = next(c for c in st.columns if c.startswith("SUPERTd"))
        df["supertrend_dir"] = st[col]
    return df
