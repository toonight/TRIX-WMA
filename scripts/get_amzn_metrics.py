
import sys
import os
import pandas as pd
import numpy as np

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from trixwma.data import load_ohlcv
from trixwma.strategy import trend_pullback_signals
from trixwma.backtest import run_backtest, compute_metrics

def main():
    sys.stdout = open("amzn_audit.txt", "w")
    ticker = "AMZN"
    # Optimised Growth Mode params (Grid Search 2026-02-17)
    # TRIX=4, TS=3.0, regime=none, entry=momentum, exit=trailing_only
    # WMA and Shift have NO effect in momentum mode (no pullback filter)
    trix_len = 4
    wma_len = 30
    shift = 10
    sl_atr = 0.0
    ts_atr = 3.0
    regime = "none" # Growth Mode
    sma_slope = 10

    print(f"--- Verifying {ticker} Metrics (Optimised Growth Mode) ---")
    print(f"Params: TRIX={trix_len}, WMA={wma_len}, Shift={shift}, Regime={regime}, TS={ts_atr}")

    # Load Data
    df = load_ohlcv(ticker, start="2010-01-01", end="2024-12-31")
    
    # Run Strategy
    signals = trend_pullback_signals(
        df, 
        trix_period=trix_len, 
        wma_period=wma_len, 
        shift=shift,
        regime_mode=regime,
        entry_mode="momentum",
        exit_mode="trailing_only",
        trix_exit_threshold=0.0
    )
    
    # Backtest (must match optimization grid parameters)
    backtest_results = run_backtest(
        df, 
        signals['entry_signal'], 
        signals['exit_signal'],
        fees_pct=0.001,
        slippage_pct=0.001,
        atr_series=signals['atr'],
        ts_atr=ts_atr,
        sl_atr=sl_atr
    )
    
    # Compute Metrics
    metrics = compute_metrics(backtest_results, df)
    
    print("\n--- GROUND TRUTH METRICS (Base: 8/30/10) ---")
    print(f"CAGR: {metrics['cagr']:.2%}")
    # Buy Hold CAGR might not be returned directly if not calculated relative to DF, 
    # but let's assume we can calc it or it is missing. 
    # Wait, compute_metrics in backtest.py DOES NOT compute buy_hold_cagr.
    # We must calculate Buy & Hold CAGR manually here or check if it's available.
    # Looking at compute_metrics code, it only uses 'equity' from bt.
    # We need to calculate BH from df.
    
    bh_total_ret = df['Close'].iloc[-1] / df['Close'].iloc[0] - 1
    n_years = (df.index[-1] - df.index[0]).days / 365.25
    bh_cagr = (1 + bh_total_ret) ** (1 / n_years) - 1
    
    print(f"BH_CAGR: {bh_cagr:.2%}")
    print(f"Alpha: {metrics['cagr'] - bh_cagr:.2%}")
    print(f"MaxDD: {metrics['max_dd']:.2%}")
    print(f"Trades: {metrics['n_trades']}")
    print(f"WinRate: {metrics['win_rate']:.2%}")
    print("")

    # --- Generate Plot ---
    import matplotlib.pyplot as plt
    plt.figure(figsize=(10, 6))
    
    # Calculate Equity Curves (Normalized to start at 1)
    strategy_equity = backtest_results['equity']
    # Re-normalize just in case
    strategy_equity = strategy_equity / strategy_equity.iloc[0]
    
    # Buy & Hold Equity
    buy_hold_equity = df['Close'] / df['Close'].iloc[0]
    
    plt.plot(strategy_equity.index, strategy_equity, label='Strategy')
    plt.plot(buy_hold_equity.index, buy_hold_equity, label='Buy & Hold', alpha=0.7)
    
    plt.title(f"{ticker} | Equity Curves")
    plt.xlabel("Date")
    plt.ylabel("Equity")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    output_path = "amzn_equity_curve.png"
    plt.savefig(output_path)
    print(f"Plot saved to {output_path}")
    plt.close()
    
    # --- TEST 2: Alt-Text Params (5, 37, 2) which claims 34.3% CAGR ---
    print("\n--- Verifying AMZN Metrics (Alt-Text: 5/37/2) ---")
    signals_opt = trend_pullback_signals(
        df, trix_period=5, wma_period=37, shift=2, regime_mode=regime,
        exit_mode="trailing_only", trix_exit_threshold=0.0
    )
    bt_opt = run_backtest(df, signals_opt['entry_signal'], signals_opt['exit_signal'], ts_atr=ts_atr, sl_atr=sl_atr)
    metrics_opt = compute_metrics(bt_opt, df)
    
    print(f"CAGR: {metrics_opt['cagr']:.2%}")
    print(f"Alpha: {metrics_opt['cagr'] - bh_cagr:.2%}")
    print(f"MaxDD: {metrics_opt['max_dd']:.2%}")

    # --- TEST 3: Alt-Text Params (5, 37, 2) with SMA_SLOPE Regime ---
    print("\n--- Verifying AMZN Metrics (Alt-Text: 5/37/2 + SMA Slope) ---")
    signals_slope = trend_pullback_signals(
        df, trix_period=5, wma_period=37, shift=2, regime_mode="sma_slope",
        exit_mode="trix_cross", trix_exit_threshold=0.0
    )
    bt_slope = run_backtest(df, signals_slope['entry_signal'], signals_slope['exit_signal'], ts_atr=ts_atr, sl_atr=sl_atr)
    metrics_slope = compute_metrics(bt_slope, df)
    
    print(f"CAGR: {metrics_slope['cagr']:.2%}")
    print(f"Alpha: {metrics_slope['cagr'] - bh_cagr:.2%}")
    print(f"MaxDD: {metrics_slope['max_dd']:.2%}")

if __name__ == "__main__":
    main()
