"""Final report generator — writes Markdown with embedded figure links.

Outputs to ``reports/latest.md`` with figures in ``reports/figures/``.
Also writes ``reports/summary.json`` for machine consumption.
"""
from pathlib import Path
import json
import pandas as pd
import numpy as np


def generate_report(
    grid_df: pd.DataFrame,
    plateaus: list[dict],
    wf_df: pd.DataFrame,
    multi_df: pd.DataFrame,
    mc_summary_data: dict,
    bh_metrics: dict,
    ticker: str,
    fig_dir: Path,
    out_path: Path,
):
    """Write the final Markdown report to *out_path*."""
    lines: list[str] = []
    _h = lines.append

    _h("# TRIX + WMA Robustness Evaluation Report\n")
    _h(f"**Primary Ticker:** {ticker}\n")

    # 1 — Problem framing
    _h("## 1. Problem Framing\n")
    _h("Optimizing a trading strategy on a 2D parameter grid (TRIX period × WMA period) "
       "often produces a **single bright pixel** that looks impressive in-sample but is "
       "fragile: small parameter changes destroy performance.\n")
    _h("By adding the SHIFT dimension and evaluating a 3D grid, we expose how that bright "
       "pixel fragments across timing perturbations. The solution is to find **plateaus** — "
       "regions where the *neighborhood* of parameters performs consistently well.\n")

    # 2 — Strategy definition
    _h("## 2. Strategy Definition\n")
    _h("- **WMA(period):** Weighted Moving Average with linearly increasing weights.\n")
    _h("- **TRIX(period):** 1-bar % change of triple-smoothed EMA.\n")
    _h("- **Entry:** Pullback condition (WMA_t < WMA_{t−shift}) AND TRIX crosses above 0.\n")
    _h("- **Exit:** TRIX crosses below 0.\n")
    _h("- **Execution:** Signals at close of bar t → fill at open of bar t+1 (no lookahead).\n")
    _h("- **Frictions:** Fees + slippage applied at execution.\n")

    # 3 — Buy-and-Hold baseline
    _h("## 3. Buy-and-Hold Baseline\n")
    _h(_metrics_table(bh_metrics, "Buy & Hold"))
    _h("")

    # 4 — 2D results
    _h("## 4. 2D Grid Results\n")
    shifts = sorted(grid_df["shift"].unique())
    for sv in shifts:
        _h(f"![CAGR SHIFT={sv}](figures/heatmap_cagr_shift{sv}_{ticker}.png)\n")

    # Best-of-shift
    _h("### Best-of-SHIFT Projection\n")
    _h(f"![Best-of-SHIFT CAGR](figures/heatmap_bestshift_cagr_{ticker}.png)\n")

    # 5 — 3D grid
    _h("## 5. 3D Results — Fragmentation Across SHIFT\n")
    _h(f"![CAGR grid](figures/heatmap_grid_cagr_{ticker}.png)\n")

    # 6 — Plateau scoring
    _h("## 6. Plateau Scoring\n")
    _h("Score = w₁·norm(median_alpha_CAGR) − w₂·norm(|median_MaxDD|) + w₃·norm(median_Sharpe)")
    _h(" − w₄·norm(std_alpha_CAGR) + w₅·frac_beating_BH\n")
    _h(f"![Plateau map](figures/plateau_map_{ticker}.png)\n")

    if plateaus:
        _h("### Top Plateau Centers\n")
        _h("| Rank | TRIX | WMA | SHIFT | Score | α-CAGR_med | MaxDD_med | Sharpe_med | α-CAGR_std | BH_frac |")
        _h("|------|------|-----|-------|-------|------------|-----------|------------|------------|---------|")
        for i, p in enumerate(plateaus[:10]):
            _h(f"| {i+1} | {p['trix_p']} | {p['wma_p']} | {p['shift']} | "
               f"{p['score']:.3f} | {p.get('nb_alpha_cagr_median', 0):.4f} | "
               f"{p['nb_maxdd_median']:.4f} | {p['nb_sharpe_median']:.3f} | "
               f"{p['nb_cagr_std']:.4f} | {p['nb_bh_frac']:.2f} |")
        _h("")

        # Pixel vs plateau
        best_pixel = grid_df.loc[grid_df["cagr"].idxmax()]
        _h("### Best Pixel vs Best Plateau\n")
        _h(f"- **Best Pixel:** TRIX={int(best_pixel['trix_p'])}, WMA={int(best_pixel['wma_p'])}, "
           f"SHIFT={int(best_pixel['shift'])} → CAGR={best_pixel['cagr']:.4f}, "
           f"α-CAGR={best_pixel.get('alpha_cagr', 0):.4f}")
        _h(f"- **Best Plateau:** TRIX={plateaus[0]['trix_p']}, WMA={plateaus[0]['wma_p']}, "
           f"SHIFT={plateaus[0]['shift']} → α-CAGR median={plateaus[0].get('nb_alpha_cagr_median', 0):.4f}\n")

    # 7 — Walk-forward
    _h("## 7. Walk-Forward OOS Results\n")
    if wf_df is not None and not wf_df.empty:
        _h(f"![Walk-forward](figures/walk_forward_{ticker}.png)\n")
        _h("| Window | Test Period | Params | OOS CAGR | OOS Sharpe | OOS MaxDD | Beats BH |")
        _h("|--------|------------|--------|----------|-----------|----------|----------|")
        for _, r in wf_df.iterrows():
            test_p = f"{str(r.get('test_start', ''))[:10]}→{str(r.get('test_end', ''))[:10]}"
            params = f"T{r.get('param_trix_p', '?')}/W{r.get('param_wma_p', '?')}/S{r.get('param_shift', '?')}"
            _h(f"| W{int(r.get('window', 0))} | {test_p} | {params} | "
               f"{r.get('oos_cagr', 0):.4f} | {r.get('oos_sharpe', 0):.3f} | "
               f"{r.get('oos_max_dd', 0):.4f} | {r.get('oos_beats_bh', False)} |")
        _h("")
    else:
        _h("Walk-forward data insufficient.\n")

    # 8 — Multi-asset
    _h("## 8. Multi-Asset Results\n")
    if multi_df is not None and not multi_df.empty:
        _h("| Ticker | TRIX | WMA | SHIFT | Score | CAGR | α-CAGR | Sharpe | MaxDD | BH CAGR | Beats BH |")
        _h("|--------|------|-----|-------|-------|------|--------|--------|-------|---------|----------|")
        for _, r in multi_df.iterrows():
            if "error" in r and pd.notna(r.get("error")):
                _h(f"| {r['ticker']} | — | — | — | — | — | — | — | — | — | ERROR |")
                continue
            _h(f"| {r.get('ticker', '')} | {r.get('trix_p', '')} | {r.get('wma_p', '')} | "
               f"{r.get('shift', '')} | {_fmt(r.get('robustness_score'))} | "
               f"{_fmt(r.get('cagr'))} | {_fmt(r.get('alpha_cagr'))} | "
               f"{_fmt(r.get('sharpe'))} | {_fmt(r.get('max_dd'))} | "
               f"{_fmt(r.get('bh_cagr'))} | {r.get('beats_bh', '')} |")
        _h("")
        if "beats_bh" in multi_df.columns:
            frac = multi_df["beats_bh"].mean()
            _h(f"**Fraction beating BH:** {frac:.1%}\n")

    # 9 — Monte Carlo
    _h("## 9. Monte Carlo Stress Results\n")
    if mc_summary_data:
        _h(f"![MC CAGR](figures/mc_cagr_{ticker}.png)\n")
        _h(f"![MC Sharpe](figures/mc_sharpe_{ticker}.png)\n")
        for metric, stats in mc_summary_data.items():
            if metric == "prob_underperform_bh":
                _h(f"**Probability of underperforming Buy & Hold:** {stats:.1%}\n")
                continue
            if not isinstance(stats, dict):
                continue
            _h(f"### {metric.upper()}")
            _h(f"- Median: {stats['median']:.4f}")
            _h(f"- 5th percentile: {stats['p5']:.4f}")
            _h(f"- 95th percentile: {stats['p95']:.4f}")
            _h(f"- Std: {stats['std']:.4f}\n")

    # 10 — Verdict
    _h("## 10. Verdict\n")
    verdict = _compute_verdict(wf_df, mc_summary_data, plateaus)
    if verdict == "GO":
        _h("**✅ GO** — Strategy shows evidence of robust outperformance across OOS windows "
           "and stress tests. Plateau-selected parameters are recommended for paper trading.\n")
    else:
        _h("**❌ NO-GO** — Strategy does not demonstrate sufficient robustness. Plateau "
           "performance degrades out-of-sample or under stress. Further research needed.\n")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  report → {out_path}")


