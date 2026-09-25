"""Shared forecasting utilities for M3.2 and M3.7."""

from __future__ import annotations

from typing import Dict

import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


FORECAST_FEATURE_COLUMNS = [
    "weekday",
    "month",
    "is_weekend",
    "lag_1",
    "lag_7",
    "lag_14",
    "rolling_mean_7",
    "rolling_mean_14",
    "rolling_std_7",
]


def build_forecast_feature_row(
    target_date: pd.Timestamp,
    history: Dict[pd.Timestamp, float],
    require_complete_history: bool = True,
) -> pd.DataFrame:
    """Build one recursive forecast feature row from historical demand."""
    lag_dates = {
        "lag_1": target_date - pd.Timedelta(days=1),
        "lag_7": target_date - pd.Timedelta(days=7),
        "lag_14": target_date - pd.Timedelta(days=14),
    }

    required_dates = [
        target_date - pd.Timedelta(days=i)
        for i in range(1, 15)
    ]

    missing_dates = [
        date for date in required_dates if date not in history
    ]

    if require_complete_history and missing_dates:
        missing_text = ", ".join(
            date.strftime("%Y-%m-%d")
            for date in missing_dates[:5]
        )
        raise ValueError(
            "Historical window is incomplete. "
            f"Missing dates: {missing_text}"
        )

    previous_7 = [
        float(history[date])
        for date in required_dates[:7]
        if date in history
    ]

    previous_14 = [
        float(history[date])
        for date in required_dates
        if date in history
    ]

    feature_values = {
        "weekday": int(target_date.weekday()),
        "month": int(target_date.month),
        "is_weekend": int(target_date.weekday() >= 5),
        "lag_1": (
            float(history[lag_dates["lag_1"]])
            if lag_dates["lag_1"] in history
            else 0.0
        ),
        "lag_7": (
            float(history[lag_dates["lag_7"]])
            if lag_dates["lag_7"] in history
            else 0.0
        ),
        "lag_14": (
            float(history[lag_dates["lag_14"]])
            if lag_dates["lag_14"] in history
            else 0.0
        ),
        "rolling_mean_7": (
            float(sum(previous_7) / len(previous_7))
            if previous_7
            else 0.0
        ),
        "rolling_mean_14": (
            float(sum(previous_14) / len(previous_14))
            if previous_14
            else 0.0
        ),
        "rolling_std_7": (
            float(
                pd.Series(
                    previous_7,
                    dtype=float,
                ).std(ddof=1)
            )
            if len(previous_7) > 1
            else 0.0
        ),
    }

    return pd.DataFrame(
        [feature_values],
        columns=FORECAST_FEATURE_COLUMNS,
    )


def build_ridge_model(alpha: float) -> Pipeline:
    """Build the shared Ridge regression pipeline."""
    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=float(alpha))),
        ]
    )
