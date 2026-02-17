"""Production-grade tests: grid schema, plateau determinism, MC gap penalty."""
import numpy as np
import pandas as pd
import pytest
from trixwma.grid import evaluate_grid, grid_to_tensor
from trixwma.robustness import compute_robustness_scores, rank_plateaus
from trixwma.backtest import buy_and_hold_metrics
from trixwma.monte_carlo import monte_carlo_stress


def _make_ohlcv(n=300, seed=42):
    np.random.seed(seed)
    close = 100.0 + np.cumsum(np.random.randn(n) * 0.5)
    open_ = close + np.random.randn(n) * 0.1
    high = np.maximum(open_, close) + np.abs(np.random.randn(n) * 0.3)
    low = np.minimum(open_, close) - np.abs(np.random.randn(n) * 0.3)
    vol = np.random.randint(1000, 10000, n)
    dates = pd.bdate_range("2020-01-01", periods=n)
    return pd.DataFrame({
        "Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol,
    }, index=dates)


# -----------------------------------------------------------------------
# Grid schema test
# -----------------------------------------------------------------------

def test_grid_schema():
    """Grid output must contain all required columns."""
    df = _make_ohlcv(n=200, seed=99)
    grid_df = evaluate_grid(
        df, (12, 13), (18, 19), (3, 4),
        ticker="TEST", start_date="2020-01-01", end_date="2020-12-31",
    )
    required = {
        "ticker", "start", "end",
        "trix_p", "wma_p", "shift",
        "total_return", "cagr", "ann_vol", "sharpe", "max_dd", "calmar",
        "n_trades", "win_rate", "avg_trade_ret", "exposure",
        "bh_cagr", "bh_sharpe", "bh_max_dd", "bh_total_return",
        "alpha_cagr", "alpha_total_return", "beats_bh",
    }
    assert required.issubset(set(grid_df.columns)), (
        f"Missing columns: {required - set(grid_df.columns)}"
    )
    assert len(grid_df) == 2 * 2 * 2  # 2 TRIX x 2 WMA x 2 SHIFT


# -----------------------------------------------------------------------
# Plateau determinism
# -----------------------------------------------------------------------

def test_plateau_determinism():
    """Same inputs → identical plateau ranking."""
    df = _make_ohlcv(n=250, seed=77)
    grid_df = evaluate_grid(df, (12, 14), (18, 20), (3, 5))
    bh = buy_and_hold_metrics(df)

    score1, meta1, ax1 = compute_robustness_scores(
        grid_df, grid_to_tensor, bh["cagr"],
        kernel=(3, 3, 3), min_trades=0, bh_frac_threshold=0.0,
    )
    r1 = rank_plateaus(score1, ax1, meta1, top_n=5)

    score2, meta2, ax2 = compute_robustness_scores(
        grid_df, grid_to_tensor, bh["cagr"],
        kernel=(3, 3, 3), min_trades=0, bh_frac_threshold=0.0,
    )
    r2 = rank_plateaus(score2, ax2, meta2, top_n=5)

    assert len(r1) == len(r2)
    for p1, p2 in zip(r1, r2):
        assert p1["trix_p"] == p2["trix_p"]
        assert p1["wma_p"] == p2["wma_p"]
        assert p1["shift"] == p2["shift"]
        assert abs(p1["score"] - p2["score"]) < 1e-12


# -----------------------------------------------------------------------
# MC gap penalty
# -----------------------------------------------------------------------

def test_mc_gap_penalty_no_crash():
    """MC with gap penalty enabled does not crash."""
    df = _make_ohlcv(n=200, seed=55)
    mc_df = monte_carlo_stress(
        df, trix_p=14, wma_p=20, shift=4,
        n_sims=5,
        gap_penalty_atr_threshold=1.0,
        gap_extra_slip_pct=0.01,
        seed=42,
    )
    assert len(mc_df) == 5
    assert "cagr" in mc_df.columns


def test_mc_gap_penalty_reproducible():
    """MC with gap penalty is deterministic given same seed."""
    df = _make_ohlcv(n=200, seed=55)
    kwargs = dict(
        trix_p=14, wma_p=20, shift=4,
        n_sims=10,
        gap_penalty_atr_threshold=1.5,
        gap_extra_slip_pct=0.005,
        seed=123,
    )
    mc1 = monte_carlo_stress(df, **kwargs)
    mc2 = monte_carlo_stress(df, **kwargs)
    pd.testing.assert_frame_equal(mc1, mc2)
