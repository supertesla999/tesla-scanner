import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.getenv("DB_PATH", "tesla_scanner.db")


def get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS scans (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp        TEXT NOT NULL,
            symbol           TEXT NOT NULL,
            price            REAL,
            sma50            REAL,
            sma100           REAL,
            sma200           REAL,
            sma300           REAL,
            rsi_4h           REAL,
            rsi_1d           REAL,
            stochrsi_k_4h    REAL,
            stochrsi_k_1d    REAL,
            volume_ratio_4h  REAL,
            volume_ratio_1d  REAL
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp  TEXT NOT NULL,
            symbol     TEXT NOT NULL,
            timeframe  TEXT NOT NULL,
            level_name TEXT NOT NULL,
            stage      INTEGER NOT NULL,
            price      REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS alert_state (
            symbol     TEXT NOT NULL,
            timeframe  TEXT NOT NULL,
            level_name TEXT NOT NULL,
            stage      INTEGER NOT NULL,
            PRIMARY KEY (symbol, timeframe, level_name, stage)
        );
    """)
    conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_scan(conn: sqlite3.Connection, symbol: str, d4h: dict, d1d: dict) -> None:
    conn.execute(
        """INSERT INTO scans
           (timestamp, symbol, price, sma50, sma100, sma200, sma300,
            rsi_4h, rsi_1d, stochrsi_k_4h, stochrsi_k_1d, volume_ratio_4h, volume_ratio_1d)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            _now(), symbol,
            d4h.get("price"),
            d4h.get("sma50"), d4h.get("sma100"), d4h.get("sma200"), d4h.get("sma300"),
            d4h.get("rsi"),   d1d.get("rsi"),
            d4h.get("stochrsi_k"), d1d.get("stochrsi_k"),
            d4h.get("volume_ratio"), d1d.get("volume_ratio"),
        ),
    )
    conn.commit()


def log_alert(conn: sqlite3.Connection, symbol: str, timeframe: str,
              level_name: str, stage: int, price: float) -> None:
    conn.execute(
        "INSERT INTO alerts (timestamp, symbol, timeframe, level_name, stage, price) VALUES (?,?,?,?,?,?)",
        (_now(), symbol, timeframe, level_name, stage, price),
    )
    conn.commit()


def get_active_alerts(conn: sqlite3.Connection, symbol: str, timeframe: str) -> set:
    rows = conn.execute(
        "SELECT level_name, stage FROM alert_state WHERE symbol=? AND timeframe=?",
        (symbol, timeframe),
    ).fetchall()
    return {(r["level_name"], r["stage"]) for r in rows}


def set_alert_active(conn: sqlite3.Connection, symbol: str, timeframe: str,
                     level_name: str, stage: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO alert_state (symbol, timeframe, level_name, stage) VALUES (?,?,?,?)",
        (symbol, timeframe, level_name, stage),
    )
    conn.commit()


def clear_alert(conn: sqlite3.Connection, symbol: str, timeframe: str,
                level_name: str, stage: int) -> None:
    conn.execute(
        "DELETE FROM alert_state WHERE symbol=? AND timeframe=? AND level_name=? AND stage=?",
        (symbol, timeframe, level_name, stage),
    )
    conn.commit()
