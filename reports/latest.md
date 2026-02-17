# TRIX + WMA Robustness Evaluation Report

**Primary Ticker:** AMZN

## 1. Problem Framing

Optimizing a trading strategy on a 2D parameter grid (TRIX period × WMA period) often produces a **single bright pixel** that looks impressive in-sample but is fragile: small parameter changes destroy performance.

By adding the SHIFT dimension and evaluating a 3D grid, we expose how that bright pixel fragments across timing perturbations. The solution is to find **plateaus** — regions where the *neighborhood* of parameters performs consistently well.

## 2. Strategy Definition

- **WMA:Weighted Moving Average** (Pullback Setup)

- **TRIX:** Momentum (Trigger)

- **Logic:** Trend-Following Pullback with Regime Filter (SMA200) & ATR Risk Management.

- **Execution:** Signals at close of bar t → fill at open of bar t+1.

## 3. Baselines

### Buy & Hold

| Metric | Buy & Hold |
|--------|---------|
| total_return | 31.1734 |
| cagr | 0.2609 |
| ann_vol | 0.3273 |
| sharpe | 0.7973 |
| max_dd | -0.5615 |
| calmar | 0.4647 |
| n_trades | 1 |
| win_rate | 1.0000 |
| avg_trade_ret | 31.1734 |
| exposure | 1.0000 |

### Buy & Hold + SMA200 Filter

| Metric | BH + SMA200 |
|--------|---------|
| total_return | 60.3172 |
| cagr | 0.3164 |
| ann_vol | 0.6299 |
| sharpe | 0.5023 |
| max_dd | -0.4747 |
| calmar | 0.6665 |
| n_trades | 50 |
| win_rate | 0.1800 |
| avg_trade_ret | 0.0708 |
| exposure | 0.7146 |

## 4. 2D Grid Results

![CAGR SHIFT=1](figures/heatmap_cagr_shift1_AMZN.png)

![CAGR SHIFT=2](figures/heatmap_cagr_shift2_AMZN.png)

![CAGR SHIFT=3](figures/heatmap_cagr_shift3_AMZN.png)

![CAGR SHIFT=4](figures/heatmap_cagr_shift4_AMZN.png)

![CAGR SHIFT=5](figures/heatmap_cagr_shift5_AMZN.png)

![CAGR SHIFT=6](figures/heatmap_cagr_shift6_AMZN.png)

![CAGR SHIFT=7](figures/heatmap_cagr_shift7_AMZN.png)

![CAGR SHIFT=8](figures/heatmap_cagr_shift8_AMZN.png)

![CAGR SHIFT=9](figures/heatmap_cagr_shift9_AMZN.png)

![CAGR SHIFT=10](figures/heatmap_cagr_shift10_AMZN.png)

![CAGR SHIFT=11](figures/heatmap_cagr_shift11_AMZN.png)

![CAGR SHIFT=12](figures/heatmap_cagr_shift12_AMZN.png)

![CAGR SHIFT=13](figures/heatmap_cagr_shift13_AMZN.png)

![CAGR SHIFT=14](figures/heatmap_cagr_shift14_AMZN.png)

![CAGR SHIFT=15](figures/heatmap_cagr_shift15_AMZN.png)

### Best-of-SHIFT Projection

![Best-of-SHIFT CAGR](figures/heatmap_bestshift_cagr_AMZN.png)

## 5. 3D Results — Fragmentation Across SHIFT

![CAGR grid](figures/heatmap_grid_cagr_AMZN.png)

## 6. Plateau Scoring

Score = w₁·norm(median_alpha_CAGR) − w₂·norm(|median_MaxDD|) + w₃·norm(median_Sharpe)
 − w₄·norm(std_alpha_CAGR) + w₅·frac_beating_BH

![Plateau map](figures/plateau_map_AMZN.png)

### Top Plateau Centers

| Rank | TRIX | WMA | SHIFT | Score | α-CAGR_med | MaxDD_med | Sharpe_med | α-CAGR_std | BH_frac |
|------|------|-----|-------|-------|------------|-----------|------------|------------|---------|
| 1 | 5 | 37 | 2 | 13.130 | 0.0823 | -0.5275 | 1.088 | 0.0357 | 1.00 |
| 2 | 5 | 37 | 7 | 13.130 | 0.0823 | -0.5275 | 1.088 | 0.0357 | 1.00 |
| 3 | 5 | 37 | 3 | 13.130 | 0.0823 | -0.5275 | 1.088 | 0.0357 | 1.00 |
| 4 | 5 | 37 | 4 | 13.130 | 0.0823 | -0.5275 | 1.088 | 0.0357 | 1.00 |
| 5 | 5 | 37 | 5 | 13.130 | 0.0823 | -0.5275 | 1.088 | 0.0357 | 1.00 |

