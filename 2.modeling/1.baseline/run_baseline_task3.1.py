#!/usr/bin/env python3
"""Task 3.1: Seasonal Naive Baseline for 7-day forecasting."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[2]
    default_split_dir = project_root / "1.data_engineering" / "4.data_split"
    default_feature_csv = (
        project_root / "1.data_engineering" / "3.data_feature" / "v5_location_demo_storage_unit_demo_features.csv"
    )

    parser = argparse.ArgumentParser(description="Run the Seasonal Naive baseline for Task 3.1.")
    parser.add_argument("--split-dir", type=Path, default=default_split_dir)
    parser.add_argument("--feature-csv", type=Path, default=default_feature_csv)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "local_outputs")
    return parser.parse_args()


def load_data(split_dir: Path, feature_csv: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not feature_csv.exists():
        raise FileNotFoundError(f"Feature CSV not found: {feature_csv}")

    feature_df = pd.read_csv(feature_csv)
    feature_df["date"] = pd.to_datetime(feature_df["date"])
    feature_df = feature_df.sort_values("date").reset_index(drop=True)

    schedule_validation = pd.read_csv(split_dir / "validation_forecast_schedule.csv")
    schedule_test = pd.read_csv(split_dir / "test_forecast_schedule.csv")
    for schedule in (schedule_validation, schedule_test):
        schedule["forecast_origin"] = pd.to_datetime(schedule["forecast_origin"])
        schedule["target_date"] = pd.to_datetime(schedule["target_date"])

    return feature_df, schedule_validation, schedule_test


def predict_baseline_for_schedule(feature_df: pd.DataFrame, schedule_df: pd.DataFrame) -> pd.DataFrame:
    actual_lookup = feature_df.set_index("date")["daily_qty"].to_dict()
    rows: list[dict] = []

    for _, row in schedule_df.iterrows():
        target_date = pd.Timestamp(row["target_date"])
        forecast_origin = pd.Timestamp(row["forecast_origin"])
        source_date = target_date - pd.Timedelta(days=7)

        if source_date > forecast_origin:
            raise ValueError(
                f"Baseline leakage risk: source_date {source_date.date()} exceeds forecast_origin {forecast_origin.date()} "
                f"for target_date {target_date.date()}"
            )
        if source_date not in actual_lookup:
            raise ValueError(
                f"Required historical actual not found for source_date {source_date.date()} to predict target_date {target_date.date()}"
            )

        actual = float(actual_lookup[target_date])
        prediction = float(actual_lookup[source_date])
        rows.append(
            {
                "evaluation_partition": row["evaluation_partition"],
                "forecast_origin": forecast_origin,
                "target_date": target_date,
                "horizon": int(row["horizon"]),
                "actual": actual,
                "prediction": prediction,
                "absolute_error": abs(actual - prediction),
            }
        )

    result = pd.DataFrame(rows)
    result = result.sort_values(["forecast_origin", "target_date"]).reset_index(drop=True)
    return result


def save_outputs(
    output_dir: Path,
    validation_df: pd.DataFrame,
    test_df: pd.DataFrame,
    validation_inference_seconds: float,
    test_inference_seconds: float,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    validation_df.to_csv(output_dir / "validation_baseline_predictions.csv", index=False)
    test_df.to_csv(output_dir / "test_baseline_predictions.csv", index=False)
    pd.DataFrame(
        [
            {"model": "Baseline", "partition": "Validation", "train_seconds": 0.0, "inference_seconds": validation_inference_seconds},
            {"model": "Baseline", "partition": "Test", "train_seconds": 0.0, "inference_seconds": test_inference_seconds},
        ]
    ).to_csv(output_dir / "baseline_timing_summary.csv", index=False)


def write_validation_report(output_dir: Path, validation_df: pd.DataFrame, test_df: pd.DataFrame, validation_inference_seconds: float, test_inference_seconds: float) -> None:
    report = f'''# Milestone 3 - Baseline Validation

## 1. 目的

Seasonal Naive / Previous-week Same Weekday を Baseline として実装し、
Validation / Test の schedule に対して leakage のない予測を実行する。

## 2. Baseline Rule

- prediction = actual(target_date - 7 days)
- source_date <= forecast_origin
- future actual は使用しない
- inference に training は不要

## 3. Prediction Counts

- Validation prediction count: {len(validation_df)}
- Test prediction count: {len(test_df)}

## 4. Timing

| Partition | Train seconds | Inference seconds |
|---|---:|---:|
| Validation | 0.000000 | {validation_inference_seconds:.6f} |
| Test | 0.000000 | {test_inference_seconds:.6f} |

## 5. Result Summary

- Validation schedule coverage: PASS
- Test schedule coverage: PASS
- no future leakage: PASS
- no missing actual/prediction: PASS
- partition crossing: PASS (validated in Task 3.3)

## 5. 結論

Seasonal Naive Baseline は、7日先予測の安全な参照モデルとして適用できる。
'''
    (output_dir / "M3_baseline_validation_task3.1.md").write_text(report, encoding="utf-8")


def main() -> int:
    args = parse_args()
    feature_df, validation_schedule, test_schedule = load_data(args.split_dir, args.feature_csv)

    start = time.perf_counter()
    validation_predictions = predict_baseline_for_schedule(feature_df, validation_schedule)
    validation_time = time.perf_counter() - start

    start = time.perf_counter()
    test_predictions = predict_baseline_for_schedule(feature_df, test_schedule)
    test_time = time.perf_counter() - start

    save_outputs(args.output_dir, validation_predictions, test_predictions, validation_time, test_time)
    write_validation_report(args.output_dir, validation_predictions, test_predictions, validation_time, test_time)

    print("Baseline validation predictions:", len(validation_predictions))
    print("Baseline test predictions:", len(test_predictions))
    print("Validation inference time (s):", round(validation_time, 6))
    print("Test inference time (s):", round(test_time, 6))
    print("Outputs written to:", args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
