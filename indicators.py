import math

import pandas as pd
import requests

BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
BINANCE_TICKER = "https://api.binance.com/api/v3/ticker/price"


def fetch_ohlcv(symbol: str, interval: str, limit: int = 350) -> pd.DataFrame:
    resp = requests.get(
        BINANCE_KLINES,
        params={"symbol": symbol, "interval": interval, "limit": limit},
        timeout=15,
    )
    resp.raise_for_status()
    cols = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_vol", "trades", "taker_base", "taker_quote", "ignore",
    ]
    df = pd.DataFrame(resp.json(), columns=cols)
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = df[c].astype(float)
    return df.iloc[:-1].reset_index(drop=True)  # drop the currently-forming candle


def fetch_price(symbol: str) -> float:
    """Live current price — identical across all timeframes."""
    resp = requests.get(BINANCE_TICKER, params={"symbol": symbol}, timeout=15)
    resp.raise_for_status()
    return float(resp.json()["price"])


def _sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n).mean()


def _rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=period - 1, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period - 1, min_periods=period).mean()
    val = (100 - 100 / (1 + gain / loss)).iloc[-1]
    return round(float(val), 2)


def _stochrsi_kd(close: pd.Series, rsi_period: int = 14, window: int = 14,
                 smooth_k: int = 3, smooth_d: int = 3) -> tuple:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=rsi_period - 1, min_periods=rsi_period).mean()
    loss = (-delta.clip(upper=0)).ewm(com=rsi_period - 1, min_periods=rsi_period).mean()
    rsi = 100 - 100 / (1 + gain / loss)
    lo = rsi.rolling(window).min()
    hi = rsi.rolling(window).max()
    stoch = (rsi - lo) / (hi - lo) * 100
    k = stoch.rolling(smooth_k).mean()
    d = k.rolling(smooth_d).mean()
    return round(float(k.iloc[-1]), 2), round(float(d.iloc[-1]), 2)


def _vol_ratio(volume: pd.Series, period: int = 20) -> float:
    avg = volume.rolling(period).mean()
    return round(float(volume.iloc[-1] / avg.iloc[-1]), 2)


def _safe(v: float):
    """Return None for NaN so callers can do simple `if v is None` checks."""
    return None if math.isnan(v) else v


def compute_indicators(symbol: str, interval: str) -> dict:
    df = fetch_ohlcv(symbol, interval)
    close = df["close"]
    volume = df["volume"]

    s50  = _sma(close, 50)
    s100 = _sma(close, 100)
    s200 = _sma(close, 200)
    s300 = _sma(close, 300)
    _k, _d = _stochrsi_kd(close)

    return {
        "price":        float(close.iloc[-1]),
        "high":         float(df["high"].iloc[-1]),
        "low":          float(df["low"].iloc[-1]),
        "prev_price":   float(close.iloc[-2]),
        "sma50":        _safe(float(s50.iloc[-1])),
        "sma100":       _safe(float(s100.iloc[-1])),
        "sma200":       _safe(float(s200.iloc[-1])),
        "sma300":       _safe(float(s300.iloc[-1])),
        "prev_sma50":   _safe(float(s50.iloc[-2])),
        "prev_sma100":  _safe(float(s100.iloc[-2])),
        "prev_sma200":  _safe(float(s200.iloc[-2])),
        "prev_sma300":  _safe(float(s300.iloc[-2])),
        "rsi":          _safe(_rsi(close)),
        "stochrsi_k":   _safe(_k),
        "stochrsi_d":   _safe(_d),
        "volume_ratio": _safe(_vol_ratio(volume)),
    }
