"""
Optimise AMZN parameters across Growth Mode (momentum entry, trailing_only exit)
and also Benchmark Mode (pullback entry, trix_cross exit with sma_slope regime).

Grid is wider than the original optimize_tech_growth.py to explore more options.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import itertools
import sys
import time

# Add project root to path
base_path = Path("d:/Projets/2026/TRIX-WMA")
sys.path.insert(0, str(base_path / "src"))

from trixwma.data import load_ohlcv
from trixwma.strategy import trend_pullback_signals
from trixwma.backtest import run_backtest, compute_metrics

def run_grid(df, profile_name, entry_mode, exit_mode, regime_mode,
             trix_range, wma_range, shift_range, ts_atr_range, sl_atr=0.0):
    """Run grid search and return sorted results."""
    results = []
    total = len(trix_range) * len(wma_range) * len(shift_range) * len(ts_atr_range)
    count = 0
    t0 = time.time()

    for trix_p, wma_p, shift_p, ts_atr in itertools.product(
        trix_range, wma_range, shift_range, ts_atr_range
    ):
        try:
            sig = trend_pullback_signals(
                df, trix_p, wma_p, shift_p,
                atr_period=14,
                regime_mode=regime_mode,
                sma200_period=200,
                sma_slope_period=10,
                entry_mode=entry_mode,
                exit_mode=exit_mode,
                trix_exit_threshold=0.0,
            )

            bt = run_backtest(
                df, sig["entry_signal"], sig["exit_signal"],
                fees_pct=0.001, slippage_pct=0.001,
                atr_series=sig["atr"], sl_atr=sl_atr, ts_atr=ts_atr
            )

            metrics = compute_metrics(bt, df)
            
            # Buy & Hold
            bh_total = df['Close'].iloc[-1] / df['Close'].iloc[0] - 1
            n_years = (df.index[-1] - df.index[0]).days / 365.25
            bh_cagr = (1 + bh_total) ** (1 / n_years) - 1

            results.append({
                "profile": profile_name,
                "trix": trix_p,
                "wma": wma_p,
                "shift": shift_p,
                "ts_atr": ts_atr,
                "sl_atr": sl_atr,
                "cagr": metrics["cagr"],
                "bh_cagr": bh_cagr,
                "alpha": metrics["cagr"] - bh_cagr,
                "max_dd": metrics["max_dd"],
                "n_trades": metrics["n_trades"],
                "win_rate": metrics["win_rate"],
                "sharpe": metrics.get("sharpe", 0),
            })

        except Exception:
            pass

        count += 1
        if count % 200 == 0:
            elapsed = time.time() - t0
            print(f"  [{profile_name}] {count}/{total} ({elapsed:.1f}s)")

    return pd.DataFrame(results)


def main():
    ticker = "AMZN"
    start_date = "2010-01-01"
    end_date = "2024-12-31"

    print(f"Loading {ticker}...")
    df = load_ohlcv(ticker, start_date, end_date)

    # ---- Profile 1: Growth Mode (momentum + trailing_only + no regime) ----
    print("\n=== GROWTH MODE (momentum + trailing_only) ===")
    growth_results = run_grid(
        df, "growth",
        entry_mode="momentum",
        exit_mode="trailing_only",
        regime_mode="none",
        trix_range=range(4, 16, 2),     # [4, 6, 8, 10, 12, 14]
        wma_range=range(10, 46, 5),     # [10, 15, 20, 25, 30, 35, 40, 45]
        shift_range=range(2, 12, 2),    # [2, 4, 6, 8, 10]
        ts_atr_range=[1.5, 2.0, 2.5, 3.0, 4.0],
    )

    # ---- Profile 2: Benchmark Mode (pullback + trix_cross + sma_slope) ----
    print("\n=== BENCHMARK MODE (pullback + trix_cross + sma_slope) ===")
    bench_results = run_grid(
        df, "benchmark",
        entry_mode="pullback",
        exit_mode="trix_cross",
        regime_mode="sma_slope",
        trix_range=range(4, 16, 2),
        wma_range=range(10, 46, 5),
        shift_range=range(2, 12, 2),
        ts_atr_range=[1.5, 2.0, 2.5, 3.0],
        sl_atr=2.0,
    )

    # ---- Profile 3: Momentum + trix_cross exit (hybrid) ----
    print("\n=== HYBRID MODE (momentum + trix_cross + sma_slope) ===")
    hybrid_results = run_grid(
        df, "hybrid",
        entry_mode="momentum",
        exit_mode="trix_cross",
        regime_mode="sma_slope",
        trix_range=range(4, 16, 2),
        wma_range=range(10, 46, 5),
        shift_range=range(2, 12, 2),
        ts_atr_range=[0.0, 1.5, 2.0, 3.0],
        sl_atr=0.0,
    )

    # Combine all
    all_results = pd.concat([growth_results, bench_results, hybrid_results], ignore_index=True)

    # Sort by CAGR
    all_results = all_results.sort_values("cagr", ascending=False)

    # Save full results
    out_path = base_path / "amzn_optimization_results.csv"
    all_results.to_csv(out_path, index=False)

    # Print top results per profile
    print("\n" + "=" * 70)
    print(f"AMZN OPTIMIZATION RESULTS — Top 5 per profile")
    print("=" * 70)

    for profile in ["growth", "benchmark", "hybrid"]:
        subset = all_results[all_results["profile"] == profile].head(5)
        print(f"\n--- {profile.upper()} ---")
        for _, row in subset.iterrows():
            print(f"  TRIX={int(row['trix'])}, WMA={int(row['wma'])}, Shift={int(row['shift'])}, "
                  f"TS={row['ts_atr']:.1f} | "
                  f"CAGR={row['cagr']:.2%} | BH={row['bh_cagr']:.2%} | "
                  f"Alpha={row['alpha']:.2%} | MaxDD={row['max_dd']:.2%} | "
                  f"Trades={int(row['n_trades'])} | WR={row['win_rate']:.0%}")

    # Overall best
    print(f"\n{'='*70}")
    print("OVERALL TOP 10:")
    print("=" * 70)
    for _, row in all_results.head(10).iterrows():
        print(f"  [{row['profile']:>10}] TRIX={int(row['trix'])}, WMA={int(row['wma'])}, "
              f"Shift={int(row['shift'])}, TS={row['ts_atr']:.1f} | "
              f"CAGR={row['cagr']:.2%} | Alpha={row['alpha']:.2%} | "
              f"MaxDD={row['max_dd']:.2%} | Trades={int(row['n_trades'])} | WR={row['win_rate']:.0%}")

    print(f"\nTotal combinations tested: {len(all_results)}")
    print(f"Results saved to {out_path}")


if __name__ == "__main__":
    main()
