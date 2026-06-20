from config import MA_CROSS_PAIRS


def _pct(price: float, level: float) -> float:
    return (price - level) / level * 100


def _hit(price: float, high: float, low: float, prev_price: float, level: float) -> bool:
    """True if the level was touched or crossed by the last closed candle."""
    in_range = low <= level <= high
    crossed = (prev_price < level <= price) or (prev_price > level >= price)
    return in_range or crossed


def check_ma_conditions(data: dict, threshold_pct: float) -> list:
    """Return at most one condition per MA (highest applicable stage)."""
    price = data["price"]
    high  = data["high"]
    low   = data["low"]
    prev  = data["prev_price"]
    results = []

    for period in (50, 100, 200, 300):
        level = data.get(f"sma{period}")
        if level is None:
            continue
        dist = _pct(price, level)
        name = f"SMA{period}"

        if _hit(price, high, low, prev, level):
            results.append({"level_name": name, "level_price": level, "stage": 2, "distance_pct": dist})
        elif abs(dist) <= threshold_pct:
            results.append({"level_name": name, "level_price": level, "stage": 1, "distance_pct": dist})

    return results


def check_sr_conditions(price: float, high: float, low: float, prev_price: float,
                         levels: list, threshold_pct: float) -> list:
    """Return at most one condition per price level (highest applicable stage).
    Role is determined dynamically: price above level = support, below = resistance."""
    results = []
    for lvl in levels:
        if not lvl:
            continue
        dist = _pct(price, lvl)
        role = "support" if price >= lvl else "resistance"
        name = f"SR_{lvl}"

        if _hit(price, high, low, prev_price, lvl):
            results.append({"level_name": name, "level_price": lvl, "stage": 2,
                             "distance_pct": dist, "role": role})
        elif abs(dist) <= threshold_pct:
            results.append({"level_name": name, "level_price": lvl, "stage": 1,
                             "distance_pct": dist, "role": role})

    return results


def check_crossovers(data: dict) -> list:
    """Detect MA crossovers on the last two closed candles."""
    results = []
    for fast, slow in MA_CROSS_PAIRS:
        cf = data.get(f"sma{fast}")
        cs = data.get(f"sma{slow}")
        pf = data.get(f"prev_sma{fast}")
        ps = data.get(f"prev_sma{slow}")

        if any(v is None for v in (cf, cs, pf, ps)):
            continue

        if pf <= ps and cf > cs:
            results.append({"level_name": f"X{fast}_{slow}", "fast": fast, "slow": slow, "direction": "bullish"})
        elif pf >= ps and cf < cs:
            results.append({"level_name": f"X{fast}_{slow}", "fast": fast, "slow": slow, "direction": "bearish"})

    return results
