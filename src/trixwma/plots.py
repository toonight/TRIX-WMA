"""Plotting utilities — all matplotlib, saved to artifacts/figures/."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _savefig(fig, name: str, fig_dir: Path):
    fig_dir.mkdir(parents=True, exist_ok=True)
    path = fig_dir / f"{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {path}")


def heatmap_2d(
    grid_df: pd.DataFrame,
    shift_val: int,
    metric: str,
    fig_dir: Path,
    ticker: str = "",
):
    """2D heatmap of metric for a single SHIFT slice."""
    sub = grid_df[grid_df["shift"] == shift_val].copy()
    if sub.empty:
        return
    pivot = sub.pivot(index="trix_p", columns="wma_p", values=metric)

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(
        pivot.values, aspect="auto", origin="lower",
        extent=[
            pivot.columns.min() - 0.5, pivot.columns.max() + 0.5,
            pivot.index.min() - 0.5, pivot.index.max() + 0.5,
        ],
        cmap="RdYlGn" if metric != "max_dd" else "RdYlGn_r",
    )
    ax.set_xlabel("WMA Period")
    ax.set_ylabel("TRIX Period")
    title = f"{metric.upper()} — SHIFT={shift_val}"
    if ticker:
        title = f"{ticker} | {title}"
    ax.set_title(title)
    fig.colorbar(im, ax=ax)
    _savefig(fig, f"heatmap_{metric}_shift{shift_val}_{ticker}", fig_dir)


def heatmap_all_shifts(grid_df: pd.DataFrame, metric: str, fig_dir: Path, ticker: str = ""):
    """Small-multiples: one heatmap per SHIFT value."""
    shifts = sorted(grid_df["shift"].unique())
    n = len(shifts)
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 5), squeeze=False)
    for idx, sv in enumerate(shifts):
        ax = axes[0, idx]
        sub = grid_df[grid_df["shift"] == sv]
        pivot = sub.pivot(index="trix_p", columns="wma_p", values=metric)
        im = ax.imshow(
            pivot.values, aspect="auto", origin="lower",
            extent=[
                pivot.columns.min() - 0.5, pivot.columns.max() + 0.5,
                pivot.index.min() - 0.5, pivot.index.max() + 0.5,
            ],
            cmap="RdYlGn" if metric != "max_dd" else "RdYlGn_r",
        )
        ax.set_title(f"SHIFT={sv}")
        ax.set_xlabel("WMA")
        ax.set_ylabel("TRIX")
        fig.colorbar(im, ax=ax)
    suptitle = f"{metric.upper()} across SHIFT"
    if ticker:
        suptitle = f"{ticker} | {suptitle}"
    fig.suptitle(suptitle, fontsize=14)
    fig.tight_layout()
    _savefig(fig, f"heatmap_grid_{metric}_{ticker}", fig_dir)


def plateau_map(
    score_tensor: np.ndarray,
    axis_vals: tuple,
    fig_dir: Path,
    ticker: str = "",
):
    """Plot robustness score as small-multiples across SHIFT slices."""
    tv, wv, sv = axis_vals
    n = len(sv)
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 5), squeeze=False)
    for idx, s in enumerate(sv):
        ax = axes[0, idx]
        slc = score_tensor[:, :, idx]
        im = ax.imshow(
            slc, aspect="auto", origin="lower",
            extent=[wv[0] - 0.5, wv[-1] + 0.5, tv[0] - 0.5, tv[-1] + 0.5],
            cmap="viridis",
        )
        ax.set_title(f"SHIFT={s}")
        ax.set_xlabel("WMA")
        ax.set_ylabel("TRIX")
        fig.colorbar(im, ax=ax)
    suptitle = "Robustness Score (plateau map)"
    if ticker:
        suptitle = f"{ticker} | {suptitle}"
    fig.suptitle(suptitle, fontsize=14)
    fig.tight_layout()
    _savefig(fig, f"plateau_map_{ticker}", fig_dir)


def equity_curves(
    df: pd.DataFrame,
    curves: dict[str, pd.Series],
    fig_dir: Path,
    ticker: str = "",
):
    """Plot multiple equity curves on one chart.

    curves: dict of label -> equity Series.
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    for label, eq in curves.items():
        ax.plot(eq.index, eq.values, label=label, linewidth=1.2)
    ax.set_ylabel("Equity")
    ax.set_xlabel("Date")
    title = "Equity Curves"
    if ticker:
        title = f"{ticker} | {title}"
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    _savefig(fig, f"equity_curves_{ticker}", fig_dir)


def walk_forward_plot(wf_df: pd.DataFrame, fig_dir: Path, ticker: str = ""):
    """Bar chart of OOS CAGR per walk-forward window vs BH."""
    if wf_df.empty:
        return
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(wf_df))
    width = 0.35
    ax.bar(x - width / 2, wf_df["oos_cagr"], width, label="Strategy OOS", color="#2ecc71")
    ax.bar(x + width / 2, wf_df["oos_bh_cagr"], width, label="Buy & Hold OOS", color="#e74c3c")
    ax.set_xlabel("Window")
    ax.set_ylabel("CAGR")
    ax.set_xticks(x)
    ax.set_xticklabels([f"W{i}" for i in x])
    title = "Walk-Forward OOS CAGR"
    if ticker:
        title = f"{ticker} | {title}"
    ax.set_title(title)
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    _savefig(fig, f"walk_forward_{ticker}", fig_dir)


def mc_distribution_plot(mc_df: pd.DataFrame, metric: str, fig_dir: Path, ticker: str = ""):
    """Histogram of MC simulation outcomes for a metric."""
    if mc_df.empty or metric not in mc_df.columns:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    vals = mc_df[metric].dropna()
    ax.hist(vals, bins=50, color="#3498db", edgecolor="white", alpha=0.8)
    ax.axvline(vals.median(), color="red", linestyle="--", label=f"Median={vals.median():.4f}")
    ax.axvline(vals.quantile(0.05), color="orange", linestyle=":", label=f"5th pct={vals.quantile(0.05):.4f}")
    ax.set_xlabel(metric.upper())
    ax.set_ylabel("Count")
    title = f"Monte Carlo — {metric.upper()}"
    if ticker:
        title = f"{ticker} | {title}"
    ax.set_title(title)
    ax.legend()
    _savefig(fig, f"mc_{metric}_{ticker}", fig_dir)


def heatmap_best_shift(
    grid_df: pd.DataFrame,
    metric: str,
    fig_dir: Path,
    ticker: str = "",
):
    """Best-of-SHIFT projection: for each (TRIX, WMA) pick the SHIFT with max metric."""
    idx = grid_df.groupby(["trix_p", "wma_p"])[metric].idxmax()
    best = grid_df.loc[idx]
    pivot = best.pivot(index="trix_p", columns="wma_p", values=metric)

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(
        pivot.values, aspect="auto", origin="lower",
        extent=[
            pivot.columns.min() - 0.5, pivot.columns.max() + 0.5,
            pivot.index.min() - 0.5, pivot.index.max() + 0.5,
        ],
        cmap="RdYlGn" if metric != "max_dd" else "RdYlGn_r",
    )
    ax.set_xlabel("WMA Period")
    ax.set_ylabel("TRIX Period")
    title = f"Best-of-SHIFT — {metric.upper()}"
    if ticker:
        title = f"{ticker} | {title}"
    ax.set_title(title)
    fig.colorbar(im, ax=ax)
    _savefig(fig, f"heatmap_bestshift_{metric}_{ticker}", fig_dir)

