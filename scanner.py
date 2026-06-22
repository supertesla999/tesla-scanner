import argparse
import logging
import time
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
load_dotenv()

from config import LEVELS, PAIRS, TIMEFRAMES, WEEKLY_SMA_THRESHOLD_PCT
from indicators import compute_indicators, fetch_price
from conditions import check_sr_conditions
import alerts
import storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

SCAN_INTERVAL_SECONDS = 3600   # hourly
WEEKLY_WINDOW_HOURS = 24       # weekly-SMA alerts repeat for this long after a hit
IST = timezone(timedelta(hours=5, minutes=30))  # snapshot headers shown in IST


def _process_weekly_sma(conn, symbol, period, sma, price, now):
    """Weekly-SMA alert with a 24h sticky-repeat window.

    Returns an alert line (str) to emit this scan, or None. Once a weekly SMA
    comes within 1% of price, it re-emits every scan for 24h with elapsed time,
    then stops. A later re-hit (after price leaves the band) starts a fresh cycle.
    """
    if sma is None:
        return None
    within = abs((sma - price) / sma) * 100 <= WEEKLY_SMA_THRESHOLD_PCT
    rec_ts = storage.get_weekly_hit(conn, symbol, period)

    if rec_ts is None:
        if within:
            storage.set_weekly_hit(conn, symbol, period, now.isoformat())
            return alerts.weekly_sma_line(symbol, period, 0.0)
        return None

    age_h = (now - datetime.fromisoformat(rec_ts)).total_seconds() / 3600.0
    if age_h < WEEKLY_WINDOW_HOURS:
        return alerts.weekly_sma_line(symbol, period, age_h)

    # 24h window elapsed → stop repeating. Reset once price leaves the band so a
    # later re-entry starts a fresh cycle.
    if not within:
        storage.clear_weekly_hit(conn, symbol, period)
    return None


def scan_once(conn) -> None:
    now = datetime.now(timezone.utc)
    weekly_lines = []
    sr_lines = []
    snap_1d = []
    snap_4h = []

    for symbol, cfg in PAIRS.items():
        log.info("Scanning %s", symbol)
        try:
            tf_data = {tf: compute_indicators(symbol, tf) for tf in TIMEFRAMES}
            live_price = fetch_price(symbol)
        except Exception as exc:
            log.error("%s — fetch failed: %s", symbol, exc)
            continue

        d4h = tf_data["4h"]
        d1d = tf_data["1d"]
        d1w = tf_data["1w"]
        storage.log_scan(conn, symbol, d4h, d1d)

        # ── ALERT 1: Weekly SMA hits (1% flat threshold, 24h sticky repeat) ──
        for period in (50, 100, 200, 300):
            line = _process_weekly_sma(
                conn, symbol, period, d1w.get(f"sma{period}"), live_price, now
            )
            if line:
                weekly_lines.append(line)

        # ── ALERT 2: S/R hits (existing one-shot dedup, per-pair threshold) ──
        sr_threshold = cfg["sr_threshold_pct"]
        sr_new = check_sr_conditions(
            d4h["price"], d4h["high"], d4h["low"], d4h["prev_price"],
            LEVELS.get(symbol, []), sr_threshold,
        )
        sr_new_keys = {(c["level_name"], c["stage"]) for c in sr_new}
        sr_stored = storage.get_active_alerts(conn, symbol, "SR")

        for key in sr_stored:
            if key not in sr_new_keys:
                storage.clear_alert(conn, symbol, "SR", key[0], key[1])

        for cond in sr_new:
            key = (cond["level_name"], cond["stage"])
            if key not in sr_stored:
                sr_lines.append(alerts.sr_line(symbol, cond))
                storage.set_alert_active(conn, symbol, "SR", key[0], key[1])
                storage.log_alert(conn, symbol, "SR", key[0], key[1], d4h["price"])

        # ── Monitoring snapshots (display only, never alert) ─────────────────
        snap_1d.append((symbol, live_price, d1d))
        snap_4h.append((symbol, live_price, d4h))

    # ── Send to Discord, in order: alerts → 1D table → 4H table ──────────────
    alert_lines = weekly_lines + sr_lines
    if alert_lines:
        alerts._send_discord("\n".join(alert_lines))

    ts_str = now.astimezone(IST).strftime("%d %b %Y %H:%M IST")
    alerts._send_discord(alerts.format_snapshot("1D", snap_1d, ts_str))
    alerts._send_discord(alerts.format_snapshot("4H", snap_4h, ts_str))


def main() -> None:
    parser = argparse.ArgumentParser(description="Tesla crypto market scanner")
    parser.add_argument("--once", action="store_true", help="Run one scan and exit")
    args = parser.parse_args()

    conn = storage.get_conn()
    storage.init_db(conn)

    scan_once(conn)
    if args.once:
        conn.close()
        return

    while True:
        time.sleep(SCAN_INTERVAL_SECONDS)
        scan_once(conn)


if __name__ == "__main__":
    main()
