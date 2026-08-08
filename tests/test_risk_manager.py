"""Unit tests for risk manager."""
import pytest
from src.risk_manager import calculate


def test_long_sl_below_entry():
    r = calculate(entry_price=50000.0, atr=500.0, direction="LONG")
    assert r.stop_loss < r.entry_price


def test_short_sl_above_entry():
    r = calculate(entry_price=50000.0, atr=500.0, direction="SHORT")
    assert r.stop_loss > r.entry_price


def test_tp_order_long():
    r = calculate(entry_price=50000.0, atr=500.0, direction="LONG")
    tp1, tp2, tp3 = r.take_profits
    assert tp1 < tp2 < tp3


def test_tp_order_short():
    r = calculate(entry_price=50000.0, atr=500.0, direction="SHORT")
    tp1, tp2, tp3 = r.take_profits
    assert tp1 > tp2 > tp3


def test_position_size_positive():
    r = calculate(entry_price=100.0, atr=2.0, direction="LONG")
    assert r.position_size > 0


def test_zero_atr_no_crash():
    r = calculate(entry_price=100.0, atr=0.0, direction="LONG")
    assert r.position_size == 0.0


def test_risk_percent_positive():
    r = calculate(entry_price=50000.0, atr=500.0)
    assert r.risk_percent > 0
