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


# ── Alert lines (flat — no priority tiers) ────────────────────────────────────

def weekly_sma_line(symbol: str, period: int, elapsed_hours: float) -> str:
    name = symbol.replace("USDT", "")
    hrs = int(round(elapsed_hours))
    when = "just now" if hrs <= 0 else f"{hrs}h ago"
    return f"🚨 {name} — Weekly SMA{period} hit ({when})"


def sr_line(symbol: str, cond: dict) -> str:
    name = symbol.replace("USDT", "")
    price_str = _fmt_price(cond["level_price"])
    role = cond["role"]
    dist = cond["distance_pct"]
    direction = "above" if dist > 0 else "below"
    if cond["stage"] == 1:
        return f"🚨 {name} — Approaching {role} {price_str} ({abs(dist):.2f}% {direction})"
    return f"🚨 {name} — HIT {role} {price_str}"


# ── Monitoring snapshot tables (display only — never alert) ───────────────────

_SNAP_FMT = "{:<5}{:<10}{:<7}{:<7}{:<7}{:<7}{:<6}{:<6}{:<7}{:<6}"
_SNAP_HEADER = _SNAP_FMT.format(
    "Pair", "Price", "SMA50", "SMA100", "SMA200", "SMA300", "Vol", "RSI", "StochK", "StochD"
)


def _fmt_table_price(p) -> str:
    if p is None:
        return "n/a"
    if p >= 1000:
        return f"{p:,.0f}"
    if p >= 1:
        return f"{p:,.2f}"
    return f"{p:.4f}"


def _dist(sma, price) -> str:
    """Signed % distance of the SMA from price: (sma - price) / price * 100."""
    if sma is None or not price:
        return "n/a"
    return f"{(sma - price) / price * 100:+.1f}%"


def _fmt_num(v, decimals: int) -> str:
    if v is None:
        return "n/a"
    return f"{v:.{decimals}f}"


def format_snapshot(tf_label: str, rows: list, ts_str: str) -> str:
    """rows = list of (symbol, current_price, indicator_dict). One live price is
    used for both tables so the same coin can't show two different prices."""
    lines = [_SNAP_HEADER]
    for symbol, price, d in rows:
        lines.append(_SNAP_FMT.format(
            symbol.replace("USDT", ""),
            _fmt_table_price(price),
            _dist(d.get("sma50"), price),
            _dist(d.get("sma100"), price),
            _dist(d.get("sma200"), price),
            _dist(d.get("sma300"), price),
            _fmt_num(d.get("volume_ratio"), 2),
            _fmt_num(d.get("rsi"), 1),
            _fmt_num(d.get("stochrsi_k"), 1),
            _fmt_num(d.get("stochrsi_d"), 1),
        ))
    table = "\n".join(lines)
    return f"📊 {tf_label} SNAPSHOT — {ts_str}\n```\n{table}\n```"
