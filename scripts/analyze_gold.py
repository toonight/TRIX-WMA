
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add project root to path to import trixwma
base_path = Path("d:/Projets/2026/TRIX-WMA")
if str(base_path) not in sys.path:
    sys.path.append(str(base_path))
    
# Also add the robustness folder just in case imports assume relative paths
robustness_path = base_path / "trix_wma_robustness"
if str(robustness_path) not in sys.path:
    sys.path.append(str(robustness_path))

# Note: Adjusting imports based on repo structure. 
# The trixwma package seems to be in src/trixwma or trix_wma_robustness/src/trixwma
# We will try adding src to path
src_path = base_path / "src"
if str(src_path) not in sys.path:
    sys.path.append(str(src_path))

try:
    from trixwma.robustness import compute_robustness_scores, rank_plateaus
    from trixwma.grid import grid_to_tensor
    from trixwma.backtest import buy_and_hold_metrics
    from trixwma.data import load_ohlcv
except ImportError:
    # Try alternate path
    sys.path.append(str(base_path / "trix_wma_robustness/src"))
    from trixwma.robustness import compute_robustness_scores, rank_plateaus
    from trixwma.grid import grid_to_tensor
    from trixwma.backtest import buy_and_hold_metrics
    from trixwma.data import load_ohlcv

def main():
    ticker = "GC=F"
    print(f"Loading data for {ticker}...")
    
    # Data cache location
    data_dir = base_path / "trix_wma_robustness/data/cache"
    df = load_ohlcv(ticker, "2010-01-01", "2024-12-31", str(data_dir))
    
    # Load Grid Parquet
    grid_path = base_path / "trix_wma_robustness/artifacts/runs/metals_opt/grid_GC=F.parquet"
    print(f"Loading grid from {grid_path}...")
    grid_df = pd.read_parquet(grid_path)
    
    # Baseline
    bh = buy_and_hold_metrics(df)
    print(f"Buy & Hold CAGR: {bh['cagr']:.2%}")
    
    # Compute Scores
    print("Computing robustness scores...")
    try:
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
            print("\n--- BEST PLATEAU (OFFICIAL) ---")
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
                
    except Exception as e:
        print(f"Error computing scores: {e}")
        # Fallback: simple max cagr if robustness fails (unlikely)
        best_idx = grid_df['cagr'].idxmax()
        best_row = grid_df.loc[best_idx]
        print("\n--- FALLBACK: MAX CAGR ---")
        print(f"TRIX: {best_row['trix_period']}")
        print(f"WMA:  {best_row['wma_period']}")
        print(f"Shift: {best_row['shift']}")
        print(f"CAGR: {best_row['cagr']:.2%}")

if __name__ == "__main__":
    main()
