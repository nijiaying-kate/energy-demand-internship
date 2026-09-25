from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.forecast_utils import (
    build_forecast_feature_row,
    build_ridge_model,
)

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


MIN_HISTORY_DAYS = 15

FEATURE_COLUMNS = [
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

TARGET_COLUMN = "daily_qty"

RIDGE_ALPHA = 1.0
DEFAULT_HORIZON = 7
DEFAULT_SEED = 42


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a leakage-safe demand forecast "
            "using Ridge Regression."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to the M2 feature dataset CSV.",
    )

    parser.add_argument(
        "--forecast-origin",
        type=str,
        required=True,
        help=(
            "Forecast origin date in YYYY-MM-DD format."
        ),
    )

    parser.add_argument(
        "--horizon",
        type=int,
        default=DEFAULT_HORIZON,
        help=(
            "Number of future days to forecast. "
            f"Default: {DEFAULT_HORIZON}."
        ),
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=(
            "Seed value recorded for reproducibility. "
            "Ridge Regression itself is deterministic."
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional local CSV output path.",
    )

    parser.add_argument(
        "--location-id",
        dest="location_id",
        type=str,
        default=None,
        help=(
            "Optional location identifier "
            "for the output contract."
        ),
    )

    parser.add_argument(
        "--storage-unit-id",
        dest="storage_unit_id",
        type=str,
        default=None,
        help=(
            "Optional storage-unit identifier "
            "for the output contract."
        ),
    )

    return parser.parse_args()


def load_data(
    input_path: Path,
) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}"
        )

    df = pd.read_csv(
        input_path
    )

    required_columns = {
        "date",
        TARGET_COLUMN,
        *FEATURE_COLUMNS,
    }

    missing_columns = sorted(
        required_columns - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Input data is missing required columns: "
            + ", ".join(missing_columns)
        )

    df["date"] = pd.to_datetime(
        df["date"],
        errors="raise",
    )

    df[TARGET_COLUMN] = pd.to_numeric(
        df[TARGET_COLUMN],
        errors="raise",
    )

    df["weekday"] = (
        df["date"]
        .dt.weekday
        .astype(int)
    )

    df["month"] = (
        df["date"]
        .dt.month
        .astype(int)
    )

    df["is_weekend"] = (
        df["date"].dt.weekday >= 5
    ).astype(int)

    if df["date"].duplicated().any():
        duplicate_dates = (
            df.loc[
                df["date"].duplicated(),
                "date",
            ]
            .dt.strftime("%Y-%m-%d")
            .tolist()
        )

        raise ValueError(
            "Duplicate dates found in input data: "
            f"{duplicate_dates[:5]}"
        )

    df = (
        df.sort_values("date")
        .reset_index(drop=True)
    )

    return df


def validate_forecast_origin(
    df: pd.DataFrame,
    forecast_origin: pd.Timestamp,
) -> None:
    if forecast_origin not in set(
        df["date"]
    ):
        raise ValueError(
            "Forecast origin "
            f"{forecast_origin.date()} "
            "does not exist in the historical dataset."
        )

    historical_df = df[
        df["date"] <= forecast_origin
    ]

    if len(historical_df) < MIN_HISTORY_DAYS:
        raise ValueError(
            "At least MIN_HISTORY_DAYS days of historical "
            "demand are required before "
            "the forecast origin."
        )


def validate_horizon(
    horizon_days: int,
) -> None:
    if horizon_days <= 0:
        raise ValueError(
            "Horizon must be a positive integer."
        )


def validate_seed(
    seed: int,
) -> None:
    if not isinstance(seed, int):
        raise ValueError(
            "Seed must be an integer."
        )


def build_training_data(
    df: pd.DataFrame,
    forecast_origin: pd.Timestamp,
) -> tuple[
    pd.DataFrame,
    pd.Series,
    dict[pd.Timestamp, float],
]:
    historical_df = df[
        df["date"] <= forecast_origin
    ].copy()

    model_ready_mask = (
        historical_df[
            FEATURE_COLUMNS
        ]
        .notna()
        .all(axis=1)
    )

    training_df = historical_df.loc[
        model_ready_mask
    ].copy()

    if training_df.empty:
        raise ValueError(
            "No model-ready training rows "
            "are available before the "
            "forecast origin."
        )

    if training_df[
        FEATURE_COLUMNS
    ].isna().any().any():
        raise ValueError(
            "NaN detected in model "
            "training features."
        )

    if training_df[
        TARGET_COLUMN
    ].isna().any():
        raise ValueError(
            "NaN detected in training target."
        )

    X_train = training_df[
        FEATURE_COLUMNS
    ].astype(float)

    y_train = training_df[
        TARGET_COLUMN
    ].astype(float)

    history = {
        pd.Timestamp(row["date"]): float(
            row[TARGET_COLUMN]
        )
        for _, row in historical_df.iterrows()
    }

    return (
        X_train,
        y_train,
        history,
    )


