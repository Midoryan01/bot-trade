# Crypto Signal Bot

Automated crypto technical-analysis signal bot. Runs free on GitHub Actions (cron every 15 min), pushes alerts to Telegram.

## Architecture

```
Scheduler → Fetcher (CCXT/Binance) → Indicators → Strategy (confluence score)
         → Risk Manager (ATR SL/TP) → State Store (dedup) → Telegram Bot
```

## Quick Start

### 1. Clone & configure

```bash
cp .env.example .env
# Fill in TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
```

### 2. Install

```bash
pip install -r requirements.txt
```

### 3. Run locally

```bash
python src/main.py
```

### 4. Deploy to GitHub Actions

1. Push to GitHub.
2. Add secrets: **Settings → Secrets → Actions**
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `ACCOUNT_EQUITY` (optional, default 10000)
   - `RISK_PER_TRADE_PCT` (optional, default 0.01)
3. The `signal_cron.yml` workflow runs automatically every 15 minutes.

### 5. Run tests

```bash
pytest tests/ -v
```

## Configuration

Edit `config/settings.yaml` to tune thresholds — no code changes needed:

| Key | Default | Description |
|-----|---------|-------------|
| `signal_threshold` | 0.70 | Minimum composite score to emit a signal |
| `atr_sl_multiplier` | 1.5 | ATR multiplier for stop-loss distance |
| `tp_rrr` | [1.5, 2.0, 3.0] | Risk-to-reward ratios for TP1/2/3 |
| `cooldown_candles` | 4 | Min candles between repeated alerts per pair |
| `rvol_threshold` | 1.5 | Relative volume threshold for volume score |

## Signal Logic

Multi-factor confluence score (must be ≥ 0.70 to fire):

| Factor | Weight |
|--------|--------|
| EMA 15/25/50 alignment | 25% |
| ADX strength | 15% |
| RSI zone | 15% |
| MACD cross | 15% |
| BB/Keltner squeeze release | 10% |
| VWAP position | 10% |
| Relative volume (RVOL) | 10% |

**Multi-timeframe**: 1h trend must agree with the 15m trigger direction. Counter-trend signals are suppressed.

## Disclaimer

Not financial advice. Always apply your own risk management.
