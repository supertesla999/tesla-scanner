PAIRS = {
    "BTCUSDT":  {"threshold_pct": 0.5},
    "ETHUSDT":  {"threshold_pct": 1.0},
    "BNBUSDT":  {"threshold_pct": 1.0},
    "SOLUSDT":  {"threshold_pct": 1.0},
    "TRXUSDT":  {"threshold_pct": 1.0},
}

TIMEFRAMES = ["4h", "1d", "1w"]

# Flat list of price levels per pair.
# Role (support / resistance) is determined dynamically at scan time
# by comparing current price against each level — no pre-classification needed.
LEVELS = {
    "BTCUSDT": [65000, 62000, 68500, 71000],
    "ETHUSDT": [3200, 3000, 3600, 3800],
    "BNBUSDT": [],
    "SOLUSDT": [],
    "TRXUSDT": [],
}

MA_CROSS_PAIRS = [(50, 100), (50, 200), (50, 300), (100, 200), (100, 300)]
