"""Momentum indicators: RSI, MACD, Stochastic RSI."""
from __future__ import annotations

import pandas as pd
import pandas_ta as ta


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    df["rsi"] = ta.rsi(df["close"], length=period)
    return df


def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    macd = ta.macd(df["close"], fast=fast, slow=slow, signal=signal)
    if macd is not None:
        df["macd"] = macd[f"MACD_{fast}_{slow}_{signal}"]
        df["macd_signal"] = macd[f"MACDs_{fast}_{slow}_{signal}"]
        df["macd_hist"] = macd[f"MACDh_{fast}_{slow}_{signal}"]
    return df


def add_stochrsi(
    df: pd.DataFrame, period: int = 14, smooth_k: int = 3, smooth_d: int = 3
) -> pd.DataFrame:
    srsi = ta.stochrsi(df["close"], length=period, rsi_length=period, k=smooth_k, d=smooth_d)
    if srsi is not None:
        k_col = next(c for c in srsi.columns if "STOCHRSIk" in c)
        d_col = next(c for c in srsi.columns if "STOCHRSId" in c)
        df["stochrsi_k"] = srsi[k_col]
        df["stochrsi_d"] = srsi[d_col]
    return df
