"""Shared helpers for the training scripts."""
from __future__ import annotations

import numpy as np
import pandas as pd


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def widest_window_with_columns(df: pd.DataFrame, month_col: str, required_cols: list[str]) -> pd.DataFrame:
    """Return the rows (sorted by month_col) where every column in required_cols is
    non-null, i.e. the real overlap window across all requested data sources."""
    sub = df.dropna(subset=required_cols).sort_values(month_col)
    return sub
