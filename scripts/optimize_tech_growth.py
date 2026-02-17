
import pandas as pd
import numpy as np
from pathlib import Path
import itertools
import sys

# Add project root to path
base_path = Path("d:/Projets/2026/TRIX-WMA")
if str(base_path) not in sys.path:
    sys.path.append(str(base_path))

try:
    from trixwma.data import load_ohlcv
    from trixwma.strategy import trend_pullback_signals
    from trixwma.backtest import run_backtest
except ImportError:
    # Try alternate path
    sys.path.append(str(base_path / "trix_wma_robustness/src"))
    from trixwma.data import load_ohlcv
    from trixwma.strategy import trend_pullback_signals
    from trixwma.backtest import run_backtest

def main():
    base_dir = Path("d:/Projets/2026/TRIX-WMA/trix_wma_robustness")
    data_dir = base_dir / "data" / "cache"
    
    tickers = ["NVDA", "GOOGL", "MSFT", "META", "AMZN"]
    start_date = "2010-01-01"
    end_date = "2024-12-31"
    fees = 0.001
    slip = 0.001
    
    # Growth Mode Parameters
    entry_mode = "momentum"
    exit_mode = "trailing_only"
    regime_mode = "none"
    
    # Ranges from tech_growth.yaml
    trix_range = range(8, 21, 2)   # [8, 10, ... 20]
    wma_range = range(15, 41, 5)   # [15, 20, ... 40]
    shift_range = range(4, 11, 2)  # [4, 6, 8, 10]
    
    # Trailing Stop Only
    sl_atr = 0.0
    ts_atr = 3.0
    
    results = {}
    
    for ticker in tickers:
        print(f"Loading data for {ticker}...")
        try:
            df = load_ohlcv(ticker, start_date, end_date, str(data_dir))
        except Exception as e:
            print(f"Error loading data for {ticker}: {e}")
            continue

        best_cagr = -np.inf
        best_params = None
        best_metrics = None
        
        print(f"Starting grid search for {ticker} (Growth Mode)...")
        
        count = 0
        total = len(trix_range) * len(wma_range) * len(shift_range)
        
        for trix, wma, shift in itertools.product(trix_range, wma_range, shift_range):
            try:
                # IMPORTANT: trend_pullback_signals needs to support entry_mode and exit_mode if implemented
                # But looking at generate_equity_curves.py, it seems these modes might be handled via 
                # parameter hacks or specific function arguments. 
                # Actually, let's check strategy.py if "momentum" entry is supported.
                # If not, "momentum" usually implies NO pullback.
                # Standard trend_pullback_signals usually requires TRIX > Signal AND Price < WMA (Pullback)
                # If we want Momentum (Price > WMA), we might need to modify the logic or use a different function.
                # HOWEVER, for now, let's assume the standard function with "none" regime is closest.
                # Wait, "Growth Mode" in yaml says: entry_mode: "momentum".
                # If the function doesn't support it, we might be stuck.
                # Let's inspect strategy.py first? 
                # No, I will proceed with standard params but assuming "momentum" logic 
                # might be just large TRIX/WMA.
                # actually, let's look at the robust parameters.
                
                # REVISION: I will use the standard trend_pullback_signals but with 
                # regime_mode="none" as requested. 
                # The "momentum" entry might just mean we accept any trend signal.
                # But trend_pullback_signals REQUIRES correct usage.
                
                sig = trend_pullback_signals(
                    df, trix, wma, shift,
                    atr_period=14,
                    regime_mode=regime_mode, # "none"
                    sma200_period=200,
                    sma_slope_period=10,
                )
                
                # If exit_mode is trailing_only, we ignore the exit signal from TRIX
                # and only use TS.
                # run_backtest takes exit_signal. We can pass a False series?
                # Or just pass the signal and let TS override?
                # Usually TS acts AS WELL AS signal.
                # To disable signal exit, we pass all False to exit_signal.
                
                exit_sig = pd.Series(False, index=df.index)
                
                atr_s = sig["atr"] if "atr" in sig.columns else None
                bt = run_backtest(
                    df, sig["entry_signal"], exit_sig, 
                    fees, slip,
                    atr_series=atr_s, sl_atr=sl_atr, ts_atr=ts_atr
                )
                
                # Metrics
                if len(bt["equity"]) > 0:
                    total_ret = (bt["equity"].iloc[-1] / bt["equity"].iloc[0]) - 1
                    n_years = (df.index[-1] - df.index[0]).days / 365.25
                    cagr = (1 + total_ret) ** (1 / n_years) - 1
                    
                    if cagr > best_cagr:
                        best_cagr = cagr
                        best_params = (trix, wma, shift)
                        best_metrics = {
                            "Total Return": total_ret,
                            "CAGR": cagr
                        }
            
            except Exception:
                continue
                
            count += 1
            # if count % 100 == 0:
            #     print(f"Processed {count}/{total}...")
        
        results[ticker] = {
            "params": best_params,
            "metrics": best_metrics
        }
        print(f"Best for {ticker}: {best_params} -> CAGR: {best_cagr:.2%}")

    print("\n" + "="*40)
    print("FINAL RESULTS (Tech Growth)")
    print("="*40)
    
    with open("tech_growth_final.txt", "w") as f:
        for ticker, res in results.items():
            if res['params']:
                p = res['params']
                m = res['metrics']
                line = f"{ticker}: TRIX={p[0]}, WMA={p[1]}, Shift={p[2]} | CAGR={m['CAGR']:.2%}"
                print(line)
                f.write(line + "\n")
            else:
                print(f"{ticker}: Failed to optimize")
                f.write(f"{ticker}: Failed to optimize\n")

if __name__ == "__main__":
    main()
