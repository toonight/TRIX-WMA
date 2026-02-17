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
    # Risk management
    atr_series: pd.Series = None,
    sl_atr: float = 0.0,
    ts_atr: float = 0.0,
    time_stop: int = 0,
) -> pd.DataFrame:
    """Run a long-only backtest with next-open execution and risk management.

    Parameters
    ----------
    df : OHLCV DataFrame (must contain 'Open', 'High', 'Low', 'Close').
    entry_signal, exit_signal : boolean Series (signal at close).
    fees_pct, slippage_pct : trading frictions.
    atr_series : Series of ATR values (aligned with df), required if sl_atr/ts_atr > 0.
    sl_atr : Initial Stop Loss multiplier (0.0 to disable).
    ts_atr : Trailing Stop multiplier (0.0 to disable).
    time_stop : Max bars in trade (0 to disable).

    Returns
    -------
    DataFrame with columns: position, equity, trade_id.
    """
    # Shift signals forward to execute at next open
    entry_exec = entry_signal.shift(1).fillna(False).astype(bool)
    exit_exec = exit_signal.shift(1).fillna(False).astype(bool)

    # Shift ATR to be available at Open
    # If decision is made at close of t-1, ATR_{t-1} is known.
    if atr_series is not None:
        atr_vals = atr_series.shift(1).fillna(0.0).values
    else:
        atr_vals = np.zeros(len(df))

    n = len(df)
    position = np.zeros(n, dtype=np.int8)
    equity = np.ones(n, dtype=np.float64)
    trade_id = np.full(n, -1, dtype=np.int32)
    
    open_prices = df["Open"].values
    high_prices = df["High"].values
    low_prices = df["Low"].values
    close_prices = df["Close"].values
    
    entry_vals = entry_exec.values
    exit_vals = exit_exec.values

    current_pos = 0
    entry_price = 0.0
    current_trade = -1
    trade_counter = 0
    
    stop_price = 0.0
    hh_since_entry = 0.0
    bars_in_trade = 0

    for i in range(1, n):
        # 1. Update Equity (Mark-to-Market)
        if current_pos == 1:
            # We are in a trade coming into bar i
            # Check stops first
            
            # Trailing Stop Update (based on previous High? or current?)
            # Usually Trailing Stop is updated based on Highs achieved.
            # If we follow "ATR Trailing Stop" logic literally:
            # Stop = HighestHigh - ATR * Mult.
            # Here we use High[i-1] (known at open of i) to update stop for bar i?
            # Standard: Stop level is determined by past data.
            # Intrabar: if Low[i] hits stop, we exit.
            
            # Update High Water Mark with PREVIOUS bar High to set stop for CURRENT bar
            # (Strictly speaking, TS updates as price moves up, so maybe High[i] matters?
            #  But we can only exit if we touch the stop line established. 
            #  Let's stick to: Stop is set at Open[i] based on known history, 
            #  then checked against Low[i].)
            
            # Wait, standard Chandelier Exit uses Highest High since Entry.
            # We updated hh_since_entry at end of i-1.
            
            # Check Stop Hit
            triggered_stop = False
            exit_price = 0.0
            
            if sl_atr > 0 or ts_atr > 0:
                if low_prices[i] <= stop_price:
                    triggered_stop = True
                    # Assume execution at stop price (with slippage?)
                    # Stop orders usually slip. We interpret stop_price as trigger.
                    # Fill at stop_price - slippage? Or min(Open, Stop)?
                    # Simplified: exit at stop_price * (1 - slippage)
                    exit_price = stop_price * (1.0 - slippage_pct)
                    
                    # Gap protection: if Open[i] < stop_price, we gapped down over stop
                    if open_prices[i] < stop_price:
                        exit_price = open_prices[i] * (1.0 - slippage_pct)

            # Check Time Stop
            if not triggered_stop and time_stop > 0:
                if bars_in_trade >= time_stop:
                    triggered_stop = True
                    exit_price = open_prices[i] * (1.0 - slippage_pct)
                    # Note: Time stop usually exits at Open of bar N+1?
                    # If bars_in_trade reached limit at end of i-1, exit at Open i.
                    # Yes.

            if triggered_stop:
                trade_return = exit_price / entry_price
                equity[i] = equity[i - 1] * trade_return * (1.0 - fees_pct)
                current_pos = 0
                entry_price = 0.0
                stop_price = 0.0
                bars_in_trade = 0
                trade_id[i] = current_trade # Log trade on exit bar? or not?
                # Logic below sets trade_id if current_pos==1.
                # If we exit today, typically position becomes 0.
                # Let's count this bar as flat or part of trade? 
                # Backtest convention: Position[i] is EOD position.
                position[i] = 0
                continue # Done with this bar

        # 2. Regular Execution
        if current_pos == 0 and entry_vals[i]:
            # Enter Long
            current_pos = 1
            entry_price = open_prices[i] * (1.0 + slippage_pct)
            equity[i] = equity[i - 1] * (1.0 - fees_pct)
            trade_counter += 1
            current_trade = trade_counter
            
            # Initialize Risk Management
            bars_in_trade = 1
            hh_since_entry = high_prices[i] # Intra-bar high? 
            # Wait, we just entered at Open. High[i] is future.
            # Initial stop based on Entry Price
            if sl_atr > 0:
                stop_price = entry_price - (atr_vals[i] * sl_atr)
            else:
                stop_price = 0.0
                
            # Check for immediate stop out (Intra-bar)
            if sl_atr > 0 and low_prices[i] <= stop_price:
                # Stopped out immediately
                exit_price = stop_price * (1.0 - slippage_pct)
                trade_return = exit_price / entry_price
                equity[i] = equity[i] * trade_return * (1.0 - fees_pct) # Exit fee
                current_pos = 0
                entry_price = 0.0
                stop_price = 0.0
                trade_id[i] = current_trade
                position[i] = 0
                continue
            
            trade_id[i] = current_trade

        elif current_pos == 1:
            # Check Signal Exit (if not stopped out)
            if exit_vals[i]:
                # Exit signal -> Sell at Open
                fill_price = open_prices[i] * (1.0 - slippage_pct)
                trade_return = fill_price / entry_price
                equity[i] = equity[i - 1] * trade_return * (1.0 - fees_pct)
                current_pos = 0
                entry_price = 0.0
                position[i] = 0
                continue
                
            else:
                # Hold
                # MTM
                equity[i] = equity[i - 1] * (close_prices[i] / close_prices[i - 1])
                bars_in_trade += 1
                
                # Update Trailing Stop at CLOSE (for next bar)
                if ts_atr > 0:
                    # Update HH
                    if high_prices[i] > hh_since_entry:
                        hh_since_entry = high_prices[i]
                    
                    # New potential stop
                    new_stop = hh_since_entry - (atr_vals[i] * ts_atr) # Use ATR available at this bar
                    # Ratchet up only
                    if new_stop > stop_price:
                        stop_price = new_stop
                        
                trade_id[i] = current_trade

        else:
            # Flat
            equity[i] = equity[i - 1]

        position[i] = current_pos

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


def buy_and_hold_sma200_metrics(
    df: pd.DataFrame,
    fees_pct: float = 0.001,
    slippage_pct: float = 0.002,
    risk_free_rate: float = 0.0,
    sma_period: int = 200,
) -> dict:
    """Compute metrics for Buy & Hold but only when Price > SMA200."""
    close = df["Close"]
    sma = close.rolling(sma_period).mean()
    
    # Signal: Hold when Close > SMA (evaluated at Close)
    # Exec: Enter Next Open
    signal = (close > sma)
    
    # Use run_backtest to get accurate equity curve with frictions
    # Signal says "Stay Long". 
    # run_backtest expects "Entry" and "Exit" signals.
    # Entry: Signal goes False -> True
    # Exit: Signal goes True -> False
    
    entry_signal = (signal & (~signal.shift(1).fillna(False)))
    exit_signal = ((~signal) & (signal.shift(1).fillna(False)))
    
    bt = run_backtest(df, entry_signal, exit_signal, fees_pct, slippage_pct)
    return compute_metrics(bt, df, risk_free_rate)


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
