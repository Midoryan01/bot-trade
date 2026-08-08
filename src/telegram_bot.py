"""
Telegram message formatting & delivery.
Uses HTML parse mode (no MarkdownV2 escaping headaches).
Retry-with-backoff for transient 429 / network failures.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import requests

from config.settings import settings
from src.risk_manager import RiskResult
from src.strategy import SignalResult

log = logging.getLogger(__name__)

_BASE_URL = "https://api.telegram.org/bot{token}/sendMessage"
_MAX_RETRIES = 3


def _send(text: str) -> bool:
    """POST to Telegram with exponential backoff on failure."""
    url = _BASE_URL.format(token=settings.telegram_bot_token)
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            r = requests.post(url, json=payload, timeout=10)
            if r.status_code == 200:
                return True
            log.warning("Telegram returned %d on attempt %d: %s", r.status_code, attempt, r.text[:200])
        except requests.RequestException as exc:
            log.warning("Telegram request failed attempt %d: %s", attempt, exc)
        time.sleep(2 ** attempt)  # 2, 4, 8 seconds
    log.error("Failed to send Telegram message after %d attempts", _MAX_RETRIES)
    return False


def _fmt_price(price: float) -> str:
    """Auto-precision: >100 → 2 dp, else 4 dp."""
    return f"{price:.2f}" if price >= 100 else f"{price:.4f}"


def _factor_emoji(score: float) -> str:
    return "✅" if score == 1.0 else "❌"


def send_entry_signal(
    symbol: str,
    signal: SignalResult,
    risk: RiskResult,
    trigger_tf: str,
    primary_tf: str,
) -> None:
    last = signal.last
    f = signal.factors
    tp1, tp2, tp3 = risk.take_profits
    direction_emoji = "🟢" if signal.direction == "LONG" else "🔴"
    
    mb_banner = "💎 <b>POTENTIAL MULTI-BAGGER ANOMALY DETECTED!</b> 💎\n(High Institutional Volume + Volatility Squeeze Release)\n\n" if signal.is_multibagger else ""

    text = (
        f"{mb_banner}"
        f"🚀 <b>SIGNAL ALERT — {signal.direction}</b> {direction_emoji}\n\n"
        f"<b>Pair:</b> #{symbol.replace('/', '')}\n"
        f"<b>Timeframe:</b> {trigger_tf} (trend: {primary_tf})\n"
        f"<b>Strategy:</b> Multi-Factor Confluence\n"
        f"<b>Confidence Score:</b> {signal.composite_score:.2f}/1.00\n\n"
        "────────────────────────────\n"
        f"📈 <b>Entry Price</b>   : ${_fmt_price(risk.entry_price)}\n"
        f"🛑 <b>Stop Loss</b>     : ${_fmt_price(risk.stop_loss)}  (-{risk.risk_percent:.2f}%)\n"
        f"🎯 <b>TP 1</b>          : ${_fmt_price(tp1)}  (RRR 1:1.5)\n"
        f"🎯 <b>TP 2</b>          : ${_fmt_price(tp2)}  (RRR 1:2.0)\n"
        f"🎯 <b>TP 3</b>          : ${_fmt_price(tp3)}  (RRR 1:3.0, runner)\n"
        f"💰 <b>Suggested Size</b>: {risk.position_size} (1% equity risk)\n"
        "────────────────────────────\n\n"
        "📊 <b>Factor Breakdown:</b>\n"
        f"• {_factor_emoji(f['ema_alignment'])} EMA 15/25/50 Alignment\n"
        f"• {_factor_emoji(f['adx_strength'])} ADX: {last.get('adx', 0):.1f}\n"
        f"• {_factor_emoji(f['rsi_zone'])} RSI: {last.get('rsi', 0):.1f}\n"
        f"• {_factor_emoji(f['macd_cross'])} MACD Cross\n"
        f"• {_factor_emoji(f['squeeze_release'])} BB/Keltner Squeeze Release\n"
        f"• {_factor_emoji(f['vwap_position'])} VWAP Position\n"
        f"• {_factor_emoji(f['volume_rvol'])} Relative Volume: {last.get('rvol', 0):.2f}x\n\n"
        f"⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC\n\n"
        "<i>⚠️ Not financial advice. Always apply your own risk management.</i>"
    )
    _send(text)


def send_invalidation(symbol: str, direction: str, entry_price: float, reason: str) -> None:
    text = (
        "⚠️ <b>SETUP INVALIDATED</b>\n\n"
        f"<b>Pair:</b> #{symbol.replace('/', '')}\n"
        f"<b>Original Signal:</b> {direction} @ ${_fmt_price(entry_price)}\n"
        f"<b>Reason:</b> {reason}\n\n"
        "<i>This setup is no longer active. No further alerts for this instance.</i>"
    )
    _send(text)


# ponytail: send_tp_hit not wired — TP tracking not implemented yet. Wire when state_store tracks open positions.
def send_tp_hit(symbol: str, tp_level: int, entry_price: float, tp_price: float, rrr: float) -> None:
    text = (
        f"🎯 <b>TAKE PROFIT HIT — TP{tp_level}</b>\n\n"
        f"<b>Pair:</b> #{symbol.replace('/', '')}\n"
        f"<b>Entry:</b> ${_fmt_price(entry_price)} → <b>Exit:</b> ${_fmt_price(tp_price)}\n"
        f"<b>Realized RRR:</b> 1:{rrr:.1f}\n"
    )
    _send(text)


def send_gainer_radar(gainer_rankings: list[tuple[str, SignalResult]]) -> None:
    """Kirimkan laporan peringkat Top Gainer Radar ke Telegram."""
    if not gainer_rankings:
        return

    lines = ["🔥 <b>PREDICTED TOMORROW'S TOP GAINER RADAR</b> 🔥\n"]
    lines.append("<i>Pre-breakout momentum & institutional volume scan:</i>\n")

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for idx, (sym, sig) in enumerate(gainer_rankings[:5]):
        medal = medals[idx] if idx < len(medals) else "🔹"
        reasons_str = ", ".join(sig.gainer_reasons) if sig.gainer_reasons else "Accumulation Pattern"
        lines.append(
            f"{medal} <b>#{sym.replace('/', '')}</b> — Score: <b>{int(sig.gainer_score * 100)}%</b>\n"
            f"   ├ Price: ${_fmt_price(sig.last['close'])}\n"
            f"   └ Drivers: <i>{reasons_str}</i>\n"
        )

    lines.append("\n⏰ <b>Scanned At:</b> " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    lines.append("\n⚠️ <i>Pre-breakout radar for educational & analysis purposes only.</i>")
    
    _send("\n".join(lines))

