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

# (header, column width). Flaggable columns are padded wide enough to leave room
# for a 🔴 flag, which renders ~2 monospace cells.
_COLS = [
    ("Pair", 5), ("Price", 10),
    ("SMA50", 8), ("SMA100", 8), ("SMA200", 8), ("SMA300", 8),
    ("Vol", 8), ("RSI", 8), ("StochK", 8), ("StochD", 8),
]

FLAG = "🔴"

# SMA-distance flag threshold (|distance| <= this); tighter for BTC/TRX per spec.
_SMA_FLAG_PCT = {"BTCUSDT": 0.5, "TRXUSDT": 0.5}
_SMA_FLAG_DEFAULT = 1.0


def _vlen(s: str) -> int:
    """Monospace display width; the 🔴 flag renders ~2 cells but len() counts 1."""
    return len(s) + s.count(FLAG)


def _cell(s: str, width: int) -> str:
    """Left-justify to a display width that accounts for the wide 🔴 flag."""
    return s + " " * max(1, width - _vlen(s))


def _row(cells: list) -> str:
    return "".join(_cell(c, w) for c, (_, w) in zip(cells, _COLS)).rstrip()


def _fmt_table_price(p) -> str:
    if p is None:
        return "n/a"
    if p >= 1000:
        return f"{p:,.0f}"
    if p >= 1:
        return f"{p:,.2f}"
    return f"{p:.4f}"


def _dist_cell(sma, price, flag_pct: float) -> str:
    """Signed % distance of the SMA from price, flagged if |distance| <= flag_pct."""
    if sma is None or not price:
        return "n/a"
    dist = (sma - price) / price * 100
    s = f"{dist:+.1f}%"
    return FLAG + s if abs(dist) <= flag_pct else s


def _vol_cell(v) -> str:
    if v is None:
        return "n/a"
    s = f"{v:.2f}"
    return FLAG + s if v > 2.0 else s


def _rsi_cell(v) -> str:
    if v is None:
        return "n/a"
    s = f"{v:.1f}"
    return FLAG + s if (v < 30 or v > 70) else s


def _stoch_cell(v) -> str:
    if v is None:
        return "n/a"
    s = f"{v:.1f}"
    return FLAG + s if (v < 20 or v > 80) else s


def format_snapshot(tf_label: str, rows: list, ts_str: str) -> str:
    """rows = list of (symbol, current_price, indicator_dict). One live price is
    used for both tables so the same coin can't show two different prices.
    Values that breach their threshold are prefixed with 🔴."""
    lines = [_row([name for name, _ in _COLS])]
    for symbol, price, d in rows:
        flag_pct = _SMA_FLAG_PCT.get(symbol, _SMA_FLAG_DEFAULT)
        lines.append(_row([
            symbol.replace("USDT", ""),
            _fmt_table_price(price),
            _dist_cell(d.get("sma50"), price, flag_pct),
            _dist_cell(d.get("sma100"), price, flag_pct),
            _dist_cell(d.get("sma200"), price, flag_pct),
            _dist_cell(d.get("sma300"), price, flag_pct),
            _vol_cell(d.get("volume_ratio")),
            _rsi_cell(d.get("rsi")),
            _stoch_cell(d.get("stochrsi_k")),
            _stoch_cell(d.get("stochrsi_d")),
        ]))
    table = "\n".join(lines)
    return f"📊 {tf_label} SNAPSHOT — {ts_str}\n```\n{table}\n```"
