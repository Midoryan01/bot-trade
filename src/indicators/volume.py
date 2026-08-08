"""Volume / order-flow indicators: VWAP, OBV, Relative Volume."""
from __future__ import annotations

import pandas as pd
import pandas_ta as ta


def add_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """Session VWAP — resets daily (requires DatetimeIndex with UTC tz)."""
    df["vwap"] = ta.vwap(df["high"], df["low"], df["close"], df["volume"])
    return df


def add_obv(df: pd.DataFrame) -> pd.DataFrame:
    df["obv"] = ta.obv(df["close"], df["volume"])
    return df


def add_rvol(df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
    """
    Relative Volume = current volume / rolling mean of last N candles.
    ponytail: simple rolling mean — upgrade to same-hour-of-day average if RVOL is too noisy.
    """
    df["rvol"] = df["volume"] / df["volume"].rolling(lookback).mean()
    return df
