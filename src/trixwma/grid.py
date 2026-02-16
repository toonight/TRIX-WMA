"""2D/3D parameter grid evaluation with benchmark alpha columns."""
import itertools
import numpy as np
import pandas as pd
from trixwma.strategy import baseline_signals, trend_pullback_signals
from trixwma.backtest import run_backtest, compute_metrics, buy_and_hold_metrics


def evaluate_grid(
    df: pd.DataFrame,
    trix_range: tuple[int, int],
    wma_range: tuple[int, int],
    shift_range: tuple[int, int],
    fees_pct: float = 0.001,
    slippage_pct: float = 0.002,
    risk_free_rate: float = 0.0,
    atr_period: int = 14,
    sl_atr: float = 0.0,
    ts_atr: float = 0.0,
    time_stop: int = 0,
    regime_mode: str = "sma_slope",
    sma200_period: int = 200,
    sma_slope_period: int = 10,
    ticker: str = "",
    start_date: str = "",
    end_date: str = "",
) -> pd.DataFrame:
    """Evaluate all parameter combinations and return a tidy results table.

    Parameters
    ----------
    df : OHLCV DataFrame.
    trix_range, wma_range, shift_range : (min, max) inclusive.
    ticker, start_date, end_date : labeling for the output table.

    Returns
    -------
    DataFrame with columns:
        ticker, start, end, trix_p, wma_p, shift,
        total_return, cagr, ann_vol, sharpe, max_dd, calmar,
        n_trades, win_rate, avg_trade_ret, exposure,
        bh_cagr, bh_sharpe, bh_max_dd, bh_total_return,
        alpha_cagr, alpha_total_return, beats_bh.
    """
    trix_vals = list(range(trix_range[0], trix_range[1] + 1))
    wma_vals = list(range(wma_range[0], wma_range[1] + 1))
    shift_vals = list(range(shift_range[0], shift_range[1] + 1))

    bh = buy_and_hold_metrics(df, fees_pct, slippage_pct, risk_free_rate)
    total = len(trix_vals) * len(wma_vals) * len(shift_vals)

    nan_metrics = {k: float("nan") for k in [
        "total_return", "cagr", "ann_vol", "sharpe",
        "max_dd", "calmar", "n_trades", "win_rate",
        "avg_trade_ret", "exposure",
    ]}

    rows = []
    done = 0
    for tp, wp, sp in itertools.product(trix_vals, wma_vals, shift_vals):
        try:
            sig = trend_pullback_signals(
                df, tp, wp, sp,
                atr_period=atr_period,
                regime_mode=regime_mode,
                sma200_period=sma200_period,
                sma_slope_period=sma_slope_period,
            )
            
            atr_series = sig["atr"] if "atr" in sig.columns else None
            
            bt = run_backtest(
                df, sig["entry_signal"], sig["exit_signal"], 
                fees_pct, slippage_pct,
                atr_series=atr_series,
                sl_atr=sl_atr,
                ts_atr=ts_atr,
                time_stop=time_stop
            )
            m = compute_metrics(bt, df, risk_free_rate)
        except Exception:
            m = nan_metrics.copy()

        row = {
            "ticker": ticker,
            "start": start_date,
            "end": end_date,
            "trix_p": tp,
            "wma_p": wp,
            "shift": sp,
        }
        row.update(m)
        row["bh_cagr"] = bh["cagr"]
        row["bh_sharpe"] = bh["sharpe"]
        row["bh_max_dd"] = bh["max_dd"]
        row["bh_total_return"] = bh["total_return"]
        row["alpha_cagr"] = m.get("cagr", np.nan) - bh["cagr"]
        row["alpha_total_return"] = m.get("total_return", np.nan) - bh["total_return"]
        row["beats_bh"] = m.get("cagr", 0) > bh["cagr"]
        rows.append(row)
        done += 1
        if done % 50 == 0 or done == total:
            print(f"  grid: {done}/{total}")

    return pd.DataFrame(rows)


def grid_to_tensor(grid_df: pd.DataFrame, metric: str):
    """Convert tidy grid to 3D numpy tensor.

    Returns
    -------
    tensor : ndarray shape (n_trix, n_wma, n_shift)
    trix_vals, wma_vals, shift_vals : lists of axis values.
    """
    trix_vals = sorted(grid_df["trix_p"].unique())
    wma_vals = sorted(grid_df["wma_p"].unique())
    shift_vals = sorted(grid_df["shift"].unique())

    shape = (len(trix_vals), len(wma_vals), len(shift_vals))
    tensor = np.full(shape, np.nan)

    trix_idx = {v: i for i, v in enumerate(trix_vals)}
    wma_idx = {v: i for i, v in enumerate(wma_vals)}
    shift_idx = {v: i for i, v in enumerate(shift_vals)}

    for _, row in grid_df.iterrows():
        i = trix_idx[row["trix_p"]]
        j = wma_idx[row["wma_p"]]
        k = shift_idx[row["shift"]]
        tensor[i, j, k] = row[metric]

    return tensor, trix_vals, wma_vals, shift_vals
