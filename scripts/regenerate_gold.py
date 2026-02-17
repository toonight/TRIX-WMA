
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from trixwma.data import load_ohlcv
from trixwma.strategy import trend_pullback_signals
from trixwma.backtest import run_backtest
from trixwma.plots import equity_curves

def main():
    ticker = "GC=F"
    # Robust Parameters (T7, W17, S10)
    trix, wma, shift = 7, 17, 10
    sl, ts = 3.0, 2.0
    regime = "sma_slope"
    slope_per = 10
    
    base_dir = Path("d:/Projets/2026/TRIX-WMA/trix_wma_robustness")
    data_dir = base_dir / "data" / "cache"
    fig_dir = Path("d:/Projets/2026/TRIX-WMA/reports/figures")
    fig_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating optimized chart for {ticker}...")
    try:
        df = load_ohlcv(ticker, "2010-01-01", "2024-12-31", str(data_dir))
        
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
            0.001, 0.001,
            atr_series=atr_s, sl_atr=sl, ts_atr=ts
        )
        strat_eq = bt["equity"] / bt["equity"].iloc[0]
        
        bh_ret = df["Close"].pct_change().fillna(0)
        bh_eq = (1 + bh_ret).cumprod()
        bh_eq = bh_eq / bh_eq.iloc[0]
        
        # Calculate Metrics for Verification
        strat_cagr = (strat_eq.iloc[-1]) ** (1/((df.index[-1] - df.index[0]).days/365.25)) - 1
        bh_cagr = (bh_eq.iloc[-1]) ** (1/((df.index[-1] - df.index[0]).days/365.25)) - 1
        print(f"Strategy CAGR: {strat_cagr:.2%}")
        print(f"Buy & Hold CAGR: {bh_cagr:.2%}")
        
        equity_curves(
            df, 
            {"Strategy": strat_eq, "Buy & Hold": bh_eq},
            fig_dir,
            ticker=ticker
        )
        print(f"Saved {fig_dir / f'equity_curves_{ticker}.png'}")
        
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
