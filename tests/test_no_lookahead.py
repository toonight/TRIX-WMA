"""No-lookahead test: signals at t must not use future prices."""
import numpy as np
import pandas as pd
import pytest
from trixwma.strategy import baseline_signals


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


def test_no_lookahead_entry():
    """Perturb future close prices and verify entry signals don't change."""
    df = _make_ohlcv()
    sig_orig = baseline_signals(df, trix_period=14, wma_period=20, shift=5)

    # Perturb the last 50 bars' close prices
    df_perturbed = df.copy()
    df_perturbed.loc[df_perturbed.index[-50:], "Close"] *= 1.5

    sig_perturbed = baseline_signals(df_perturbed, trix_period=14, wma_period=20, shift=5)

    # Signals for bars BEFORE the perturbation should be identical
    cutoff = len(df) - 50 - 30  # Extra margin for indicator warmup contamination
    orig_early = sig_orig["entry_signal"].iloc[:cutoff]
    pert_early = sig_perturbed["entry_signal"].iloc[:cutoff]
    assert (orig_early == pert_early).all(), "Entry signals changed when only future prices were perturbed!"


def test_no_lookahead_exit():
    """Same test for exit signals."""
    df = _make_ohlcv()
    sig_orig = baseline_signals(df, trix_period=14, wma_period=20, shift=5)

    df_pert = df.copy()
    df_pert.loc[df_pert.index[-50:], "Close"] *= 0.7

    sig_pert = baseline_signals(df_pert, trix_period=14, wma_period=20, shift=5)

    cutoff = len(df) - 50 - 30
    assert (sig_orig["exit_signal"].iloc[:cutoff] == sig_pert["exit_signal"].iloc[:cutoff]).all(), \
        "Exit signals leaked future data!"
