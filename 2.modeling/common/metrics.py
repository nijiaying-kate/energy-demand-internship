"""Shared evaluation metrics for modeling tasks."""

from __future__ import annotations

from typing import Dict

import pandas as pd


def compute_metrics(
    actual: pd.Series,
    pred: pd.Series,
) -> Dict[str, float]:
    """Compute MAE, RMSE, R2, and WAPE from aligned actual/prediction series."""
    if actual.empty:
        raise ValueError("Prediction data is empty.")

    if len(actual) != len(pred):
        raise ValueError("Actual and prediction series must have the same length.")

    error = actual - pred
    abs_error = error.abs()

    mae = float(abs_error.mean())
    rmse = float((error ** 2).mean() ** 0.5)

    ss_res = float((error ** 2).sum())
    ss_tot = float(((actual - actual.mean()) ** 2).sum())

    if ss_tot == 0:
        raise ValueError(
            "R² is undefined because the actual target has zero variance."
        )

    r2 = float(1.0 - (ss_res / ss_tot))

    actual_abs_sum = float(actual.abs().sum())
    if actual_abs_sum == 0:
        raise ValueError(
            "WAPE is undefined because the actual target sum is zero."
        )

    wape = float((abs_error.sum() / actual_abs_sum) * 100.0)

    return {
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2,
        "WAPE": wape,
    }
