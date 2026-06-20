import argparse
import logging
import time

from dotenv import load_dotenv
load_dotenv()

from config import LEVELS, MA_CROSS_PAIRS, PAIRS, TIMEFRAMES
from indicators import compute_indicators
from conditions import check_crossovers, check_ma_conditions, check_sr_conditions
import alerts
import storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)


def scan_once(conn) -> None:
    for symbol, cfg in PAIRS.items():
        threshold = cfg["threshold_pct"]
        log.info("Scanning %s", symbol)

        try:
            tf_data = {tf: compute_indicators(symbol, tf) for tf in TIMEFRAMES}
        except Exception as exc:
            log.error("%s — fetch failed: %s", symbol, exc)
            continue

        d4h = tf_data["4h"]
        d1d = tf_data["1d"]
        storage.log_scan(conn, symbol, d4h, d1d)

        # ── MA proximity + crossovers (per timeframe) ─────────────────────────
        for tf in TIMEFRAMES:
            data = tf_data[tf]
            tf_label = tf.upper()

            # MA proximity
            new_ma = check_ma_conditions(data, threshold)
            new_ma_keys = {(c["level_name"], c["stage"]) for c in new_ma}
            stored_ma = storage.get_active_alerts(conn, symbol, tf)

            for key in stored_ma:
                if key not in new_ma_keys:
                    storage.clear_alert(conn, symbol, tf, key[0], key[1])

            for cond in new_ma:
                key = (cond["level_name"], cond["stage"])
                if key not in stored_ma:
                    alerts.send_ma_alert(symbol, tf_label, cond, d4h, d1d)
                    storage.set_alert_active(conn, symbol, tf, key[0], key[1])
                    storage.log_alert(conn, symbol, tf, key[0], key[1], data["price"])

            # Crossovers — stored under a separate "tf_cross" key to avoid
            # being wiped by the MA proximity clearing logic above
            tf_cross = tf + "_cross"
            stored_cross = storage.get_active_alerts(conn, symbol, tf_cross)

            for cross in check_crossovers(data):
                dir_short = cross["direction"][:4]  # "bull" or "bear"
                level_name = f"{cross['level_name']}_{dir_short}"
                key = (level_name, 3)
                if key not in stored_cross:
                    alerts.send_crossover_alert(symbol, tf_label, cross, d4h, d1d)
                    storage.set_alert_active(conn, symbol, tf_cross, level_name, 3)
                    storage.log_alert(conn, symbol, tf_cross, level_name, 3, data["price"])

            # When fast flips above/below slow, clear the opposite direction's
            # dedup so the next reversal can fire again
            for fast, slow in MA_CROSS_PAIRS:
                cf = data.get(f"sma{fast}")
                cs = data.get(f"sma{slow}")
                if cf is not None and cs is not None:
                    opposite = "bear" if cf > cs else "bull"
                    storage.clear_alert(conn, symbol, tf_cross, f"X{fast}_{slow}_{opposite}", 3)

        # ── S/R levels (once per pair, using 4H candle) ──────────────────────
        sr_new = check_sr_conditions(
            d4h["price"], d4h["high"], d4h["low"], d4h["prev_price"],
            LEVELS.get(symbol, []), threshold,
        )
        sr_new_keys = {(c["level_name"], c["stage"]) for c in sr_new}
        sr_stored = storage.get_active_alerts(conn, symbol, "SR")

        for key in sr_stored:
            if key not in sr_new_keys:
                storage.clear_alert(conn, symbol, "SR", key[0], key[1])

        for cond in sr_new:
            key = (cond["level_name"], cond["stage"])
            if key not in sr_stored:
                alerts.send_sr_alert(symbol, cond, d4h, d1d)
                storage.set_alert_active(conn, symbol, "SR", key[0], key[1])
                storage.log_alert(conn, symbol, "SR", key[0], key[1], d4h["price"])


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
        time.sleep(900)
        scan_once(conn)


if __name__ == "__main__":
    main()
