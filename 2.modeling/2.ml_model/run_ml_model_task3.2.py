#!/usr/bin/env python3
"""Task 3.2: baseline-validated ML comparison with Ridge, RandomForest, and GradientBoosting."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.metrics import compute_metrics
from common.forecast_utils import (
    build_forecast_feature_row,
    build_ridge_model,
)

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

MODEL_READY_START = pd.Timestamp("2023-01-15")
MODEL_READY_END = pd.Timestamp("2024-12-30")

MODEL_CANDIDATES: Dict[str, Dict[str, Dict[str, Any]]] = {
    "Ridge": {
        "alpha_1.0": {"alpha": 1.0},
    },
    "RandomForest": {
        "Config C": {
            "n_estimators": 300,
            "max_depth": None,
            "min_samples_leaf": 2,
            "max_features": 0.8,
        },
    },
    "GradientBoosting": {
        "GB_150_0.05_3": {
            "n_estimators": 150,
            "learning_rate": 0.05,
            "max_depth": 3,
            "min_samples_leaf": 3,
        },
    },
}

WEEKDAY_MAP = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[2]
    default_split_dir = project_root / "1.data_engineering" / "4.data_split"
    default_feature_csv = (
        project_root
        / "1.data_engineering"
        / "3.data_feature"
        / "v5_location_demo_storage_unit_demo_features.csv"
    )

    parser = argparse.ArgumentParser(
        description=(
            "Train and validate the Ridge / RandomForest / "
            "GradientBoosting forecasting models."
        )
    )
    parser.add_argument("--split-dir", type=Path, default=default_split_dir)
    parser.add_argument("--feature-csv", type=Path, default=default_feature_csv)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "local_outputs",
    )
    return parser.parse_args()


def load_feature_data(feature_csv: Path) -> pd.DataFrame:
    if not feature_csv.exists():
        raise FileNotFoundError(f"Feature CSV not found: {feature_csv}")

    df = pd.read_csv(feature_csv)

    required = [
        "date",
        "daily_qty",
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
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required feature columns: {missing}")

    df["date"] = pd.to_datetime(df["date"])
    df["weekday"] = df["date"].dt.day_name().map(WEEKDAY_MAP)
    df["month"] = df["date"].dt.month.astype(int)
    df["is_weekend"] = (
        df["date"].dt.day_name().isin(["Saturday", "Sunday"]).astype(int)
    )

    df = df[
        (df["date"] >= MODEL_READY_START)
        & (df["date"] <= MODEL_READY_END)
    ].copy()

    return df.sort_values("date").reset_index(drop=True)


def load_schedule(split_dir: Path, schedule_name: str) -> pd.DataFrame:
    path = split_dir / schedule_name
    if not path.exists():
        raise FileNotFoundError(f"Schedule CSV not found: {path}")

    df = pd.read_csv(path)
    df["forecast_origin"] = pd.to_datetime(df["forecast_origin"])
    df["target_date"] = pd.to_datetime(df["target_date"])

    return df.sort_values(
        ["forecast_origin", "target_date"]
    ).reset_index(drop=True)


def make_feature_row(
    target_date: pd.Timestamp,
    history: Dict[pd.Timestamp, float],
) -> Dict[str, float]:
    """Build M3.2 recursive features using shared forecasting logic."""
    row = build_forecast_feature_row(
        target_date=target_date,
        history=history,
        require_complete_history=False,
    )
    return row.iloc[0].to_dict()


def build_model_data_for_origin(
    feature_df: pd.DataFrame,
    origin: pd.Timestamp,
) -> pd.DataFrame:
    window = feature_df[feature_df["date"] <= origin].copy()
    if window.empty:
        raise ValueError(
            f"No training data available for forecast origin {origin.date()}"
        )
    return window


def build_model(
    model_family: str,
    candidate_config: Dict[str, Any],
) -> Any:
    if model_family == "Ridge":
        return build_ridge_model(
            alpha=float(candidate_config["alpha"])
        )

    if model_family == "RandomForest":
        return RandomForestRegressor(
            random_state=42,
            n_jobs=-1,
            **candidate_config,
        )

    if model_family == "GradientBoosting":
        return GradientBoostingRegressor(
            random_state=42,
            **candidate_config,
        )

    raise ValueError(f"Unsupported model family: {model_family}")


def generate_predictions(
    model_family: str,
    model_config: Dict[str, Any],
    candidate_name: str,
    feature_df: pd.DataFrame,
    schedule: pd.DataFrame,
    skip_seen_targets: bool = False,
) -> Tuple[pd.DataFrame, float, float]:
    outputs: List[Dict[str, Any]] = []
    train_seconds = 0.0
    inference_seconds = 0.0

    for origin in sorted(schedule["forecast_origin"].unique()):
        training_window = build_model_data_for_origin(
            feature_df,
            origin,
        )

        model = build_model(model_family, model_config)

        X_train = training_window[FEATURE_COLUMNS].copy()
        y_train = training_window["daily_qty"].astype(float)

        train_start = time.perf_counter()
        model.fit(X_train, y_train)
        train_seconds += time.perf_counter() - train_start

        origin_tasks = schedule[
            schedule["forecast_origin"] == origin
        ].sort_values("target_date")

        history = {
            pd.Timestamp(row["date"]): float(row["daily_qty"])
            for _, row in training_window.iterrows()
        }

        for _, task in origin_tasks.iterrows():
            target_date = pd.Timestamp(task["target_date"])

            actual_value = float(
                feature_df.loc[
                    feature_df["date"] == target_date,
                    "daily_qty",
                ].iloc[0]
            )

            if skip_seen_targets and target_date in history:
                continue

            feature_row = make_feature_row(
                target_date,
                history,
            )
            row_df = pd.DataFrame(
                [feature_row],
                columns=FEATURE_COLUMNS,
            )

            inference_start = time.perf_counter()
            pred_value = float(model.predict(row_df)[0])
            inference_seconds += (
                time.perf_counter() - inference_start
            )

            outputs.append(
                {
                    "model_family": model_family,
                    "candidate": candidate_name,
                    "evaluation_partition": task[
                        "evaluation_partition"
                    ],
                    "forecast_origin": origin,
                    "target_date": target_date,
                    "horizon": int(task["horizon"]),
                    "actual": actual_value,
                    "prediction": pred_value,
                    "absolute_error": abs(
                        actual_value - pred_value
                    ),
                }
            )

            history[target_date] = pred_value

    prediction_df = pd.DataFrame(outputs)
    prediction_df = prediction_df.sort_values(
        ["forecast_origin", "target_date"]
    ).reset_index(drop=True)

    return (
        prediction_df,
        train_seconds,
        inference_seconds,
    )


def evaluate_candidate(
    model_family: str,
    candidate_name: str,
    candidate_config: Dict[str, Any],
    feature_df: pd.DataFrame,
    schedule: pd.DataFrame,
) -> Tuple[pd.DataFrame, Dict[str, float], float, float]:
    prediction_df, train_seconds, inference_seconds = generate_predictions(
        model_family=model_family,
        model_config=candidate_config,
        candidate_name=candidate_name,
        feature_df=feature_df,
        schedule=schedule,
        skip_seen_targets=True,
    )

    metrics = compute_metrics(
        prediction_df["actual"],
        prediction_df["prediction"],
    )

    return (
        prediction_df,
        metrics,
        train_seconds,
        inference_seconds,
    )


def generate_final_predictions(
    model_family: str,
    model_config: Dict[str, Any],
    feature_df: pd.DataFrame,
    schedule: pd.DataFrame,
) -> Tuple[pd.DataFrame, float, float]:
    return generate_predictions(
        model_family=model_family,
        model_config=model_config,
        candidate_name="final_selection",
        feature_df=feature_df,
        schedule=schedule,
        skip_seen_targets=False,
    )


def select_best_result(
    results: List[
        Tuple[
            str,
            str,
            Dict[str, Any],
            pd.DataFrame,
            Dict[str, float],
            float,
            float,
        ]
    ],
) -> Tuple[
    str,
    str,
    Dict[str, Any],
    pd.DataFrame,
    Dict[str, float],
    float,
    float,
]:
    return min(
        results,
        key=lambda item: (
            item[4]["WAPE"],
            item[4]["MAE"],
        ),
    )


def write_validation_report(
    output_dir: Path,
    selected_model_family: str,
    selected_candidate_name: str,
    selected_config: Dict[str, Any],
    selection_metrics: Dict[str, float],
    validation_pred: pd.DataFrame,
    test_pred: pd.DataFrame,
    validation_train_seconds: float,
    validation_inference_seconds: float,
    test_train_seconds: float,
    test_inference_seconds: float,
) -> None:
    report = f"""# Milestone 3 - ML Validation

