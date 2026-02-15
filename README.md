# TRIX + WMA Robustness Research Framework

A production-grade Python framework for systematically evaluating the robustness of a TRIX + WMA pullback trading strategy.

This repository implements a rigorous research pipeline that goes beyond simple backtesting to assess **parameter stability (plateaus)**, **out-of-sample generalization (walk-forward)**, and **resilience to stress (Monte Carlo)**.

## Key Features

- **No Lookahead Bias**: Strict "signal at close, execute at next open" design.
- **3D Parameter Grid**: Evaluates TRIX period × WMA period × SHIFT (lookback) to find stable regions.
- **Plateau Scoring**: Ranks parameter sets by neighborhood stability and **Alpha** (outperformance vs Buy & Hold), not just raw return.
- **Walk-Forward Validation**: Rolling OOS testing with embargo periods to verify temporal robustness.
- **Monte Carlo Stress Tests**:
  - Randomized slippage & missed trades.
  - **Gap Penalty Model**: Applies extra slippage when opening gaps exceed ATR thresholds.
- **Multi-Asset Evaluation**: One-command validation across dozens of tickers.
- **Production Reporting**: Generates a unified Markdown report with "GO/NO-GO" verdict and embedded figures.

## Installation

```powershell
git clone https://github.com/toonight/TRIX-WMA.git
cd TRIX-WMA/trix_wma_robustness
pip install -e ".[dev]"
```

## Quick Start

Run the full pipeline with a single command:

```powershell
python -m trixwma run-all --config config/default.yaml
```

This will:
1. Download data (cached to `data/cache/*.parquet`).
2. Run a 3D grid search (TRIX × WMA × SHIFT).
3. Identify robust plateaus using neighborhood convolution.
4. Run walk-forward validation on the best plateaus.
5. Run Monte Carlo stress tests with gap penalties.
6. Generate a final report at `reports/latest.md`.

## Project Structure

```
trix_wma_robustness/
├── config/             # YAML configuration
│   └── default.yaml
├── src/trixwma/        # Source code
│   ├── data.py         # Data loading & caching
│   ├── grid.py         # 3D parameter grid evaluation
│   ├── robustness.py   # Neighborhood plateau scoring
│   ├── validation.py   # Walk-forward & multi-asset
│   ├── monte_carlo.py  # Stress testing & bootstrapping
│   ├── reports.py      # Markdown report generator
│   └── ...
├── tests/              # pytest suite (17 tests)
├── artifacts/          # Generated outputs
│   └── tables/         # CSV/Parquet results
└── reports/            # Final human-readable reports
    ├── latest.md       # Main report with verdict
    ├── summary.json    # Machine-readable summary
    └── figures/        # Generated plots
```

## Configuration (`config/default.yaml`)

Key parameters you might want to tune:

- **`tickers`**: List of assets to analyze (primary ticker detailed in report).
- **`plateau_objective_weights`**: Importance of CAGR vs. MaxDD vs. Stability.
- **`gap_penalty_atr_threshold`**: ATR multiple to trigger gap slippage (default 2.0).
- **`walk_forward`**: Window lengths for train/test splits.

## Methodology

1. **Grid Search**: We exhaustively simulate `TRIX \in [10..20]`, `WMA \in [15..25]`, `SHIFT \in [3..6]`.
2. **Robustness Score**: A composite score is calculated for every 3x3x3 neighborhood:
   $$ Score = Median(\alpha_{CAGR}) - Median(MaxDD) - Std(\alpha_{CAGR}) + BH\_Fraction $$
3. **Selection**: Top-scoring "plateau centers" are selected, rejecting those with too few trades.
4. **Validation**: Selected parameters are tested on unseen data (Walk-Forward) and perturbed conditions (Monte Carlo).
5. **Verdict**: A **GO** verdict requires positive OOS Sharpe, positive Alpha, and robust Monte Carlo survival.

## License

MIT
