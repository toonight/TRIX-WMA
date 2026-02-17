
import pandas as pd
import numpy as np
from trixwma.robustness import compute_robustness_scores, rank_plateaus
from trixwma.grid import grid_to_tensor
from trixwma.backtest import buy_and_hold_metrics
from trixwma.data import load_ohlcv

# Load Data and Grid
ticker = "AMZN"
print(f"Loading data for {ticker}...")
df = load_ohlcv(ticker, "2010-01-01", "2024-12-31", "data/cache")
grid_df = pd.read_csv("artifacts/tables/grid_AMZN.csv")

# Baseline
bh = buy_and_hold_metrics(df)
print(f"Buy & Hold CAGR: {bh['cagr']:.2%}")

# Compute Scores
print("Computing robustness scores...")
score, meta, axis = compute_robustness_scores(
    grid_df, grid_to_tensor, bh["cagr"],
    kernel=(3, 3, 3), 
    min_trades=15,
    bh_frac_threshold=0.4
)

# Rank
ranked = rank_plateaus(score, axis, meta, top_n=5)

if not ranked:
    print("No robust plateau found.")
else:
    best = ranked[0]
    print("\n--- BEST PLATEAU ---")
    print(f"TRIX: {best['trix_p']}")
    print(f"WMA:  {best['wma_p']}")
    print(f"Shift: {best['shift']}")
    print(f"Score: {best['score']:.4f}")
    print(f"Median CAGR: {best['nb_cagr_median']:.2%}")
    print(f"Median Alpha: {best['nb_alpha_cagr_median']:.2%}")
    print(f"Frac > BH: {best['nb_bh_frac']:.2%}")

    if best['nb_cagr_median'] > bh['cagr']:
        print("\n✅ VERDICT: BEATS BUY & HOLD")
    else:
        print("\n❌ VERDICT: FAILS TO BEAT BUY & HOLD")
