"""Volatility indicators: ATR, Bollinger Bands, Keltner Channels."""
from __future__ import annotations

import pandas as pd
import pandas_ta as ta


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=period)
    return df


def add_bollinger(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> pd.DataFrame:
    bb = ta.bbands(df["close"], length=period, std=std)
    if bb is not None:
        # Column names vary by pandas-ta version (e.g. BBU_20_2.0 vs BBU_20_2.0_2.0)
        # Use startswith discovery to stay version-agnostic.
        cols = bb.columns.tolist()
        df["bb_upper"] = bb[[c for c in cols if c.startswith("BBU_")][0]]
        df["bb_mid"]   = bb[[c for c in cols if c.startswith("BBM_")][0]]
        df["bb_lower"] = bb[[c for c in cols if c.startswith("BBL_")][0]]
        df["bb_width"] = bb[[c for c in cols if c.startswith("BBB_")][0]]
    return df


def add_keltner(df: pd.DataFrame, period: int = 20, atr_mult: float = 1.5) -> pd.DataFrame:
    kc = ta.kc(df["high"], df["low"], df["close"], length=period, scalar=atr_mult)
    if kc is not None:
        cols = kc.columns.tolist()
        df["kc_upper"] = kc[[c for c in cols if c.startswith("KCUe_")][0]]
        df["kc_lower"] = kc[[c for c in cols if c.startswith("KCLe_")][0]]
    return df


def is_bb_kc_squeeze(df: pd.DataFrame) -> pd.Series:
    """
    True on rows where Bollinger Bands are inside Keltner Channels
    (TTM-Squeeze style volatility compression).
    Requires add_bollinger and add_keltner to have run first.
    """
    return (df["bb_upper"] <= df["kc_upper"]) & (df["bb_lower"] >= df["kc_lower"])
