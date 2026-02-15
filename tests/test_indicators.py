"""Indicator sanity tests."""
import numpy as np
import pandas as pd
import pytest
from trixwma.indicators import wma, trix, atr


@pytest.fixture
def close_series():
    np.random.seed(42)
    n = 500
    prices = 100.0 + np.cumsum(np.random.randn(n) * 0.5)
    return pd.Series(prices, name="Close")


def test_wma_shape(close_series):
    result = wma(close_series, 20)
    assert len(result) == len(close_series)
    # First 19 values should be NaN
    assert result.iloc[:19].isna().all()
    assert result.iloc[19:].notna().all()


def test_trix_shape(close_series):
    result = trix(close_series, 14)
    assert len(result) == len(close_series)
    # First value NaN due to pct_change
    assert result.iloc[0] != result.iloc[0]  # NaN check


def test_trix_values_reasonable(close_series):
    result = trix(close_series, 14)
    valid = result.dropna()
    # TRIX values should be small percentages
    assert valid.abs().max() < 10.0, "TRIX values unreasonably large"


def test_wma_no_nan_after_warmup(close_series):
    period = 10
    result = wma(close_series, period)
    assert result.iloc[period:].notna().all()


def test_atr_shape():
    np.random.seed(0)
    n = 200
    high = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5) + 1)
    low = high - 2
    close = (high + low) / 2
    result = atr(high, low, close, 14)
    assert len(result) == n
    assert result.iloc[14:].notna().all()
