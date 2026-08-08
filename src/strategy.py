"""
Confluence scoring & entry/exit logic.

Each sub-score returns 0.0 or 1.0 (binary). Weights sum to 1.0.
composite_score >= SIGNAL_THRESHOLD → emit signal.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from config.settings import settings
from src.indicators.volatility import is_bb_kc_squeeze


@dataclass
class SignalResult:
    direction: str          # "LONG" | "SHORT" | "NONE"
    composite_score: float
    factors: dict[str, float]   # factor name → sub-score (0 or 1)
    last: pd.Series             # last completed candle
    is_multibagger: bool = False  # Anomaly tag: High Volume Spike + Squeeze Breakout
    gainer_score: float = 0.0     # Probabilitas Pre-Breakout Top Gainer (0.0 - 1.0)
    gainer_reasons: list[str] = None  # Alasan pendukung prediksi gainer




def _score_ema(row: pd.Series, direction: str) -> float:
    e15, e25, e50 = row["ema_15"], row["ema_25"], row["ema_50"]
    if direction == "LONG":
        return 1.0 if (e15 > e25 > e50 and row["close"] > e15) else 0.0
    return 1.0 if (e15 < e25 < e50 and row["close"] < e15) else 0.0


def _score_adx(row: pd.Series, direction: str) -> float:
    if row["adx"] <= 20:
        return 0.0
    return 1.0 if (direction == "LONG" and row["dmp"] > row["dmn"]) else (
        1.0 if (direction == "SHORT" and row["dmn"] > row["dmp"]) else 0.0
    )


def _score_rsi(row: pd.Series, direction: str) -> float:
    rsi = row["rsi"]
    if direction == "LONG":
        return 1.0 if 45 <= rsi <= 62 else 0.0
    return 1.0 if 38 <= rsi <= 55 else 0.0  # mirror zone for shorts


def _score_macd(row: pd.Series, prev: pd.Series, direction: str) -> float:
    if direction == "LONG":
        return 1.0 if (row["macd"] > row["macd_signal"] and row["macd_hist"] > prev["macd_hist"]) else 0.0
    return 1.0 if (row["macd"] < row["macd_signal"] and row["macd_hist"] < prev["macd_hist"]) else 0.0


def _score_squeeze_release(df: pd.DataFrame, direction: str) -> float:
    """Squeeze was active on prev candle, released on current = breakout."""
    squeeze = is_bb_kc_squeeze(df)
    prev_squeeze = squeeze.iloc[-2] if len(squeeze) >= 2 else False
    curr_squeeze = squeeze.iloc[-1]
    if prev_squeeze and not curr_squeeze:
        # Confirm direction of breakout
        last = df.iloc[-1]
        return 1.0 if (direction == "LONG" and last["close"] > last["bb_mid"]) else (
            1.0 if (direction == "SHORT" and last["close"] < last["bb_mid"]) else 0.0
        )
    return 0.0


def _score_vwap(row: pd.Series, direction: str) -> float:
    if direction == "LONG":
        return 1.0 if row["close"] > row["vwap"] else 0.0
    return 1.0 if row["close"] < row["vwap"] else 0.0


def _score_rvol(row: pd.Series) -> float:
    return 1.0 if row["rvol"] >= settings.rvol_threshold else 0.0


WEIGHTS = {
    "ema_alignment": 0.25,
    "adx_strength":  0.15,
    "rsi_zone":      0.15,
    "macd_cross":    0.15,
    "squeeze_release": 0.10,
    "vwap_position": 0.10,
    "volume_rvol":   0.10,
}


def _compute(df: pd.DataFrame, direction: str) -> SignalResult:
    last = df.iloc[-1]
    prev = df.iloc[-2]

    factors = {
        "ema_alignment":   _score_ema(last, direction),
        "adx_strength":    _score_adx(last, direction),
        "rsi_zone":        _score_rsi(last, direction),
        "macd_cross":      _score_macd(last, prev, direction),
        "squeeze_release": _score_squeeze_release(df, direction),
        "vwap_position":   _score_vwap(last, direction),
        "volume_rvol":     _score_rvol(last),
    }

    score = sum(WEIGHTS[k] * v for k, v in factors.items())
    
    # Anomaly Multi-Bagger Detector:
    is_mb = bool(
        last.get("rvol", 0) >= 2.5
        and factors["squeeze_release"] == 1.0
        and last.get("adx", 0) >= 20
    )

    # Top Gainer Predictor Scoring (Pre-Breakout Momentum):
    gainer_reasons = []
    g_score = 0.0

    # 1. Volume Accumulation (30%)
    if last.get("rvol", 0) >= 2.0:
        g_score += 0.30
        gainer_reasons.append(f"Volume Surge ({last.get('rvol', 0):.1f}x avg)")
    elif last.get("rvol", 0) >= 1.3:
        g_score += 0.15

    # 2. Volatility Compression / Squeeze (30%)
    if factors["squeeze_release"] == 1.0:
        g_score += 0.30
        gainer_reasons.append("Volatility Squeeze Breakout")
    elif is_bb_kc_squeeze(df).iloc[-1]:
        g_score += 0.20
        gainer_reasons.append("Coiling Squeeze (Pre-Explosive)")

    # 3. Strong Trend & Directional Bias (20%)
    if factors["ema_alignment"] == 1.0 and last.get("adx", 0) > 20:
        g_score += 0.20
        gainer_reasons.append("Bullish Trend Expansion")

    # 4. Momentum Acceleration (20%)
    if factors["macd_cross"] == 1.0:
        g_score += 0.20
        gainer_reasons.append("MACD Momentum Acceleration")

    return SignalResult(
        direction=direction,
        composite_score=round(score, 4),
        factors=factors,
        last=last,
        is_multibagger=is_mb,
        gainer_score=round(g_score, 2),
        gainer_reasons=gainer_reasons
    )


def evaluate(df_trigger: pd.DataFrame, df_primary: pd.DataFrame | None = None) -> SignalResult:
    """
    Multi-timeframe: if df_primary supplied, suppress trigger signals
    that conflict with the higher-timeframe trend.
    """
    # Determine primary-timeframe trend bias (EMA stack + ADX)
    htf_bias = "NEUTRAL"
    if df_primary is not None and not df_primary.empty:
        p = df_primary.iloc[-1]
        if p["ema_15"] > p["ema_25"] > p["ema_50"] and p["adx"] > 20:
            htf_bias = "LONG"
        elif p["ema_15"] < p["ema_25"] < p["ema_50"] and p["adx"] > 20:
            htf_bias = "SHORT"

    # Only score directions not suppressed by HTF bias
    candidates = []
    if htf_bias != "SHORT":
        candidates.append(_compute(df_trigger, "LONG"))
    if htf_bias != "LONG":
        candidates.append(_compute(df_trigger, "SHORT"))

    best = max(candidates, key=lambda r: r.composite_score)

    if best.composite_score < settings.signal_threshold:
        return SignalResult("NONE", best.composite_score, best.factors, best.last)

    return best

