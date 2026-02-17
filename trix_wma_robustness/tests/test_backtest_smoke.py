"""Backtest smoke test — runs quickly on a small dataset."""
import numpy as np
import pandas as pd
import pytest
from trixwma.strategy import baseline_signals
from trixwma.backtest import run_backtest, compute_metrics, buy_and_hold_metrics


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


def test_backtest_runs():
    df = _make_ohlcv()
    sig = baseline_signals(df, 14, 20, 5)
    bt = run_backtest(df, sig["entry_signal"], sig["exit_signal"])
    assert len(bt) == len(df)
    assert "equity" in bt.columns
    assert "position" in bt.columns
    assert bt["equity"].iloc[0] == 1.0


def test_metrics_keys():
    df = _make_ohlcv()
    sig = baseline_signals(df, 14, 20, 5)
    bt = run_backtest(df, sig["entry_signal"], sig["exit_signal"])
    m = compute_metrics(bt, df)
    expected_keys = {
        "total_return", "cagr", "ann_vol", "sharpe", "max_dd",
        "calmar", "n_trades", "win_rate", "avg_trade_ret", "exposure",
    }
    assert expected_keys.issubset(m.keys())


def test_buy_and_hold_metrics():
    df = _make_ohlcv()
    m = buy_and_hold_metrics(df)
    assert "cagr" in m
    assert "max_dd" in m
    assert m["exposure"] == 1.0


def test_determinism():
    """Same inputs yield same outputs."""
    df = _make_ohlcv(seed=123)
    sig1 = baseline_signals(df, 12, 18, 4)
    bt1 = run_backtest(df, sig1["entry_signal"], sig1["exit_signal"])
    m1 = compute_metrics(bt1, df)

    sig2 = baseline_signals(df, 12, 18, 4)
    bt2 = run_backtest(df, sig2["entry_signal"], sig2["exit_signal"])
    m2 = compute_metrics(bt2, df)

    assert m1 == m2, "Non-deterministic results!"


def test_equity_never_negative():
    df = _make_ohlcv(n=500)
    sig = baseline_signals(df, 14, 20, 5)
    bt = run_backtest(df, sig["entry_signal"], sig["exit_signal"])
    assert (bt["equity"] > 0).all(), "Equity went negative!"


def test_benchmark_correctness():
    """BH total_return on a known 5-bar series must match manual calc."""
    dates = pd.bdate_range("2020-01-01", periods=5)
    df = pd.DataFrame({
        "Open":  [100.0, 102.0, 104.0, 103.0, 105.0],
        "High":  [101.0, 103.0, 105.0, 104.0, 106.0],
        "Low":   [ 99.0, 101.0, 103.0, 102.0, 104.0],
        "Close": [101.0, 103.0, 104.0, 103.5, 105.5],
        "Volume": [1000] * 5,
    }, index=dates)

    m = buy_and_hold_metrics(df, fees_pct=0.0, slippage_pct=0.0)
    # Entry at first open (100), exit at last open (105)
    expected_total_return = (105.0 / 100.0) - 1.0
    assert abs(m["total_return"] - expected_total_return) < 1e-8, (
        f"BH total_return {m['total_return']} != expected {expected_total_return}"
    )

