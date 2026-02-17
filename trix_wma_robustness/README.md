# 🦅 TRIX-WMA Robustness Framework

> **A production-grade algorithmic trading research pipeline for Trend-Following strategies.**
> *Systematic validation across Time, Parameters, and Assets.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Stable-success?style=for-the-badge)]()
[![Code Style](https://img.shields.io/badge/Code%20Style-Black-black?style=for-the-badge)](https://github.com/psf/black)

---

## 📊 Performance Highlights (2010-2024)

This framework has rigorously validated the **TRIX-WMA** strategy. The verdict? **It is a Cyclical Alpha Generator.**

| Asset Class | Ticker | Strategy CAGR | Buy & Hold | Verdict |
|:-----------:|:------:|:-------------:|:----------:|:-------:|
| **Forex** | `EURUSD` | **+2.0%** | -2.0% | ✅ **Alpha** |
| **Forex** | `USDJPY` | **+4.3%** | +3.5% | ✅ **Beats Market** |
| **Metals** | `Silver` | **+10.6%** | +3.6% | 🚀 **Crushes Market** |
| **Metals** | `Gold` | **+6.5%** | +5.8% | ✅ **Steady Growth** |
| **Tech Growth** | `NVDA` | **+48.3%** | +46.9% | ✅ **Beats B&H** |
| **Tech Growth** | `AMZN` | **+34.3%** | +26.1% | ✅ **Beats B&H** |

> **Verdict:** This strategy is **production-ready** with 3 distinct profiles (Growth, Metals, Forex). It adapts to different asset behaviors to maximize Alpha.

---

## 🧠 The Strategy

**Logic:** A robust **Trend-Following Pullback** system designed to capture the "meat" of the move while filtering out noise.

1.  **Trend Filter:**
    *   **Regime:** Market must be in a "bullish" state (e.g., SMA200 rising).
2.  **Trigger (TRIX):**
    *   Uses the **Trix** indicator (Triple Exponential Smoothed Moving Average) to detect momentum shifts.
3.  **Signal (WMA Cross):**
    *   Enters when Trix crosses its signal line after a pullback.
4.  **Risk Management:**
    *   **ATR Stop Loss:** Adapts to volatility.
    *   **Trailing Stop:** Locks in profits as the trend extends.
5.  **Profiles:**
    *   🚀 **Growth (Tech):** Momentum Entry + Wide Trailing Stop (No TRIX Exit).
    *   🥇 **Cyclical (Metals):** Pullback Entry + TRIX Exit.
    *   💱 **Forex:** Pullback Entry + Tight Risk Management.

---

## 🚀 Key Features

*   **🛡️ Robustness First:** We don't just "backtest". We stress-test.
    *   **3D Grid Search:** `TRIX` × `WMA` × `SHIFT` (Lookback) to find stable parameter "plateaus".
    *   **Walk-Forward Validation:** Rolling out-of-sample testing to prevent overfitting.
    *   **Monte Carlo:** 100+ simulations with randomized slippage, skipped trades, and timing delays.
*   **🌍 Multi-Asset Production Ready:**
    *   One-command optimization for Gold, Silver, Forex, and Equities.
    *   Built-in `yfinance` data loader with caching.
*   **📈 Professional Reporting:**
    *   Generates beautiful Markdown reports with embedded heatmaps and equity curves.
    *   Automated "GO/NO-GO" verdicts based on Sharpe, Alpha, and Drawdown.

---

## 🛠️ Installation

```powershell
# Clone the repository
git clone https://github.com/toonight/TRIX-WMA.git
cd TRIX-WMA/trix_wma_robustness

# Install dependencies
pip install -e ".[dev]"
```

---

## ⚡ Quick Start

### 1. Run the Golden Zone Pipeline (Recommended)
This runs the strategy on our identified "Golden Zone" (stable parameters) for Gold:

```powershell
python -m trixwma run-all --config config/metals_opt.yaml
```

### 2. Run a Full Optimization
To find new parameters for a specific asset (e.g., Forex):

```powershell
python -m trixwma run-all --config config/tech_growth.yaml
```

### 3. Check the Report
Open `reports/latest.md` to see your full analysis, including:
*   Heatmaps of parameter stability.
*   Monte Carlo probability cones.
*   Walk-Forward equity curves.

---

## 📂 Project Structure

```text
trix_wma_robustness/
├── config/             # ⚙️ Strategy configurations (Gold, Forex, Crypto)
├── src/
│   └── trixwma/        # 🧠 Core logic (Grid, Validation, Monte Carlo)
├── reports/            # 📄 Generated reports & figures
├── artifacts/          # 💾 Data tables & intermediate results
├── tests/              # 🧪 Unit tests (Pytest)
└── README.md           # 📖 This file
```

---

## 📜 License

MIT License. Free to use, modify, and profit from.

---

<p align="center">
  <i>Built with ❤️ by the TRIX-WMA Research Team</i>
</p>
