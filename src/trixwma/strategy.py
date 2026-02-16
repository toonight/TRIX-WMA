"""Strategy signal generation — no lookahead.

All signals are computed using data available at the close of bar t.
Execution is shifted to next open (handled in backtest module).
"""
import pandas as pd
from trixwma.indicators import trix, wma, atr


def baseline_signals(
    df: pd.DataFrame,
    trix_period: int,
    wma_period: int,
    shift: int,
) -> pd.DataFrame:
    """Generate baseline TRIX+WMA signals (Legacy)."""
    close = df["Close"]
    w = wma(close, wma_period)
    t = trix(close, trix_period)

    pullback = w < w.shift(shift)
    trix_cross_up = (t.shift(1) <= 0) & (t > 0)

    entry = pullback & trix_cross_up
    exit_ = (t.shift(1) > 0) & (t <= 0)

    # Return minimal columns
    out = pd.DataFrame({
        "entry_signal": entry.astype(bool),
        "exit_signal": exit_.astype(bool),
    }, index=df.index)
    return out


def trend_pullback_signals(
    df: pd.DataFrame,
    trix_period: int,
    wma_period: int,
    shift: int,
    atr_period: int = 14,
    regime_mode: str = "sma_slope",
    sma200_period: int = 200,
    sma_slope_period: int = 10,
    # Legacy compat
    use_regime_filter: bool = True,
) -> pd.DataFrame:
    """Trend-Following Pullback Strategy.

    Logic:
    1. Regime Filter (configurable mode).
    2. Setup: WMA decreases (pullback) relative to shifted WMA.
    3. Trigger: TRIX crosses above 0.
    4. Exit: TRIX crosses below 0 (soft exit).

    Regime Modes:
    - "price_above_sma": Close > SMA200 (strictest).
    - "sma_slope": SMA200 is rising over sma_slope_period bars (default).
    - "ema_cross": EMA50 > EMA200 (golden cross).
    - "none": No regime filter.
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    # Indicators
    w = wma(close, wma_period)
    t = trix(close, trix_period)
    a = atr(high, low, close, atr_period)
    sma200 = close.rolling(sma200_period).mean()

    # 1. Regime Filter
    if regime_mode == "price_above_sma":
        regime = (close > sma200)
    elif regime_mode == "sma_slope":
        regime = (sma200 > sma200.shift(sma_slope_period))
    elif regime_mode == "ema_cross":
        ema50 = close.ewm(span=50, adjust=False).mean()
        ema200 = close.ewm(span=sma200_period, adjust=False).mean()
        regime = (ema50 > ema200)
    elif regime_mode == "none":
        regime = pd.Series(True, index=df.index)
    else:
        # Fallback: use legacy boolean
        if use_regime_filter:
            regime = (close > sma200)
        else:
            regime = pd.Series(True, index=df.index)

    # 2. Setup (Pullback): WMA < WMA_{t-shift}
    pullback = w < w.shift(shift)

    # 3. Trigger: TRIX crosses above 0
    trix_cross_up = (t.shift(1) <= 0) & (t > 0)

    # Entry = Regime & Pullback & Trigger
    entry = regime & pullback & trix_cross_up

    # 4. Exit: TRIX crosses below 0
    exit_signal = (t.shift(1) > 0) & (t <= 0)

    out = pd.DataFrame({
        "entry_signal": entry.fillna(False).astype(bool),
        "exit_signal": exit_signal.fillna(False).astype(bool),
        "atr": a.ffill(),
        "close": close,
    }, index=df.index)

    return out
