import logging
import os

import requests

log = logging.getLogger(__name__)


def _fmt_price(p: float) -> str:
    if p >= 1000:
        return f"${p:,.2f}"
    if p >= 1:
        return f"${p:.4f}"
    return f"${p:.6f}"


def _ctx(d4h: dict, d1d: dict) -> str:
    return (
        f"RSI: {d4h['rsi']} (4H) / {d1d['rsi']} (1D)\n"
        f"StochRSI: {d4h['stochrsi_k']} (4H) / {d1d['stochrsi_k']} (1D)\n"
        f"Vol: {d4h['volume_ratio']}x (4H) / {d1d['volume_ratio']}x (1D)"
    )


def _send(text: str) -> None:
    """Send to all configured notification channels."""
    _send_telegram(text)
    _send_discord(text)


def _send_telegram(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=10,
    )
    if not resp.ok:
        log.error("Telegram %s: %s", resp.status_code, resp.text[:200])


def _send_discord(text: str) -> None:
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        return
    resp = requests.post(url, json={"content": text}, timeout=10)
    if not resp.ok:
        log.error("Discord %s: %s", resp.status_code, resp.text[:200])


def send_ma_alert(symbol: str, tf: str, cond: dict, d4h: dict, d1d: dict) -> None:
    price_str = _fmt_price(cond["level_price"])
    dist = cond["distance_pct"]
    direction = "above" if dist > 0 else "below"

    if cond["stage"] == 1:
        header = f"⚠️ {symbol} — {tf}"
        body = (
            f"Approaching: {cond['level_name']} @ {price_str}\n"
            f"Distance: {abs(dist):.2f}% {direction}"
        )
    else:
        header = f"🔴 {symbol} — {tf}"
        body = f"HIT: {cond['level_name']} @ {price_str}"

    _send(f"{header}\n{body}\n{_ctx(d4h, d1d)}")


def send_sr_alert(symbol: str, cond: dict, d4h: dict, d1d: dict) -> None:
    price_str = _fmt_price(cond["level_price"])
    dist = cond["distance_pct"]
    direction = "above" if dist > 0 else "below"
    role = cond["role"]

    if cond["stage"] == 1:
        header = f"⚠️ {symbol}"
        body = (
            f"Approaching {role}: {price_str}\n"
            f"Distance: {abs(dist):.2f}% {direction}"
        )
    else:
        header = f"🔴 {symbol}"
        body = f"HIT {role}: {price_str}"

    _send(f"{header}\n{body}\n{_ctx(d4h, d1d)}")


def send_crossover_alert(symbol: str, tf: str, cross: dict, d4h: dict, d1d: dict) -> None:
    is_bull = cross["direction"] == "bullish"
    emoji = "🟢" if is_bull else "🔴"
    side = "above" if is_bull else "below"
    header = f"{emoji} {symbol} — {tf}"
    body = f"{cross['direction'].capitalize()} Cross: SMA{cross['fast']} crossed {side} SMA{cross['slow']}"
    _send(f"{header}\n{body}\n{_ctx(d4h, d1d)}")
