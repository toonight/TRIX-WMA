"""Data download and caching via yfinance.

All prices are **adjusted** (auto_adjust=True): Open, High, Low, Close are
split- and dividend-adjusted.  This ensures consistency across the pipeline
and avoids spurious gaps at split/dividend dates.
"""
from pathlib import Path
import pandas as pd
import yfinance as yf


def _cache_path(ticker: str, start: str, end: str, cache_dir: Path) -> Path:
    safe = ticker.replace("/", "_").replace("^", "_")
    return cache_dir / f"{safe}_{start}_{end}.parquet"


def load_ohlcv(
    ticker: str,
    start: str,
    end: str,
    cache_dir: str | Path = "data/cache",
) -> pd.DataFrame:
    """Download daily OHLCV via yfinance with local parquet cache.

    Returns DataFrame with columns: Open, High, Low, Close, Volume.
    Index is DatetimeIndex named 'Date'.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cp = _cache_path(ticker, start, end, cache_dir)

    if cp.exists():
        df = pd.read_parquet(cp)
    else:
        print(f"  downloading {ticker} {start}..{end}")
        df = yf.download(
            ticker,
            start=start,
            end=end,
            auto_adjust=True,
            progress=False,
        )
        if df.empty:
            raise ValueError(f"No data returned for {ticker}")
        # Flatten multi-level columns that yfinance sometimes returns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.to_parquet(cp)

    df.index.name = "Date"
    required = ["Open", "High", "Low", "Close", "Volume"]
    for c in required:
        if c not in df.columns:
            raise KeyError(f"Missing column {c} in {ticker} data")
    return df[required].copy()