def build_model() -> Pipeline:
    return build_ridge_model(alpha=RIDGE_ALPHA)


def recursive_forecast(
    model: Pipeline,
    forecast_origin: pd.Timestamp,
    history: dict[pd.Timestamp, float],
    horizon_days: int,
    location_id: str | None = None,
    storage_unit_id: str | None = None,
) -> pd.DataFrame:
    results = []

    recursive_history = history.copy()

    for horizon in range(
        1,
        horizon_days + 1,
    ):
        target_date = (
            forecast_origin
            + pd.Timedelta(days=horizon)
        )

        feature_row = build_forecast_feature_row(
            target_date=target_date,
            history=recursive_history,
            require_complete_history=True,
        )

        prediction = float(
            model.predict(feature_row)[0]
        )

        if not np.isfinite(prediction):
            raise ValueError(
                "Non-finite prediction generated "
                f"for {target_date.date()}."
            )

        results.append(
            {
                "forecast_origin": (
                    forecast_origin.strftime(
                        "%Y-%m-%d"
                    )
                ),
                "target_date": (
                    target_date.strftime(
                        "%Y-%m-%d"
                    )
                ),
                "horizon": horizon,
                "location_id": location_id,
                "storage_unit_id": storage_unit_id,
                "model_name": (
                    "Ridge Regression"
                ),
                "actual_qty": np.nan,
                "predicted_qty": prediction,
            }
        )

        recursive_history[
            target_date
        ] = prediction

    return pd.DataFrame(
        results
    )


def print_forecast(
    forecast_df: pd.DataFrame,
    forecast_origin: pd.Timestamp,
    horizon_days: int,
    seed: int,
    train_time_seconds: float,
    inference_time_seconds: float,
) -> None:
    print()
    print("=" * 62)
    print(
        f"{horizon_days}-Day Demand Forecast"
    )
    print("=" * 62)
    print(
        "Forecast Origin : "
        f"{forecast_origin.strftime('%Y-%m-%d')}"
    )
    print(
        "Model           : Ridge Regression"
    )
    print(
        f"Alpha           : {RIDGE_ALPHA}"
    )
    print(
        f"Seed            : {seed}"
    )
    print()
    print(
        f"{'Horizon':<10}"
        f"{'Target Date':<15}"
        f"{'Predicted Demand':>18}"
    )
    print("-" * 43)

    for _, row in forecast_df.iterrows():
        print(
            f"{int(row['horizon']):<10}"
            f"{row['target_date']:<15}"
            f"{row['predicted_qty']:>18.2f}"
        )

    print()
    print(
        f"Train Time      : "
        f"{train_time_seconds:.6f} seconds"
    )
    print(
        f"Inference Time  : "
        f"{inference_time_seconds:.6f} seconds"
    )
    print("=" * 62)


def save_output(
    forecast_df: pd.DataFrame,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_columns = [
        "forecast_origin",
        "target_date",
        "horizon",
        "location_id",
        "storage_unit_id",
        "model_name",
        "actual_qty",
        "predicted_qty",
    ]

    forecast_df[
        output_columns
    ].to_csv(
        output_path,
        index=False,
    )

    print()
    print(
        "Local forecast CSV saved to: "
        f"{output_path}"
    )


def main() -> int:
    args = parse_args()

    validate_horizon(
        args.horizon
    )

    validate_seed(
        args.seed
    )

    forecast_origin = pd.to_datetime(
        args.forecast_origin,
        format="%Y-%m-%d",
        errors="raise",
    )

    df = load_data(
        args.input
    )

    validate_forecast_origin(
        df=df,
        forecast_origin=forecast_origin,
    )

    (
        X_train,
        y_train,
        history,
    ) = build_training_data(
        df=df,
        forecast_origin=forecast_origin,
    )

    model = build_model()

    train_start = time.perf_counter()

    model.fit(
        X_train,
        y_train,
    )

    train_time_seconds = (
        time.perf_counter()
        - train_start
    )

    inference_start = time.perf_counter()

    forecast_df = recursive_forecast(
        model=model,
        forecast_origin=forecast_origin,
        history=history,
        horizon_days=args.horizon,
        location_id=args.location_id,
        storage_unit_id=args.storage_unit_id,
    )

    inference_time_seconds = (
        time.perf_counter()
        - inference_start
    )

    if len(forecast_df) != args.horizon:
        raise RuntimeError(
            f"Expected {args.horizon} forecasts, "
            f"but generated {len(forecast_df)}."
        )

    print_forecast(
        forecast_df=forecast_df,
        forecast_origin=forecast_origin,
        horizon_days=args.horizon,
        seed=args.seed,
        train_time_seconds=train_time_seconds,
        inference_time_seconds=inference_time_seconds,
    )

    if args.output is not None:
        save_output(
            forecast_df=forecast_df,
            output_path=args.output,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