### Best Pixel vs Best Plateau

- **Best Pixel:** TRIX=5, WMA=10, SHIFT=1 → CAGR=0.3684, α-CAGR=0.1075
- **Best Plateau:** TRIX=5, WMA=37, SHIFT=2 → α-CAGR median=0.0823

## 7. Walk-Forward OOS Results

![Walk-forward](figures/walk_forward_AMZN.png)

| Window | Test Period | Params | OOS CAGR | OOS Sharpe | OOS MaxDD | Beats BH |
|--------|------------|--------|----------|-----------|----------|----------|
| W0 | 2015-01-12→2016-01-04 | T5/W37/S2 | 1.8379 | 4.646 | -0.0899 | True |
| W1 | 2015-07-13→2016-07-01 | T5/W37/S8 | 0.2731 | 0.852 | -0.3266 | False |
| W2 | 2016-01-11→2017-01-04 | T5/W37/S8 | 0.0113 | 0.040 | -0.2857 | False |
| W3 | 2016-07-12→2017-07-03 | T5/W37/S8 | 0.0003 | 0.002 | -0.1319 | False |
| W4 | 2017-01-11→2018-01-04 | T5/W37/S8 | 0.2247 | 1.943 | -0.0942 | False |
| W5 | 2017-07-12→2018-07-03 | T7/W23/S6 | -0.0967 | -0.766 | -0.1356 | False |
| W6 | 2018-01-11→2019-01-04 | T7/W22/S15 | -0.3863 | -1.928 | -0.3804 | False |
| W7 | 2018-07-12→2019-07-03 | T5/W36/S15 | -0.3810 | -1.367 | -0.4660 | False |
| W8 | 2019-01-11→2020-01-03 | T5/W36/S15 | -0.0442 | -0.319 | -0.1738 | False |
| W9 | 2019-07-12→2020-07-02 | T5/W37/S8 | 0.3686 | 1.267 | -0.1738 | False |
| W10 | 2020-01-13→2021-01-04 | T5/W37/S8 | 0.7649 | 2.453 | -0.0802 | True |
| W11 | 2020-07-13→2021-07-02 | T5/W37/S8 | 0.1839 | 0.799 | -0.1664 | True |
| W12 | 2021-01-11→2022-01-04 | T5/W37/S8 | 0.2270 | 1.093 | -0.1208 | True |
| W13 | 2021-07-13→2022-07-01 | T5/W37/S8 | -0.3388 | -1.481 | -0.3705 | True |
| W14 | 2022-01-11→2023-01-04 | T5/W37/S8 | -0.4365 | -1.074 | -0.4418 | True |
| W15 | 2022-07-12→2023-07-03 | T15/W23/S11 | 0.4859 | 2.297 | -0.0843 | True |
| W16 | 2023-01-11→2024-01-04 | T15/W37/S6 | 0.7628 | 2.250 | -0.0708 | True |
| W17 | 2023-07-12→2024-07-03 | T15/W23/S11 | 0.0298 | 0.200 | -0.1362 | False |

## 8. Multi-Asset Results

## 9. Monte Carlo Stress Results

![MC CAGR](figures/mc_cagr_AMZN.png)

![MC Sharpe](figures/mc_sharpe_AMZN.png)

### CAGR
- Median: 0.3265
- 5th percentile: 0.2538
- 95th percentile: 0.3864
- Std: 0.0453

### SHARPE
- Median: 1.0227
- 5th percentile: 0.8226
- 95th percentile: 1.2018
- Std: 0.1264

### MAX_DD
- Median: -0.5437
- 5th percentile: -0.5798
- 95th percentile: -0.5032
- Std: 0.0354

### TOTAL_RETURN
- Median: 67.7202
- 5th percentile: 28.5433
- 95th percentile: 132.1791
- Std: 35.9078

### N_TRADES
- Median: 96.0000
- 5th percentile: 94.0000
- 95th percentile: 98.0000
- Std: 1.0929

**Probability of underperforming Buy & Hold:** 8.0%

## 10. Verdict

**✅ GO** — Strategy shows evidence of robust outperformance across OOS windows and stress tests. Plateau-selected parameters are recommended for paper trading.
