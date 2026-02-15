"""Vectorized backtest engine and metrics computation.

Design: signals computed at close of bar t ⟹ execution at open of bar t+1.
Fees and slippage applied at execution price.
"""
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Backtest core
# ---------------------------------------------------------------------------

def run_backtest(
    df: pd.DataFrame,
    entry_signal: pd.Series,
    exit_signal: pd.Series,
    fees_pct: float = 0.001,
    slippage_pct: float = 0.002,
) -> pd.DataFrame:
    """Run a long-only backtest with next-open execution.

    Parameters
    ----------
    df : OHLCV DataFrame (must contain 'Open' and 'Close').
    entry_signal, exit_signal : boolean Series aligned to df index.
        These are "signal at close" — execution happens at *next* bar's Open.
    fees_pct : one-way fee fraction.
    slippage_pct : one-way slippage fraction.

    Returns
    -------
    DataFrame with columns:
        position  – 1 when in trade, 0 otherwise
        equity    – equity curve (starts at 1.0)
        trade_id  – integer id for each round-trip trade
    """
    # Shift signals forward by 1 bar to execute at next open
    entry_exec = entry_signal.shift(1).fillna(False).astype(bool)
    exit_exec = exit_signal.shift(1).fillna(False).astype(bool)

    n = len(df)
    position = np.zeros(n, dtype=np.int8)
    equity = np.ones(n, dtype=np.float64)
    trade_id = np.full(n, -1, dtype=np.int32)
    open_prices = df["Open"].values
    close_prices = df["Close"].values
    entry_vals = entry_exec.values
    exit_vals = exit_exec.values

    current_pos = 0
    entry_price = 0.0
    current_trade = -1
    trade_counter = 0

    for i in range(1, n):
        if current_pos == 0 and entry_vals[i]:
            # Enter at open of bar i
            current_pos = 1
            entry_price = open_prices[i] * (1.0 + slippage_pct)
            # Deduct entry fee from equity
            equity[i] = equity[i - 1] * (1.0 - fees_pct)
            trade_counter += 1
            current_trade = trade_counter
        elif current_pos == 1 and exit_vals[i]:
            # Exit at open of bar i
            fill_price = open_prices[i] * (1.0 - slippage_pct)
            trade_return = fill_price / entry_price
            equity[i] = equity[i - 1] * trade_return * (1.0 - fees_pct)
            current_pos = 0
            entry_price = 0.0
        else:
            if current_pos == 1:
                # Mark-to-market using close
                equity[i] = equity[i - 1] * (close_prices[i] / close_prices[i - 1])
            else:
                equity[i] = equity[i - 1]

        position[i] = current_pos
        if current_pos == 1:
            trade_id[i] = current_trade

    return pd.DataFrame({
        "position": position,
        "equity": equity,
        "trade_id": trade_id,
    }, index=df.index)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(
    bt: pd.DataFrame,
    df: pd.DataFrame,
    risk_free_rate: float = 0.0,
) -> dict:
    """Compute strategy performance metrics from backtest results.

    Parameters
    ----------
    bt : backtest DataFrame (from run_backtest).
    df : original OHLCV DataFrame.
    risk_free_rate : annualized risk-free rate.

    Returns
    -------
    dict of metric_name -> value.
    """
    equity = bt["equity"]
    n_bars = len(equity)
    if n_bars < 2:
        return _empty_metrics()

    total_return = equity.iloc[-1] / equity.iloc[0] - 1.0

    # Annualization
    years = n_bars / 252.0
    if years <= 0:
        return _empty_metrics()
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0

    # Daily returns
    daily_ret = equity.pct_change().dropna()
    ann_vol = daily_ret.std() * np.sqrt(252)
    sharpe = (cagr - risk_free_rate) / ann_vol if ann_vol > 0 else 0.0

    # Max drawdown
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max
    max_dd = drawdown.min()

    calmar = cagr / abs(max_dd) if abs(max_dd) > 1e-10 else 0.0

    # Trade stats
    trade_ids = bt["trade_id"]
    unique_trades = trade_ids[trade_ids >= 0].unique()
    n_trades = len(unique_trades)

    win_count = 0
    trade_returns = []
    for tid in unique_trades:
        mask = trade_ids == tid
        seg = equity[mask]
        if len(seg) >= 1:
            # Find first bar of trade and last bar
            first_idx = seg.index[0]
            last_idx = seg.index[-1]
            pos_first = bt.index.get_loc(first_idx)
            if pos_first > 0:
                tr = seg.iloc[-1] / equity.iloc[pos_first - 1] - 1.0
            else:
                tr = seg.iloc[-1] / seg.iloc[0] - 1.0
            trade_returns.append(tr)
            if tr > 0:
                win_count += 1

    win_rate = win_count / n_trades if n_trades > 0 else 0.0
    avg_trade_ret = np.mean(trade_returns) if trade_returns else 0.0

    # Exposure
    exposure = bt["position"].mean()

    return {
        "total_return": total_return,
        "cagr": cagr,
        "ann_vol": ann_vol,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "calmar": calmar,
        "n_trades": n_trades,
        "win_rate": win_rate,
        "avg_trade_ret": avg_trade_ret,
        "exposure": exposure,
    }


def buy_and_hold_metrics(
    df: pd.DataFrame,
    fees_pct: float = 0.001,
    slippage_pct: float = 0.002,
    risk_free_rate: float = 0.0,
) -> dict:
    """Compute buy-and-hold metrics on the same data window."""
    close = df["Close"].values
    n = len(close)
    if n < 2:
        return _empty_metrics()

    # Entry at first open, exit at last open
    entry = df["Open"].iloc[0] * (1.0 + slippage_pct) * (1.0 + fees_pct)
    exit_ = df["Open"].iloc[-1] * (1.0 - slippage_pct) * (1.0 - fees_pct)

    equity = pd.Series(close / close[0], index=df.index)
    total_return = exit_ / entry - 1.0
    years = n / 252.0
    cagr = (1.0 + total_return) ** (1.0 / years) - 1.0 if years > 0 else 0.0
    daily_ret = equity.pct_change().dropna()
    ann_vol = daily_ret.std() * np.sqrt(252)
    sharpe = (cagr - risk_free_rate) / ann_vol if ann_vol > 0 else 0.0
    running_max = equity.cummax()
    dd = (equity - running_max) / running_max
    max_dd = dd.min()
    calmar = cagr / abs(max_dd) if abs(max_dd) > 1e-10 else 0.0

    return {
        "total_return": total_return,
        "cagr": cagr,
        "ann_vol": ann_vol,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "calmar": calmar,
        "n_trades": 1,
        "win_rate": 1.0 if total_return > 0 else 0.0,
        "avg_trade_ret": total_return,
        "exposure": 1.0,
    }


def _empty_metrics() -> dict:
    return {
        "total_return": 0.0,
        "cagr": 0.0,
        "ann_vol": 0.0,
        "sharpe": 0.0,
        "max_dd": 0.0,
        "calmar": 0.0,
        "n_trades": 0,
        "win_rate": 0.0,
        "avg_trade_ret": 0.0,
        "exposure": 0.0,
    }
