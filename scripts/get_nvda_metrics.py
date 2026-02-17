
import sys
import os
import pandas as pd
from pathlib import Path

# Add project root/src to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(project_root, "src")
sys.path.append(src_path)

from trixwma.data import load_ohlcv
from trixwma.strategy import trend_pullback_signals
from trixwma.backtest import run_backtest, compute_metrics, buy_and_hold_metrics

# Configuration
TICKER = "NVDA"
# "NVDA": (8, 20, 10, 0.0, 3.0, "none", 10)
TRIX_PERIOD = 8
WMA_PERIOD = 20
SHIFT = 10
SL_ATR = 0.0
TS_ATR = 3.0
REGIME_MODE = "none"
SMA_SLOPE_PERIOD = 10

START_DATE = "2010-01-01"
END_DATE = "2024-12-31"
DATA_DIR = os.path.join(project_root, "data", "cache")

def run_verification():
    print(f"Running verification for {TICKER} ({START_DATE} to {END_DATE})...")
    
    try:
        # Load Data
        df = load_ohlcv(TICKER, START_DATE, END_DATE, DATA_DIR)
        print(f"Loaded {len(df)} bars.")
        
        # Strategies
        # 1. Generate Signals
        sig = trend_pullback_signals(
            df, 
            trix_period=TRIX_PERIOD, 
            wma_period=WMA_PERIOD, 
            shift=SHIFT,
            atr_period=14,
            regime_mode=REGIME_MODE, # "none"
            sma200_period=200,
            sma_slope_period=SMA_SLOPE_PERIOD
        )
        
        atr_s = sig["atr"]
        entry_sig = sig["entry_signal"]
        
        # Growth Mode Logic: Force exit_signal to False if regime is "none"
        if REGIME_MODE == "none":
            exit_sig = pd.Series(False, index=df.index)
        else:
            exit_sig = sig["exit_signal"]

        # 2. Run Backtest
        bt = run_backtest(
            df, 
            entry_sig, 
            exit_sig, 
            fees_pct=0.001, 
            slippage_pct=0.001,
            atr_series=atr_s, 
            sl_atr=SL_ATR, 
            ts_atr=TS_ATR
        )
        
        # 3. Compute Metrics
        metrics = compute_metrics(bt, df)
        bh_metrics = buy_and_hold_metrics(df, fees_pct=0.001, slippage_pct=0.001)
        
        print("\n--- NVDA METRICS (Ground Truth) ---")
        print(f"CAGR: {metrics['cagr']:.2%}")
        print(f"Total Return: {metrics['total_return']:.2%}")
        print(f"Max Drawdown: {metrics['max_dd']:.2%}")
        print(f"Win Rate: {metrics['win_rate']:.2%}")
        print(f"Trades: {metrics['n_trades']}")
        print(f"Exposure: {metrics['exposure']:.2%}")
        print("-" * 30)
        print(f"Buy & Hold CAGR: {bh_metrics['cagr']:.2%}")
        print("-" * 30)
        
        # Alpha Calculation
        alpha = metrics['cagr'] - bh_metrics['cagr']
        print(f"Alpha: {alpha:.2%}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_verification()
