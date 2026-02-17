"""Plateau / neighborhood robustness scoring on 3D parameter tensors."""
import numpy as np
from scipy.ndimage import uniform_filter


def _robust_normalize(arr: np.ndarray) -> np.ndarray:
    """Normalize using median / MAD to avoid outlier domination."""
    med = np.nanmedian(arr)
    mad = np.nanmedian(np.abs(arr - med))
    if mad < 1e-12:
        mad = np.nanstd(arr)
    if mad < 1e-12:
        return np.zeros_like(arr)
    return (arr - med) / mad


def neighborhood_stats(
    tensor: np.ndarray,
    kernel: tuple[int, int, int] = (3, 3, 3),
) -> dict[str, np.ndarray]:
    """Compute neighborhood statistics for each cell in a 3D tensor.

    Uses uniform_filter for mean/std.  NaN-safe: replaces NaN with global
    median before filtering, then re-masks original NaN positions.

    Returns dict with keys: mean, median (approx via mean), std.
    """
    mask = np.isnan(tensor)
    fill_val = np.nanmedian(tensor) if not np.all(mask) else 0.0
    filled = np.where(mask, fill_val, tensor)

    nb_mean = uniform_filter(filled, size=kernel, mode="nearest")
    nb_sq_mean = uniform_filter(filled ** 2, size=kernel, mode="nearest")
    nb_var = np.maximum(nb_sq_mean - nb_mean ** 2, 0.0)
    nb_std = np.sqrt(nb_var)
    nb_median = nb_mean  # Approximation; exact median is expensive in 3D

    nb_mean[mask] = np.nan
    nb_median[mask] = np.nan
    nb_std[mask] = np.nan

    return {"mean": nb_mean, "median": nb_median, "std": nb_std}


def beats_bh_fraction(
    cagr_tensor: np.ndarray,
    bh_cagr: float,
    kernel: tuple[int, int, int] = (3, 3, 3),
) -> np.ndarray:
    """Fraction of neighbors (incl self) that beat buy-and-hold CAGR."""
    exceeds = (cagr_tensor > bh_cagr).astype(float)
    mask = np.isnan(cagr_tensor)
    exceeds[mask] = 0.0
    frac = uniform_filter(exceeds, size=kernel, mode="nearest")
    frac[mask] = np.nan
    return frac


