PAIRS = {
    "BTCUSDT":  {"sr_threshold_pct": 0.5},
    "ETHUSDT":  {"sr_threshold_pct": 1.0},
    "BNBUSDT":  {"sr_threshold_pct": 1.0},
    "SOLUSDT":  {"sr_threshold_pct": 1.0},
    "TRXUSDT":  {"sr_threshold_pct": 0.5},
}

# Weekly-SMA alerts use one flat proximity threshold for every pair.
WEEKLY_SMA_THRESHOLD_PCT = 1.0

TIMEFRAMES = ["4h", "1d", "1w"]

# Flat list of price levels per pair.
# Role (support / resistance) is determined dynamically at scan time
# by comparing current price against each level — no pre-classification needed.
LEVELS = {
    "BTCUSDT": [67245.33, 65642.68, 63796.62, 62307.05],
    "ETHUSDT": [1963.56, 1820.00, 1726.62, 1680.35, 1538.03],
    "BNBUSDT": [711.12, 686.91, 585.41, 570.85],
    "SOLUSDT": [97.59, 75.89, 71.75, 49.03],
    "TRXUSDT": [0.3674, 0.3254, 0.3223],
}

MA_CROSS_PAIRS = [(50, 100), (50, 200), (50, 300), (100, 200), (100, 300)]
