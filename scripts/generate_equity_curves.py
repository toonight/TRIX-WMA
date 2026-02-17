
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from trixwma.data import load_ohlcv
from trixwma.strategy import trend_pullback_signals
from trixwma.backtest import run_backtest
from trixwma.plots import equity_curves

# Configuration for Showcase Plots
# Ticker -> (TRIX, WMA, SHIFT, SL_ATR, TS_ATR, REGIME_MODE, SMA_SLOPE_PERIOD)
CONFIGS = {
    # Metals
    "GC=F": (7, 17, 10, 3.0, 2.0, "sma_slope", 10),  # Gold (Robust Plateau)
    "SI=F": (7, 15, 10, 2.0, 1.5, "sma_slope", 10), # Silver (Std)
    
    # Forex
    "EURUSD=X": (5, 21, 7, 3.0, 2.0, "sma_slope", 10),
    "GBPUSD=X": (4, 25, 10, 3.0, 2.0, "sma_slope", 10),
    "USDJPY=X": (8, 23, 10, 3.0, 2.0, "sma_slope", 10),
    
    # Energy
    "CL=F": (4, 10, 4, 3.0, 2.0, "sma_slope", 10),
    "NG=F": (4, 10, 7, 3.0, 2.0, "sma_slope", 10),
    "RB=F": (7, 22, 10, 3.0, 2.0, "sma_slope", 10),

    # Tech (Benchmark)
    "TSLA": (7, 18, 6, 2.0, 1.5, "sma_slope", 10),
    
    # Tech Giants (Showcase Performance vs BH)
    "NVDA": (7, 18, 6, 2.0, 1.5, "sma_slope", 10),
    "GOOGL": (7, 18, 6, 2.0, 1.5, "sma_slope", 10),
    "MSFT": (7, 18, 6, 2.0, 1.5, "sma_slope", 10),
    "META": (7, 18, 6, 2.0, 1.5, "sma_slope", 10),
    "AMZN": (7, 18, 6, 2.0, 1.5, "sma_slope", 10),
}

def main():
    base_dir = Path("d:/Projets/2026/TRIX-WMA/trix_wma_robustness")
    data_dir = base_dir / "data" / "cache"
    fig_dir = base_dir / "reports" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    
    start_date = "2010-01-01"
    end_date = "2024-12-31"
    
    fees = 0.001
    slip = 0.001

    print(f"Generating Equity Curves in {fig_dir}...")

    for ticker, params in CONFIGS.items():
        trix, wma, shift, sl, ts, regime, slope_per = params
        print(f"Processing {ticker}...")
        
        try:
            df = load_ohlcv(ticker, start_date, end_date, str(data_dir))
            
            # Strategy
            sig = trend_pullback_signals(
                df, trix, wma, shift,
                atr_period=14,
                regime_mode=regime,
                sma200_period=200,
                sma_slope_period=slope_per,
            )
            atr_s = sig["atr"] if "atr" in sig.columns else None
            bt = run_backtest(
                df, sig["entry_signal"], sig["exit_signal"], 
                fees, slip,
                atr_series=atr_s, sl_atr=sl, ts_atr=ts
            )
            strat_eq = bt["equity"] / bt["equity"].iloc[0]
            
            # Buy & Hold
            bh_ret = df["Close"].pct_change().fillna(0)
            bh_eq = (1 + bh_ret).cumprod()
            bh_eq = bh_eq / bh_eq.iloc[0]
            
            # Plot
            equity_curves(
                df, 
                {"Strategy": strat_eq, "Buy & Hold": bh_eq},
                fig_dir,
                ticker=ticker
            )
            print(f"  Saved equity_curves_{ticker}.png")
            
        except Exception as e:
            print(f"  Failed {ticker}: {e}")

if __name__ == "__main__":
    main()
