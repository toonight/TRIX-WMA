"""Strategy signal generation — no lookahead.

All signals are computed using data available at the close of bar t.
Execution is shifted to next open (handled in backtest module).
"""
import pandas as pd
from trixwma.indicators import trix, wma


def baseline_signals(
    df: pd.DataFrame,
    trix_period: int,
    wma_period: int,
    shift: int,
) -> pd.DataFrame:
    """Generate baseline TRIX+WMA pullback signals.

    Entry setup  : pullback = WMA_t < WMA_{t-shift}
    Exit trigger : TRIX crosses above 0 from below
                   i.e. TRIX_{t-1} <= 0 and TRIX_t > 0

    Parameters
    ----------
    df : DataFrame with at least 'Close' column.
    trix_period, wma_period, shift : strategy parameters.

    Returns
    -------
    DataFrame with columns: wma, trix, entry_signal, exit_signal.
    Signals are boolean, aligned to bar t (close-of-day knowledge).
    """
    close = df["Close"]
    w = wma(close, wma_period)
    t = trix(close, trix_period)

    pullback = w < w.shift(shift)
    trix_cross_up = (t.shift(1) <= 0) & (t > 0)

    entry = pullback & trix_cross_up
    exit_ = (t.shift(1) > 0) & (t <= 0)  # TRIX crosses below 0 => exit

    out = pd.DataFrame({
        "wma": w,
        "trix": t,
        "entry_signal": entry.astype(bool),
        "exit_signal": exit_.astype(bool),
    }, index=df.index)
    return out


def robust_signals(
    df: pd.DataFrame,
    trix_period: int,
    wma_period: int,
    shift: int,
    setup_lookback: int = 3,
) -> pd.DataFrame:
    """Robust variant — require pullback present within last N bars + TRIX trigger.

    Entry: TRIX crosses above 0 AND pullback condition was true in any of the
           last `setup_lookback` bars (inclusive of current bar).
    Exit : same as baseline (TRIX crosses below 0).
    """
    close = df["Close"]
    w = wma(close, wma_period)
    t = trix(close, trix_period)

    pullback = w < w.shift(shift)
    # Setup is true if pullback was true in any of the last N bars
    setup = pullback.rolling(setup_lookback, min_periods=1).max().astype(bool)

    trix_cross_up = (t.shift(1) <= 0) & (t > 0)
    entry = setup & trix_cross_up
    exit_ = (t.shift(1) > 0) & (t <= 0)

    out = pd.DataFrame({
        "wma": w,
        "trix": t,
        "entry_signal": entry.astype(bool),
        "exit_signal": exit_.astype(bool),
    }, index=df.index)
    return out
