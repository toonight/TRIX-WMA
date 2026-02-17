
import pandas as pd
import numpy as np
from pathlib import Path
from trixwma.data import load_ohlcv
from trixwma.strategy import trend_pullback_signals
from trixwma.backtest import run_backtest
import itertools

def main():
    base_dir = Path("d:/Projets/2026/TRIX-WMA/trix_wma_robustness")
    data_dir = base_dir / "data" / "cache"
    
    ticker = "GC=F"
    start_date = "2010-01-01"
    end_date = "2024-12-31"
    fees = 0.001
    slip = 0.001
    
    print(f"Loading data for {ticker}...")
    try:
        df = load_ohlcv(ticker, start_date, end_date, str(data_dir))
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # Parameter Ranges
    trix_range = range(3, 16)
    wma_range = range(5, 31)
    shift_range = range(1, 11)
    
    best_cagr = -np.inf
    best_params = None
    best_metrics = None
    
    print(f"Starting grid search for {ticker}...")
    
    count = 0
    total = len(trix_range) * len(wma_range) * len(shift_range)
    
    for trix, wma, shift in itertools.product(trix_range, wma_range, shift_range):
        try:
            sig = trend_pullback_signals(
                df, trix, wma, shift,
                atr_period=14,
                regime_mode="sma_slope",
                sma200_period=200,
                sma_slope_period=10,
            )
            atr_s = sig["atr"] if "atr" in sig.columns else None
            bt = run_backtest(
                df, sig["entry_signal"], sig["exit_signal"], 
                fees, slip,
                atr_series=atr_s, sl_atr=3.0, ts_atr=2.0 # Keeping SL/TS constant as per config, or could optimize too
            )
            
            # Metrics
            total_ret = (bt["equity"].iloc[-1] / bt["equity"].iloc[0]) - 1
            n_years = (df.index[-1] - df.index[0]).days / 365.25
            cagr = (1 + total_ret) ** (1 / n_years) - 1
            
            if cagr > best_cagr:
                best_cagr = cagr
                best_params = (trix, wma, shift)
                best_metrics = {
                    "Total Return": total_ret,
                    "CAGR": cagr,
                    "Equity": bt["equity"].iloc[-1]
                }
                # print(f"New Best: {best_params} -> CAGR: {cagr:.2%}")
        
        except Exception:
            continue
            
        # count += 1
        # if count % 500 == 0:
        #     print(f"Processed {count}/{total}...")

    print("-" * 30)
    print(f"Optimization Complete for {ticker}")
    print(f"Best Params: TRIX={best_params[0]}, WMA={best_params[1]}, Shift={best_params[2]}")
    print(f"Metrics: CAGR={best_metrics['CAGR']:.2%}, Total Return={best_metrics['Total Return']:.2%}")
    
    # Buy & Hold Comparison
    bh_ret = df["Close"].pct_change().fillna(0)
    bh_total_ret = (1 + bh_ret).cumprod().iloc[-1] - 1
    bh_cagr = (1 + bh_total_ret) ** (1 / n_years) - 1
    print(f"Buy & Hold: CAGR={bh_cagr:.2%}")

if __name__ == "__main__":
    main()
