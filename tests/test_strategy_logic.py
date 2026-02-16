
import pandas as pd
import numpy as np
import pytest
from trixwma.strategy import trend_pullback_signals
from trixwma.backtest import run_backtest

# Create sample data
@pytest.fixture
def sample_data():
    dates = pd.date_range("2020-01-01", periods=100)
    df = pd.DataFrame({
        "Open": 100.0,
        "High": 105.0,
        "Low": 95.0,
        "Close": 100.0,
        "Volume": 1000
    }, index=dates)
    # create a trend
    df["Close"] = np.linspace(100, 200, 100)
    df["Open"] = df["Close"]
    df["High"] = df["Close"] + 5
    df["Low"] = df["Close"] - 5
    return df

def test_strategy_logic_runs(sample_data):
    # Just check if it runs without error
    sig = trend_pullback_signals(sample_data, trix_period=10, wma_period=20, shift=5, atr_period=14)
    assert "entry_signal" in sig.columns
    assert "exit_signal" in sig.columns
    assert "atr" in sig.columns

@pytest.mark.parametrize("mode", ["price_above_sma", "sma_slope", "ema_cross", "none"])
def test_regime_modes(sample_data, mode):
    """All regime modes should produce valid signals without crashing."""
    sig = trend_pullback_signals(
        sample_data, trix_period=5, wma_period=10, shift=3,
        regime_mode=mode, sma200_period=50,  # Short SMA for 100-bar data
    )
    assert "entry_signal" in sig.columns
    assert sig["entry_signal"].dtype == bool
    assert sig["exit_signal"].dtype == bool
    assert len(sig) == len(sample_data)

def test_none_mode_more_permissive(sample_data):
    """'none' mode should generate >= as many entries as 'price_above_sma'."""
    sig_strict = trend_pullback_signals(
        sample_data, 5, 10, 3, regime_mode="price_above_sma", sma200_period=50,
    )
    sig_none = trend_pullback_signals(
        sample_data, 5, 10, 3, regime_mode="none", sma200_period=50,
    )
    assert sig_none["entry_signal"].sum() >= sig_strict["entry_signal"].sum()

def test_backtest_risk_management(sample_data):
    # Manually craft a signal
    entry = pd.Series(False, index=sample_data.index)
    exit_ = pd.Series(False, index=sample_data.index)
    
    # Enter on bar 10
    entry.iloc[10] = True 
    # No exit signal
    
    # ATR Mock
    atr_vals = pd.Series(2.0, index=sample_data.index) # Fixed ATR 2.0
    
    # Test 1: No stops, should hold till end
    bt = run_backtest(sample_data, entry, exit_, fees_pct=0, slippage_pct=0, atr_series=atr_vals)
    # Check trade entry
    assert bt["position"].iloc[11] == 1 # Entered at Open of 11 (signal at 10)
    assert bt["position"].iloc[-1] == 1 # Still open
    
    # Test 2: Initial Stop Loss
    # Entry Price = Open[11] = 100 + (11 * (100/99) approx) ... linear space 100->200
    # Let's make price constant to control it easily
    df_flat = sample_data.copy()
    df_flat["Open"] = 100.0
    df_flat["Close"] = 100.0
    df_flat["High"] = 102.0
    df_flat["Low"] = 98.0
    
    # Entry at 11
    # SL ATR = 3.0. ATR = 2.0. Stop Dist = 6.0. Stop Price = 94.0.
    # Low is 98.0. Should NOT trigger.
    bt_safe = run_backtest(df_flat, entry, exit_, atr_series=atr_vals, sl_atr=3.0)
    assert bt_safe["position"].iloc[-1] == 1
    
    # SL ATR = 1.0. ATR = 2.0. Stop Dist = 2.0. Stop Price = 98.0.
    # Low is 98.0. Should trigger (Low <= Stop).
    bt_stop = run_backtest(df_flat, entry, exit_, atr_series=atr_vals, sl_atr=1.0)
    assert bt_stop["position"].iloc[11] == 0 # Should exit SAME BAR if triggered?
    # Logic: 
    # Bar 11: Enter at Open.
    # Initialize Stop.
    # Check stop vs Low[11].
    # Low[11] (98) <= Stop (98)? Yes. Exit.
    # Position[11] should be 0 (flat at EOD).
    assert bt_stop["position"].iloc[11] == 0 
    assert bt_stop["trade_id"].iloc[11] == 1 # It was a trade
    
    # Test 3: Time Stop
    # Time Stop = 5 bars.
    # Enter at 11. 
    # 11 (1), 12 (2), 13 (3), 14 (4), 15 (5).
    # Should exit at close of 15? Or Open of 16?
    # Code: if bars_in_trade >= time_stop: exit at Open[i].
    # Loop i=11. bars=1.
    # ...
    # i=15. bars=5. Check triggered? Yes. Exit at Open[15].
    # Wait, if bars_in_trade >= time_stop at START of loop?
    # Logic:
    # 2. Regular Execution: ... bars_in_trade = 1.
    # Next loop i=12. 
    # 1. Update Equity. check time_stop. bars_in_trade is 1. (from prev bar).
    # so at i=12, bars_in_trade is 1.
    # increment to 2 at end.
    # ...
    # i=15. bars_in_trade is 4. increment to 5 at end.
    # i=16. bars_in_trade is 5. triggered_stop = True. Exit at Open[16].
    # So it holds 11, 12, 13, 14, 15. (5 bars). Exits 16.
    
    bt_time = run_backtest(df_flat, entry, exit_, atr_series=atr_vals, time_stop=5)
    assert bt_time["position"].iloc[15] == 1
    assert bt_time["position"].iloc[16] == 0