def write_summary_json(
    ticker: str,
    run_tag: str,
    plateaus: list[dict],
    best_pixel: dict,
    bh_metrics: dict,
    wf_df: pd.DataFrame | None,
    mc_summary_data: dict,
    out_path: Path,
):
    """Write machine-readable summary JSON."""
    # Strip neighbor lists for compactness
    clean_plateaus = []
    for p in plateaus:
        cp = {k: v for k, v in p.items() if k != "neighbors"}
        clean_plateaus.append(cp)

    verdict = _compute_verdict(wf_df, mc_summary_data, plateaus)

    oos_summary = {}
    if wf_df is not None and not wf_df.empty:
        oos_summary = {
            "n_windows": len(wf_df),
            "median_oos_cagr": float(wf_df["oos_cagr"].median()) if "oos_cagr" in wf_df.columns else None,
            "median_oos_sharpe": float(wf_df["oos_sharpe"].median()) if "oos_sharpe" in wf_df.columns else None,
            "frac_beats_bh": float(wf_df["oos_beats_bh"].mean()) if "oos_beats_bh" in wf_df.columns else None,
        }

    doc = {
        "run_tag": run_tag,
        "ticker": ticker,
        "selected_plateaus": clean_plateaus,
        "best_pixel": best_pixel,
        "bh_metrics": bh_metrics,
        "oos_summary": oos_summary,
        "mc_summary": mc_summary_data,
        "verdict": verdict,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, default=str), encoding="utf-8")
    print(f"  summary.json → {out_path}")


def _compute_verdict(wf_df, mc_summary_data, plateaus) -> str:
    """GO if OOS median Sharpe > 0, median alpha > 0, MC p5 CAGR > 0."""
    if not plateaus:
        return "NO-GO"

    # OOS checks
    oos_ok = True
    if wf_df is not None and not wf_df.empty:
        if "oos_sharpe" in wf_df.columns:
            oos_ok = wf_df["oos_sharpe"].median() > 0
    else:
        oos_ok = False

    # MC checks
    mc_ok = True
    if mc_summary_data and "cagr" in mc_summary_data:
        cagr_stats = mc_summary_data["cagr"]
        if isinstance(cagr_stats, dict):
            mc_ok = cagr_stats.get("p5", 0) > 0

    # Alpha check
    alpha_ok = plateaus[0].get("nb_alpha_cagr_median", 0) > 0

    return "GO" if (oos_ok and mc_ok and alpha_ok) else "NO-GO"


def _metrics_table(m: dict, label: str) -> str:
    lines = [f"| Metric | {label} |", "|--------|---------|"]
    for k, v in m.items():
        lines.append(f"| {k} | {_fmt(v)} |")
    return "\n".join(lines)


def _fmt(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v)
