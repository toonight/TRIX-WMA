"""Walk-forward validation with embargo and multi-asset testing."""
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta

from trixwma.grid import evaluate_grid
from trixwma.robustness import compute_robustness_scores, rank_plateaus
from trixwma.grid import grid_to_tensor
from trixwma.strategy import trend_pullback_signals
from trixwma.backtest import run_backtest, compute_metrics, buy_and_hold_metrics
from trixwma.data import load_ohlcv


# ---------------------------------------------------------------------------
# Walk-forward (full re-optimization per window)
# ---------------------------------------------------------------------------

def walk_forward(
    df: pd.DataFrame,
    trix_range: tuple[int, int],
    wma_range: tuple[int, int],
    shift_range: tuple[int, int],
    train_years: int = 5,
    test_years: int = 1,
    step_months: int = 6,
    embargo_bars: int = 5,
    fees_pct: float = 0.001,
    slippage_pct: float = 0.002,
    risk_free_rate: float = 0.0,
    kernel: tuple[int, int, int] = (3, 3, 3),
    weights: dict | None = None,
    min_trades: int = 30,
    # New params
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
    """Rolling walk-forward with embargo.

    For each window:
      1. Train: optimize plateau score on train segment.
      2. Embargo: skip ``embargo_bars`` between train and test.
      3. Test: apply selected params on test segment.

    Returns DataFrame with one row per window.
    """
    dates = df.index
    start = dates[0]
    end = dates[-1]

    train_delta = relativedelta(years=train_years)
    test_delta = relativedelta(years=test_years)
    step_delta = relativedelta(months=step_months)

    results = []
    window_start = start
    win_id = 0

    while True:
        train_end_date = window_start + train_delta
        test_start_date = train_end_date
        test_end_date = test_start_date + test_delta

        if test_end_date > end:
            break

        train_df = df.loc[window_start:train_end_date].copy()
        if len(train_df) < 100:
            window_start += step_delta
            continue

        if embargo_bars > 0 and len(train_df) > embargo_bars:
            train_df = train_df.iloc[:-embargo_bars]

        test_df = df.loc[test_start_date:test_end_date].copy()
        if embargo_bars > 0 and len(test_df) > embargo_bars:
            test_df = test_df.iloc[embargo_bars:]

        if len(test_df) < 20:
            window_start += step_delta
            continue

        # Train: grid search + plateau scoring
        train_grid = evaluate_grid(
            train_df, trix_range, wma_range, shift_range,
            fees_pct, slippage_pct, risk_free_rate,
            atr_period=atr_period,
            sl_atr=sl_atr,
            ts_atr=ts_atr,
            time_stop=time_stop,
            regime_mode=regime_mode,
            sma200_period=sma200_period,
            sma_slope_period=sma_slope_period,
            ticker=ticker, start_date=start_date, end_date=end_date,
        )
        bh_train = buy_and_hold_metrics(train_df, fees_pct, slippage_pct, risk_free_rate)
        
        # If train_grid is empty or all NaN, skip?
        # Assuming evaluate_grid returns valid DF with NaNs where appropriate.

        score, meta, axis = compute_robustness_scores(
            train_grid, grid_to_tensor, bh_train["cagr"],
            kernel=kernel, weights=weights, min_trades=min_trades,
            bh_frac_threshold=0.0, # looser restriction for WF optimization step?
        )
        ranked = rank_plateaus(score, axis, meta, top_n=1)

        if not ranked:
            # Fallback to best pixel
            if train_grid["cagr"].max() > -999:
                 best_row = train_grid.loc[train_grid["cagr"].idxmax()]
                 best_params = {
                     "trix_p": int(best_row["trix_p"]),
                     "wma_p": int(best_row["wma_p"]),
                     "shift": int(best_row["shift"]),
                 }
                 selection_method = "best_cagr_fallback"
            else:
                 # No valid params
                 window_start += step_delta
                 continue
        else:
            best_params = {
                "trix_p": ranked[0]["trix_p"],
                "wma_p": ranked[0]["wma_p"],
                "shift": ranked[0]["shift"],
            }
            selection_method = "plateau"

        # Test: apply selected params OOS
        sig = trend_pullback_signals(
            test_df, best_params["trix_p"], best_params["wma_p"], best_params["shift"],
            atr_period=atr_period,
            regime_mode=regime_mode,
            sma200_period=sma200_period,
            sma_slope_period=sma_slope_period,
        )
        atr_series = sig["atr"] if "atr" in sig.columns else None
        
        bt = run_backtest(
            test_df, sig["entry_signal"], sig["exit_signal"], fees_pct, slippage_pct,
            atr_series=atr_series,
            sl_atr=sl_atr,
            ts_atr=ts_atr,
            time_stop=time_stop
        )
        oos_metrics = compute_metrics(bt, test_df, risk_free_rate)
        bh_test = buy_and_hold_metrics(test_df, fees_pct, slippage_pct, risk_free_rate)

        row = {
            "window": win_id,
            "train_start": window_start,
            "train_end": train_end_date,
            "test_start": test_df.index[0],
            "test_end": test_df.index[-1],
            "selection_method": selection_method,
            **{f"param_{k}": v for k, v in best_params.items()},
            **{f"oos_{k}": v for k, v in oos_metrics.items()},
            "oos_bh_cagr": bh_test["cagr"],
            "oos_beats_bh": oos_metrics["cagr"] > bh_test["cagr"],
        }
        results.append(row)
        win_id += 1
        window_start += step_delta

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Walk-forward for a single fixed plateau (no re-optimization)
# ---------------------------------------------------------------------------

def walk_forward_selected_plateau(
    df: pd.DataFrame,
    trix_p: int,
    wma_p: int,
    shift: int,
    test_years: int = 1,
    step_months: int = 6,
    embargo_bars: int = 5,
    fees_pct: float = 0.001,
    slippage_pct: float = 0.002,
    risk_free_rate: float = 0.0,
    # New params
    atr_period: int = 14,
    sl_atr: float = 0.0,
    ts_atr: float = 0.0,
    time_stop: int = 0,
    regime_mode: str = "sma_slope",
    sma200_period: int = 200,
    sma_slope_period: int = 10,
) -> pd.DataFrame:
    """Evaluate a fixed parameter set across rolling OOS windows.

    Unlike ``walk_forward``, this does NOT re-optimize each window.
    It simply applies the given params and records OOS performance,
    testing whether the plateau generalizes temporally.
    """
    dates = df.index
    start = dates[0]
    end = dates[-1]

    test_delta = relativedelta(years=test_years)
    step_delta = relativedelta(months=step_months)

    results = []
    win_start = start
    win_id = 0

    while True:
        win_end = win_start + test_delta
        if win_end > end:
            break

        seg = df.loc[win_start:win_end].copy()
        if embargo_bars > 0 and len(seg) > embargo_bars:
            seg = seg.iloc[embargo_bars:]
        if len(seg) < 20:
            win_start += step_delta
            continue

        sig = trend_pullback_signals(
            seg, trix_p, wma_p, shift,
            atr_period=atr_period,
            regime_mode=regime_mode,
            sma200_period=sma200_period,
            sma_slope_period=sma_slope_period,
        )
        atr_series = sig["atr"] if "atr" in sig.columns else None
            
        bt = run_backtest(
            seg, sig["entry_signal"], sig["exit_signal"], fees_pct, slippage_pct,
            atr_series=atr_series,
            sl_atr=sl_atr,
            ts_atr=ts_atr,
            time_stop=time_stop
        )
        m = compute_metrics(bt, seg, risk_free_rate)
        bh = buy_and_hold_metrics(seg, fees_pct, slippage_pct, risk_free_rate)

        results.append({
            "window": win_id,
            "start": seg.index[0],
            "end": seg.index[-1],
            **{f"oos_{k}": v for k, v in m.items()},
            "oos_bh_cagr": bh["cagr"],
            "oos_beats_bh": m["cagr"] > bh["cagr"],
        })
        win_id += 1
        win_start += step_delta

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Multi-asset
# ---------------------------------------------------------------------------

def multi_asset_evaluation(
    tickers: list[str],
    start_date: str,
    end_date: str,
    trix_range: tuple[int, int],
    wma_range: tuple[int, int],
    shift_range: tuple[int, int],
    cache_dir: str = "data/cache",
    fees_pct: float = 0.001,
    slippage_pct: float = 0.002,
    risk_free_rate: float = 0.0,
    kernel: tuple[int, int, int] = (3, 3, 3),
    weights: dict | None = None,
    min_trades: int = 30,
    # New params
    atr_period: int = 14,
    sl_atr: float = 0.0,
    ts_atr: float = 0.0,
    time_stop: int = 0,
    regime_mode: str = "sma_slope",
    sma200_period: int = 200,
    sma_slope_period: int = 10,
) -> pd.DataFrame:
    """Run grid + robustness for multiple tickers.

    Returns summary table with ``oos_underperformance_freq`` where applicable.
    """
    rows = []
    for ticker in tickers:
        print(f"  multi-asset: {ticker}")
        try:
            df = load_ohlcv(ticker, start_date, end_date, cache_dir)
            grid_df = evaluate_grid(
                df, trix_range, wma_range, shift_range,
                fees_pct, slippage_pct, risk_free_rate,
                atr_period=atr_period,
                sl_atr=sl_atr,
                ts_atr=ts_atr,
                time_stop=time_stop,
                regime_mode=regime_mode,
                sma200_period=sma200_period,
                sma_slope_period=sma_slope_period,
                ticker=ticker, start_date=start_date, end_date=end_date,
            )
            bh = buy_and_hold_metrics(df, fees_pct, slippage_pct, risk_free_rate)
            score, meta, axis = compute_robustness_scores(
                grid_df, grid_to_tensor, bh["cagr"],
                kernel=kernel, weights=weights, min_trades=min_trades,
            )
            ranked = rank_plateaus(score, axis, meta, top_n=1)

            if ranked:
                best = ranked[0]
                mask = (
                    (grid_df["trix_p"] == best["trix_p"]) &
                    (grid_df["wma_p"] == best["wma_p"]) &
                    (grid_df["shift"] == best["shift"])
                )
                pixel = grid_df[mask].iloc[0] if mask.any() else {}
                row = {
                    "ticker": ticker,
                    "trix_p": best["trix_p"],
                    "wma_p": best["wma_p"],
                    "shift": best["shift"],
                    "robustness_score": best["score"],
                    "cagr": pixel.get("cagr", np.nan),
                    "sharpe": pixel.get("sharpe", np.nan),
                    "max_dd": pixel.get("max_dd", np.nan),
                    "alpha_cagr": pixel.get("alpha_cagr", np.nan),
                    "n_trades": pixel.get("n_trades", 0),
                    "bh_cagr": bh["cagr"],
                    "beats_bh": pixel.get("cagr", 0) > bh["cagr"],
                    "nb_cagr_median": best["nb_cagr_median"],
                    "nb_alpha_cagr_median": best["nb_alpha_cagr_median"],
                    "nb_sharpe_median": best["nb_sharpe_median"],
                    "nb_bh_frac": best["nb_bh_frac"],
                }
            else:
                row = {
                    "ticker": ticker,
                    "trix_p": np.nan, "wma_p": np.nan, "shift": np.nan,
                    "robustness_score": np.nan,
                    "cagr": np.nan, "sharpe": np.nan, "max_dd": np.nan,
                    "alpha_cagr": np.nan,
                    "n_trades": 0, "bh_cagr": bh["cagr"],
                    "beats_bh": False,
                    "nb_cagr_median": np.nan,
                    "nb_alpha_cagr_median": np.nan,
                    "nb_sharpe_median": np.nan,
                    "nb_bh_frac": np.nan,
                }
            rows.append(row)
        except Exception as e:
            print(f"    SKIP {ticker}: {e}")
            rows.append({"ticker": ticker, "error": str(e)})

    result_df = pd.DataFrame(rows)

    # Compute underperformance frequency
    if "beats_bh" in result_df.columns:
        valid = result_df["beats_bh"].dropna()
        if len(valid) > 0:
            result_df.attrs["oos_underperformance_freq"] = 1.0 - valid.mean()

    return result_df
