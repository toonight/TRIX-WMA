
import pandas as pd
import matplotlib.pyplot as plt
from trixwma.data import load_ohlcv
from trixwma.strategy import trend_pullback_signals
from trixwma.backtest import run_backtest
from trixwma import plots

ticker = "AMZN"
trix_p = 5
wma_p = 37
shift = 2

# Profile settings (Growth)
entry_mode = "momentum"
exit_mode = "trailing_only"
ts_atr = 3.5 # From optimized run (approx)
atr_period = 14

print(f"Generating equity curve for {ticker} (T{trix_p}/W{wma_p}/S{shift})...")
df = load_ohlcv(ticker, "2010-01-01", "2024-12-31", "data/cache")

# Signals
sig = trend_pullback_signals(
    df, trix_p, wma_p, shift,
    atr_period=atr_period,
    regime_mode="none",
    entry_mode=entry_mode,
    exit_mode=exit_mode,
)

# Backtest
bt = run_backtest(
    df, sig["entry_signal"], sig["exit_signal"], 
    0.001, 0.001, 
    atr_series=sig["atr"],
    ts_atr=ts_atr
)

# B&H
bh_ret = df["Close"].pct_change().fillna(0)
bh_eq = (1 + bh_ret).cumprod()
strat_eq = bt["equity"] / bt["equity"].iloc[0]
bh_eq = bh_eq / bh_eq.iloc[0]

from pathlib import Path
save_dir = Path("artifacts/figures")
plots.equity_curves(df, {"Strategy": strat_eq, "Buy & Hold": bh_eq}, save_dir, ticker)
print(f"Saved to {save_dir / f'equity_curves_{ticker}.png'}")
