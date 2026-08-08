"""Market data acquisition — CCXT wrapper with multi-exchange fallback."""
from __future__ import annotations

import logging

import ccxt
import pandas as pd

log = logging.getLogger(__name__)

# List exchange fallback berurutan berdasarkan aksesibilitas ISP lokal
EXCHANGE_CLASSES = [ccxt.okx, ccxt.kucoin, ccxt.gate, ccxt.binance]

def fetch_ohlcv(symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
    """
    Fetch OHLCV candles dengan fallback otomatis antar exchange jika terkena block / timeout.
    Returns DataFrame indexed by UTC datetime.
    """
    last_exception = None

    for exchange_cls in EXCHANGE_CLASSES:
        exchange_name = exchange_cls.__name__
        try:
            log.debug("Mencoba fetch %s %s via %s...", symbol, timeframe, exchange_name)
            exchange = exchange_cls({"enableRateLimit": True, "timeout": 8000})
            
            raw = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not raw:
                continue

            df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df.set_index("timestamp", inplace=True)
            df = df.astype(float)

            log.info("Berhasil fetch %s %s dari %s (%d candles)", symbol, timeframe, exchange_name, len(df) - 1)
            # Drop candle terakhir yang belum closed
            return df.iloc[:-1]

        except Exception as exc:  # noqa: BLE001
            last_exception = exc
            log.warning("Fetch via %s gagal (%s), mencoba exchange berikutnya...", exchange_name, str(exc)[:60])

    raise ValueError(f"Gagal fetch {symbol}/{timeframe} dari semua exchange. Error terakhir: {last_exception}")