## 1. 目的

Ridge, RandomForest, GradientBoosting を同一条件で比較し、
Validation Set で candidate selection を行い、Test Set で最終評価を実施する。

## 2. Model families and features

- models: Ridge, RandomForestRegressor, GradientBoostingRegressor
- features: weekday, month, is_weekend, lag_1, lag_7, lag_14, rolling_mean_7, rolling_mean_14, rolling_std_7
- target: daily_qty
- selection rule: lower Validation WAPE first, then lower Validation MAE

## 3. Selected configuration

- model family: {selected_model_family}
- candidate: {selected_candidate_name}
- config: {selected_config}

## 4. Validation results

- validation prediction count: {len(validation_pred)}
- validation WAPE: {selection_metrics['WAPE']:.4f}
- validation MAE: {selection_metrics['MAE']:.4f}
- validation RMSE: {selection_metrics['RMSE']:.4f}
- validation R²: {selection_metrics['R2']:.4f}
- validation train time (s): {validation_train_seconds:.6f}
- validation inference time (s): {validation_inference_seconds:.6f}

## 5. Final Test summary

- test prediction count: {len(test_pred)}
- test train time (s): {test_train_seconds:.6f}
- test inference time (s): {test_inference_seconds:.6f}

## 6. Leakage control

- training_window uses date <= forecast_origin only
- recursive feature generation is used for horizon 1～7
- future actual is not used directly
- selected configuration is frozen before Test execution
"""

    (
        output_dir / "M3_ml_model_validation_task3.2.md"
    ).write_text(report, encoding="utf-8")


def main() -> int:
    args = parse_args()

    feature_df = load_feature_data(args.feature_csv)

    validation_schedule = load_schedule(
        args.split_dir,
        "validation_forecast_schedule.csv",
    )
    test_schedule = load_schedule(
        args.split_dir,
        "test_forecast_schedule.csv",
    )

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_results: List[
        Tuple[
            str,
            str,
            Dict[str, Any],
            pd.DataFrame,
            Dict[str, float],
            float,
            float,
        ]
    ] = []

    for model_family, candidate_map in MODEL_CANDIDATES.items():
        for candidate_name, config in candidate_map.items():
            result = evaluate_candidate(
                model_family,
                candidate_name,
                config,
                feature_df,
                validation_schedule,
            )
            all_results.append(
                (
                    model_family,
                    candidate_name,
                    config,
                    result[0],
                    result[1],
                    result[2],
                    result[3],
                )
            )

    selection_results = pd.DataFrame(
        [
            {
                "model_family": model_family,
                "candidate": candidate_name,
                **config,
                "MAE": metrics["MAE"],
                "RMSE": metrics["RMSE"],
                "R2": metrics["R2"],
                "WAPE": metrics["WAPE"],
                "train_seconds": train_seconds,
                "inference_seconds": inference_seconds,
            }
            for (
                model_family,
                candidate_name,
                config,
                _,
                metrics,
                train_seconds,
                inference_seconds,
            ) in all_results
        ]
    )

    selection_results = selection_results.sort_values(
        ["WAPE", "MAE"]
    ).reset_index(drop=True)

    (
        selected_model_family,
        selected_candidate_name,
        selected_config,
        selected_pred_df,
        selected_metrics,
        selected_validation_train_seconds,
        selected_validation_inference_seconds,
    ) = select_best_result(all_results)

    timing_rows: List[Dict[str, Any]] = []

    for model_family, candidate_map in MODEL_CANDIDATES.items():
        family_results = [
            result
            for result in all_results
            if result[0] == model_family
        ]

        family_best = select_best_result(family_results)

        family_best[3].to_csv(
            args.output_dir
            / f"validation_{model_family.lower()}_predictions.csv",
            index=False,
        )

        timing_rows.append(
            {
                "model": model_family,
                "partition": "Validation",
                "train_seconds": family_best[5],
                "inference_seconds": family_best[6],
            }
        )

    test_predictions: Dict[str, pd.DataFrame] = {}

    for model_family, candidate_map in MODEL_CANDIDATES.items():
        family_results = [
            result
            for result in all_results
            if result[0] == model_family
        ]

        family_best = select_best_result(family_results)
        best_config = family_best[2]

        test_prediction_df, test_train_seconds, test_inference_seconds = (
            generate_final_predictions(
                model_family,
                best_config,
                feature_df,
                test_schedule,
            )
        )

        test_predictions[model_family] = test_prediction_df

        test_prediction_df.to_csv(
            args.output_dir
            / f"test_{model_family.lower()}_predictions.csv",
            index=False,
        )

        timing_rows.append(
            {
                "model": model_family,
                "partition": "Test",
                "train_seconds": test_train_seconds,
                "inference_seconds": test_inference_seconds,
            }
        )

    selected_test_pred = test_predictions[selected_model_family]

    selection_results.to_csv(
        args.output_dir / "validation_model_selection_results.csv",
        index=False,
    )

    pd.DataFrame(timing_rows).to_csv(
        args.output_dir / "ml_timing_summary.csv",
        index=False,
    )

    write_validation_report(
        args.output_dir,
        selected_model_family,
        selected_candidate_name,
        selected_config,
        selected_metrics,
        selected_pred_df,
        selected_test_pred,
        selected_validation_train_seconds,
        selected_validation_inference_seconds,
        next(
            row["train_seconds"]
            for row in timing_rows
            if row["model"] == selected_model_family
            and row["partition"] == "Test"
        ),
        next(
            row["inference_seconds"]
            for row in timing_rows
            if row["model"] == selected_model_family
            and row["partition"] == "Test"
        ),
    )

    print("Selected ML family:", selected_model_family)
    print("Selected candidate:", selected_candidate_name)
    print("Selected config:", selected_config)
    print("Validation WAPE:", round(selected_metrics["WAPE"], 4))
    print("Validation MAE:", round(selected_metrics["MAE"], 4))
    print("Validation RMSE:", round(selected_metrics["RMSE"], 4))
    print("Validation R²:", round(selected_metrics["R2"], 4))
    print("Selected test prediction count:", len(selected_test_pred))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
EOF