"""Monte Carlo stress tests for strategy robustness.

Includes gap-penalty model: when next-open gap exceeds a configurable
ATR threshold, additional slippage is applied.
"""
import numpy as np
import pandas as pd
from trixwma.strategy import baseline_signals
from trixwma.backtest import run_backtest, compute_metrics
from trixwma.indicators import atr as compute_atr


def monte_carlo_stress(
    df: pd.DataFrame,
    trix_p: int,
    wma_p: int,
    shift: int,
    n_sims: int = 500,
    base_fees_pct: float = 0.001,
    base_slippage_pct: float = 0.002,
    slippage_multiplier_range: tuple[float, float] = (0.5, 2.0),
    miss_trade_prob: float = 0.02,
    random_delay_bars: tuple[int, int] = (0, 1),
    risk_free_rate: float = 0.0,
    seed: int = 42,
    gap_penalty_atr_threshold: float = 0.0,
    gap_extra_slip_pct: float = 0.005,
) -> pd.DataFrame:
    """Run Monte Carlo stress tests on a given parameter set.

    Perturbations per simulation:
      - Randomized slippage multiplier
      - Randomly missed trades (entry signals dropped)
      - Random execution delay (0 or 1 extra bars)
      - Gap penalty: if |Open_t − Close_{t-1}| / ATR > threshold,
        apply extra slippage on that bar's fill.

    Parameters
    ----------
    gap_penalty_atr_threshold : set > 0 to enable gap penalty model.
    gap_extra_slip_pct : extra slippage applied on gap bars.

    Returns DataFrame with one row per simulation containing metrics.
    """
    rng = np.random.default_rng(seed)

    sig = baseline_signals(df, trix_p, wma_p, shift)
    base_entry = sig["entry_signal"].values.copy()
    base_exit = sig["exit_signal"].values.copy()
    n = len(df)

    # Pre-compute gap mask if gap penalty is enabled
    gap_mask = np.zeros(n, dtype=bool)
    if gap_penalty_atr_threshold > 0:
        atr_vals = compute_atr(df["High"], df["Low"], df["Close"], 14).values
        opens = df["Open"].values
        closes = df["Close"].values
        for i in range(1, n):
            if atr_vals[i] > 0 and not np.isnan(atr_vals[i]):
                gap_ratio = abs(opens[i] - closes[i - 1]) / atr_vals[i]
                if gap_ratio > gap_penalty_atr_threshold:
                    gap_mask[i] = True

    results = []
    for sim in range(n_sims):
        slip_mult = rng.uniform(*slippage_multiplier_range)
        sim_slippage = base_slippage_pct * slip_mult

        # For gap-penalty sims, we need per-bar slippage — handled via
        # a modified backtest where gap bars get extra cost.
        # We approximate by adding gap penalty to base slippage for the
        # whole run when any gap bar coincides with a trade execution.
        effective_slippage = sim_slippage
        if gap_penalty_atr_threshold > 0:
            # Compute fraction of entry bars that fall on gap bars
            entry = base_entry.copy()
            miss_mask_sim = rng.random(n) < miss_trade_prob
            entry[miss_mask_sim] = False
            delay = rng.integers(random_delay_bars[0], random_delay_bars[1] + 1)
            if delay > 0:
                entry = np.roll(entry, delay)
                entry[:delay] = False

            # Shift entry forward by 1 (as backtest does)
            exec_bars = np.zeros(n, dtype=bool)
            exec_bars[1:] = entry[:-1]
            gap_trade_frac = (exec_bars & gap_mask).sum() / max(exec_bars.sum(), 1)
            effective_slippage += gap_extra_slip_pct * gap_trade_frac

            entry_s = pd.Series(entry, index=df.index)
        else:
            entry = base_entry.copy()
            miss_mask_sim = rng.random(n) < miss_trade_prob
            entry[miss_mask_sim] = False
            delay = rng.integers(random_delay_bars[0], random_delay_bars[1] + 1)
            if delay > 0:
                entry = np.roll(entry, delay)
                entry[:delay] = False
            entry_s = pd.Series(entry, index=df.index)

        exit_s = pd.Series(base_exit, index=df.index)
        bt = run_backtest(df, entry_s, exit_s, base_fees_pct, effective_slippage)
        m = compute_metrics(bt, df, risk_free_rate)
        m["sim"] = sim
        m["slippage_mult"] = slip_mult
        m["delay_bars"] = delay
        m["gap_slip_added"] = effective_slippage - sim_slippage
        results.append(m)

        if (sim + 1) % 100 == 0:
            print(f"  MC: {sim + 1}/{n_sims}")

    return pd.DataFrame(results)


def mc_summary(mc_df: pd.DataFrame, bh_cagr: float = 0.0) -> dict:
    """Summarize Monte Carlo results.

    Returns dict with percentile stats plus ``prob_underperform_bh``.
    """
    summary = {}
    for col in ["cagr", "sharpe", "max_dd", "total_return", "n_trades"]:
        if col in mc_df.columns:
            vals = mc_df[col].dropna()
            summary[col] = {
                "median": float(vals.median()),
                "p5": float(vals.quantile(0.05)),
                "p25": float(vals.quantile(0.25)),
                "p75": float(vals.quantile(0.75)),
                "p95": float(vals.quantile(0.95)),
                "mean": float(vals.mean()),
                "std": float(vals.std()),
            }

    # Probability of underperforming buy-and-hold
    if "cagr" in mc_df.columns:
        cagr_vals = mc_df["cagr"].dropna()
        summary["prob_underperform_bh"] = float((cagr_vals < bh_cagr).mean())
    else:
        summary["prob_underperform_bh"] = float("nan")

    return summary


def bootstrap_trade_returns(
    df: pd.DataFrame,
    trix_p: int,
    wma_p: int,
    shift: int,
    n_sims: int = 500,
    fees_pct: float = 0.001,
    slippage_pct: float = 0.002,
    risk_free_rate: float = 0.0,
    seed: int = 42,
) -> pd.DataFrame:
    """Bootstrap resample trade returns and compute distribution of total return."""
    rng = np.random.default_rng(seed)

    sig = baseline_signals(df, trix_p, wma_p, shift)
    bt = run_backtest(df, sig["entry_signal"], sig["exit_signal"], fees_pct, slippage_pct)
    equity = bt["equity"]
    trade_ids = bt["trade_id"]
    unique_trades = trade_ids[trade_ids >= 0].unique()

    if len(unique_trades) < 5:
        return pd.DataFrame()

    trade_rets = []
    for tid in unique_trades:
        mask = trade_ids == tid
        seg = equity[mask]
        pos_first = bt.index.get_loc(seg.index[0])
        if pos_first > 0:
            tr = seg.iloc[-1] / equity.iloc[pos_first - 1] - 1.0
        else:
            tr = seg.iloc[-1] / seg.iloc[0] - 1.0
        trade_rets.append(tr)

    trade_rets = np.array(trade_rets)
    n_trades = len(trade_rets)

    rows = []
    for sim in range(n_sims):
        sample = rng.choice(trade_rets, size=n_trades, replace=True)
        total = np.prod(1 + sample) - 1.0
        rows.append({"sim": sim, "total_return": total, "mean_trade": sample.mean()})

    return pd.DataFrame(rows)
