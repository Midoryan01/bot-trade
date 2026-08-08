"""
Position sizing, SL/TP calculation.
All pure functions — no side effects, easily unit-tested.
"""
from __future__ import annotations

from dataclasses import dataclass

from config.settings import settings


@dataclass
class RiskResult:
    entry_price: float
    stop_loss: float
    risk_per_unit: float
    risk_percent: float
    take_profits: list[float]   # [tp1, tp2, tp3]
    position_size: float        # in base asset units


def calculate(entry_price: float, atr: float, direction: str = "LONG") -> RiskResult:
    """
    direction: "LONG" or "SHORT"
    All values are positive prices regardless of direction.
    """
    sl_distance = settings.atr_sl_multiplier * atr

    if direction == "LONG":
        stop_loss = entry_price - sl_distance
        take_profits = [entry_price + rrr * sl_distance for rrr in settings.tp_rrr]
    else:  # SHORT
        stop_loss = entry_price + sl_distance
        take_profits = [entry_price - rrr * sl_distance for rrr in settings.tp_rrr]

    risk_per_unit = abs(entry_price - stop_loss)
    risk_percent = (risk_per_unit / entry_price) * 100

    capital_at_risk = settings.account_equity * settings.risk_per_trade_pct
    # ponytail: zero-division guard — ATR can be 0 on flat synthetic data
    position_size = capital_at_risk / risk_per_unit if risk_per_unit > 0 else 0.0

    return RiskResult(
        entry_price=round(entry_price, 8),
        stop_loss=round(stop_loss, 8),
        risk_per_unit=round(risk_per_unit, 8),
        risk_percent=round(risk_percent, 4),
        take_profits=[round(tp, 8) for tp in take_profits],
        position_size=round(position_size, 6),
    )
