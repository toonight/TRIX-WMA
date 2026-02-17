"""TRIX and WMA indicator implementations — pure pandas/numpy."""
import numpy as np
import pandas as pd


def wma(series: pd.Series, period: int) -> pd.Series:
    """Weighted Moving Average with linearly increasing weights."""
    weights = np.arange(1, period + 1, dtype=float)
    def _wma(x):
        return np.dot(x, weights) / weights.sum()
    return series.rolling(period).apply(_wma, raw=True)


def _ema(series: pd.Series, span: int) -> pd.Series:
    """Standard EMA helper."""
    return series.ewm(span=span, adjust=False).mean()


def trix(close: pd.Series, period: int) -> pd.Series:
    """TRIX indicator: 1-bar percent change of triple-smoothed EMA.

    Returns values in percent (×100).
    """
    ema1 = _ema(close, period)
    ema2 = _ema(ema1, period)
    ema3 = _ema(ema2, period)
    return ema3.pct_change() * 100.0


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range."""
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()
