"""CLI — single command to run the full pipeline."""
import argparse
import sys
from datetime import datetime
from pathlib import Path

import yaml
import pandas as pd


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(prog="trixwma", description="TRIX+WMA Robustness Research")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run-all", help="Run full pipeline")
    run_p.add_argument("--config", default="config/default.yaml", help="Path to YAML config")

    args = parser.parse_args()

    if args.command == "run-all":
        _run_all(args.config)
    else:
        parser.print_help()
        sys.exit(1)


def _run_all(config_path: str):
    cfg = load_config(config_path)

    # Resolve paths relative to config file location
    base = Path(config_path).resolve().parent.parent
    data_cache = base / "data" / "cache"
    art = base / "artifacts"
    tab_dir = art / "tables"

    # Reports directory (primary output)
    reports_dir = base / "reports"
    fig_dir = reports_dir / "figures"

    run_tag = cfg.get("output_run_tag", "auto")
    if run_tag == "auto":
        run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = art / "runs" / run_tag
    run_dir.mkdir(parents=True, exist_ok=True)

    trix_range = tuple(cfg["trix_period_range"])
    wma_range = tuple(cfg["wma_period_range"])
    shift_range = tuple(cfg["shift_range"])
    fees = cfg.get("fees_pct", 0.001)
    slip = cfg.get("slippage_pct", 0.002)
    rfr = cfg.get("risk_free_rate", 0.0)
    min_trades = cfg.get("min_trades", 30)
    kernel = tuple(cfg.get("neighborhood_kernel", [3, 3, 3]))
    weights = cfg.get("plateau_objective_weights")
    seed = cfg.get("seed", 42)
    plateau_top_n = cfg.get("plateau_top_n", 5)
    bh_frac_threshold = cfg.get("bh_frac_threshold", 0.7)

    # Gap penalty
    gap_atr = cfg.get("gap_penalty_atr_threshold", 0.0)
    gap_slip = cfg.get("gap_extra_slip_pct", 0.005)

    ticker = cfg["tickers"][0]
    start = cfg["start_date"]
    end = cfg["end_date"]

    # ---------- Step 1: Data ----------
    from trixwma.data import load_ohlcv
    print(f"[1/7] Data — {ticker}")
    df = load_ohlcv(ticker, start, end, str(data_cache))
    print(f"  {len(df)} bars loaded")

    # ---------- Step 2: Grid ----------
    from trixwma.grid import evaluate_grid, grid_to_tensor
    print("[2/7] Grid evaluation")
    grid_df = evaluate_grid(
        df, trix_range, wma_range, shift_range, fees, slip, rfr,
        ticker=ticker, start_date=start, end_date=end,
    )
    tab_dir.mkdir(parents=True, exist_ok=True)
    grid_path = tab_dir / f"grid_{ticker}.csv"
    grid_df.to_csv(grid_path, index=False)
    grid_df.to_parquet(run_dir / f"grid_{ticker}.parquet", index=False)
    print(f"  {len(grid_df)} combinations → {grid_path}")

    # ---------- Step 3: Robustness scoring ----------
    from trixwma.robustness import compute_robustness_scores, rank_plateaus
    from trixwma.backtest import buy_and_hold_metrics
    print("[3/7] Robustness scoring")
    bh = buy_and_hold_metrics(df, fees, slip, rfr)
    score, meta, axis_vals = compute_robustness_scores(
        grid_df, grid_to_tensor, bh["cagr"],
        kernel=kernel, weights=weights, min_trades=min_trades,
        bh_frac_threshold=bh_frac_threshold,
    )
    plateaus = rank_plateaus(score, axis_vals, meta, top_n=plateau_top_n)
    plat_df = pd.DataFrame([{k: v for k, v in p.items() if k != "neighbors"} for p in plateaus])
    plat_df.to_csv(tab_dir / f"plateaus_{ticker}.csv", index=False)
    print(f"  {len(plateaus)} plateau centers found")

    # ---------- Step 4: Plots ----------
    from trixwma.plots import (
        heatmap_2d, heatmap_all_shifts, heatmap_best_shift,
        plateau_map, equity_curves,
        walk_forward_plot, mc_distribution_plot,
    )
    print("[4/7] Generating plots")
    shifts = sorted(grid_df["shift"].unique())
    for sv in shifts:
        heatmap_2d(grid_df, sv, "cagr", fig_dir, ticker)
        heatmap_2d(grid_df, sv, "sharpe", fig_dir, ticker)
        heatmap_2d(grid_df, sv, "max_dd", fig_dir, ticker)
    heatmap_all_shifts(grid_df, "cagr", fig_dir, ticker)
    heatmap_all_shifts(grid_df, "sharpe", fig_dir, ticker)
    heatmap_best_shift(grid_df, "cagr", fig_dir, ticker)
    heatmap_best_shift(grid_df, "alpha_cagr", fig_dir, ticker)
    plateau_map(score, axis_vals, fig_dir, ticker)

    # Equity curves: best pixel, best plateau, buy-and-hold
    from trixwma.strategy import baseline_signals
    from trixwma.backtest import run_backtest
    eq_curves = {}

    bh_eq = df["Close"] / df["Close"].iloc[0]
    eq_curves["Buy & Hold"] = bh_eq

    best_row = grid_df.loc[grid_df["cagr"].idxmax()]
    sig_bp = baseline_signals(df, int(best_row["trix_p"]), int(best_row["wma_p"]), int(best_row["shift"]))
    bt_bp = run_backtest(df, sig_bp["entry_signal"], sig_bp["exit_signal"], fees, slip)
    eq_curves["Best Pixel"] = bt_bp["equity"]

    if plateaus:
        p = plateaus[0]
        sig_pl = baseline_signals(df, p["trix_p"], p["wma_p"], p["shift"])
        bt_pl = run_backtest(df, sig_pl["entry_signal"], sig_pl["exit_signal"], fees, slip)
        eq_curves["Best Plateau"] = bt_pl["equity"]

    equity_curves(df, eq_curves, fig_dir, ticker)

    # ---------- Step 5: Walk-forward ----------
    from trixwma.validation import walk_forward
    print("[5/7] Walk-forward validation")
    wf_cfg = cfg.get("walk_forward", {})
    wf_df = walk_forward(
        df, trix_range, wma_range, shift_range,
        train_years=wf_cfg.get("train_years", 5),
        test_years=wf_cfg.get("test_years", 1),
        step_months=wf_cfg.get("step_months", 6),
        embargo_bars=wf_cfg.get("embargo_bars", 5),
        fees_pct=fees, slippage_pct=slip, risk_free_rate=rfr,
        kernel=kernel, weights=weights, min_trades=min_trades,
        ticker=ticker, start_date=start, end_date=end,
    )
    wf_df.to_csv(tab_dir / f"walk_forward_{ticker}.csv", index=False)
    walk_forward_plot(wf_df, fig_dir, ticker)
    print(f"  {len(wf_df)} windows")

    # ---------- Step 6: Monte Carlo ----------
    from trixwma.monte_carlo import monte_carlo_stress, mc_summary as mc_sum_fn
    print("[6/7] Monte Carlo stress tests")
    mc_cfg = cfg.get("monte_carlo", {})
    if plateaus:
        mc_params = plateaus[0]
    else:
        mc_params = {"trix_p": int(best_row["trix_p"]), "wma_p": int(best_row["wma_p"]),
                     "shift": int(best_row["shift"])}
    mc_df = monte_carlo_stress(
        df, mc_params["trix_p"], mc_params["wma_p"], mc_params["shift"],
        n_sims=mc_cfg.get("n_sims", 500),
        base_fees_pct=fees, base_slippage_pct=slip,
        slippage_multiplier_range=tuple(mc_cfg.get("slippage_multiplier_range", [0.5, 2.0])),
        miss_trade_prob=mc_cfg.get("miss_trade_prob", 0.02),
        random_delay_bars=tuple(mc_cfg.get("random_delay_bars", [0, 1])),
        risk_free_rate=rfr,
        seed=seed,
        gap_penalty_atr_threshold=gap_atr,
        gap_extra_slip_pct=gap_slip,
    )
    mc_df.to_csv(tab_dir / f"mc_stress_{ticker}.csv", index=False)
    mc_summary_data = mc_sum_fn(mc_df, bh_cagr=bh["cagr"])
    mc_distribution_plot(mc_df, "cagr", fig_dir, ticker)
    mc_distribution_plot(mc_df, "sharpe", fig_dir, ticker)
    mc_distribution_plot(mc_df, "max_dd", fig_dir, ticker)
    print(f"  {len(mc_df)} simulations")

    # ---------- Step 6b: Multi-asset ----------
    multi_tickers = cfg.get("multi_asset_tickers", cfg["tickers"])
    multi_df = None
    if len(multi_tickers) > 1:
        from trixwma.validation import multi_asset_evaluation
        print(f"[6b/7] Multi-asset evaluation ({len(multi_tickers)} tickers)")
        multi_df = multi_asset_evaluation(
            multi_tickers, start, end,
            trix_range, wma_range, shift_range,
            str(data_cache), fees, slip, rfr,
            kernel, weights, min_trades,
        )
        multi_df.to_csv(tab_dir / "multi_asset.csv", index=False)
        print(f"  {len(multi_df)} tickers processed")
    else:
        multi_df = pd.DataFrame()

    # ---------- Step 7: Report + summary.json ----------
    from trixwma.report import generate_report, write_summary_json
    print("[7/7] Generating report")
    report_path = reports_dir / "latest.md"
    generate_report(
        grid_df, plateaus, wf_df, multi_df,
        mc_summary_data, bh, ticker, fig_dir, report_path,
    )

    # Machine-readable summary
    best_pixel_dict = {
        "trix_p": int(best_row["trix_p"]),
        "wma_p": int(best_row["wma_p"]),
        "shift": int(best_row["shift"]),
        "cagr": float(best_row["cagr"]),
        "alpha_cagr": float(best_row.get("alpha_cagr", 0)),
    }
    write_summary_json(
        ticker, run_tag, plateaus, best_pixel_dict, bh,
        wf_df, mc_summary_data,
        reports_dir / "summary.json",
    )

    print(f"\n✅ Pipeline complete. Run tag: {run_tag}")
    print(f"   Report:       {report_path}")
    print(f"   Summary JSON: {reports_dir / 'summary.json'}")
    print(f"   Figures:      {fig_dir}")
    print(f"   Tables:       {tab_dir}")


if __name__ == "__main__":
    main()