def compute_robustness_scores(
    grid_df,
    tensor_builder,
    bh_cagr: float,
    kernel: tuple[int, int, int] = (3, 3, 3),
    weights: dict | None = None,
    min_trades: int = 30,
    bh_frac_threshold: float = 0.7,
) -> tuple:
    """Compute composite robustness score for every cell in the 3D grid.

    The score is based on **alpha_cagr** (strategy CAGR minus BH CAGR)
    rather than raw CAGR, so plateau selection measures outperformance.

    Parameters
    ----------
    grid_df : tidy DataFrame from grid evaluation (must contain 'alpha_cagr').
    tensor_builder : callable(grid_df, metric) -> (tensor, trix_vals, wma_vals, shift_vals).
    bh_cagr : buy-and-hold CAGR for BH-fraction computation.
    kernel, weights, min_trades, bh_frac_threshold : scoring parameters.

    Returns
    -------
    score_tensor, meta dict, axis_vals tuple.
    """
    if weights is None:
        weights = {
            "cagr": 1.0,
            "maxdd": 1.0,
            "sharpe": 0.5,
            "neighbor_var_penalty": 0.5,
            "bh_outperformance_fraction": 1.0,
        }

    # Build tensors — use alpha_cagr if available, else compute from cagr
    if "alpha_cagr" in grid_df.columns:
        alpha_t, tv, wv, sv = tensor_builder(grid_df, "alpha_cagr")
    else:
        cagr_raw, tv, wv, sv = tensor_builder(grid_df, "cagr")
        alpha_t = cagr_raw - bh_cagr

    cagr_t, _, _, _ = tensor_builder(grid_df, "cagr")
    maxdd_t, _, _, _ = tensor_builder(grid_df, "max_dd")
    sharpe_t, _, _, _ = tensor_builder(grid_df, "sharpe")
    trades_t, _, _, _ = tensor_builder(grid_df, "n_trades")

    # Neighborhood stats on alpha_cagr (outperformance)
    alpha_nb = neighborhood_stats(alpha_t, kernel)
    maxdd_nb = neighborhood_stats(maxdd_t, kernel)
    sharpe_nb = neighborhood_stats(sharpe_t, kernel)
    alpha_std = alpha_nb["std"]

    # BH fraction (using raw CAGR vs BH threshold)
    bh_frac = beats_bh_fraction(cagr_t, bh_cagr, kernel)

    # Neighborhood median trades
    trades_nb = neighborhood_stats(trades_t, kernel)

    # Also compute raw cagr_nb for meta
    cagr_nb = neighborhood_stats(cagr_t, kernel)

    # Normalize components
    n_alpha = _robust_normalize(alpha_nb["median"])
    n_maxdd = _robust_normalize(np.abs(maxdd_nb["median"]))
    n_sharpe = _robust_normalize(sharpe_nb["median"])
    n_std = _robust_normalize(alpha_std)

    # Composite score — using alpha_cagr instead of raw cagr
    score = (
        weights["cagr"] * n_alpha
        - weights["maxdd"] * n_maxdd
        + weights["sharpe"] * n_sharpe
        - weights["neighbor_var_penalty"] * n_std
        + weights["bh_outperformance_fraction"] * bh_frac
    )

    # Apply rejection constraints
    reject = np.zeros_like(score, dtype=bool)
    reject |= trades_nb["median"] < min_trades
    reject |= bh_frac < bh_frac_threshold
    reject |= np.isnan(score)
    score[reject] = np.nan

    meta = {
        "cagr_median": cagr_nb["median"],
        "alpha_cagr_median": alpha_nb["median"],
        "maxdd_median": maxdd_nb["median"],
        "sharpe_median": sharpe_nb["median"],
        "cagr_std": alpha_std,
        "bh_frac": bh_frac,
        "trades_median": trades_nb["median"],
    }

    return score, meta, (tv, wv, sv)


def rank_plateaus(
    score_tensor: np.ndarray,
    axis_vals: tuple,
    meta: dict,
    top_n: int = 10,
) -> list[dict]:
    """Return top-N plateau centers ranked by robustness score.

    Each entry includes neighborhood summary stats and the list of
    neighboring parameter cells within the kernel.
    """
    tv, wv, sv = axis_vals
    flat = score_tensor.ravel()
    if not np.any(~np.isnan(flat)):
        return []

    indices = np.argsort(flat)[::-1]  # descending
    results = []
    for idx in indices:
        if np.isnan(flat[idx]):
            continue
        i, j, k = np.unravel_index(idx, score_tensor.shape)

        # Collect neighboring cells
        neighbors = []
        for di in range(-1, 2):
            for dj in range(-1, 2):
                for dk in range(-1, 2):
                    ni, nj, nk = i + di, j + dj, k + dk
                    if 0 <= ni < len(tv) and 0 <= nj < len(wv) and 0 <= nk < len(sv):
                        neighbors.append({
                            "trix_p": tv[ni],
                            "wma_p": wv[nj],
                            "shift": sv[nk],
                        })

        entry = {
            "trix_p": tv[i],
            "wma_p": wv[j],
            "shift": sv[k],
            "score": float(flat[idx]),
            "nb_cagr_median": float(meta["cagr_median"][i, j, k]),
            "nb_alpha_cagr_median": float(meta["alpha_cagr_median"][i, j, k]),
            "nb_maxdd_median": float(meta["maxdd_median"][i, j, k]),
            "nb_sharpe_median": float(meta["sharpe_median"][i, j, k]),
            "nb_cagr_std": float(meta["cagr_std"][i, j, k]),
            "nb_bh_frac": float(meta["bh_frac"][i, j, k]),
            "neighbors": neighbors,
        }
        results.append(entry)
        if len(results) >= top_n:
            break

    return results
