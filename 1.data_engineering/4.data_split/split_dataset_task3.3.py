#!/usr/bin/env python3
"""Task 3.3: implement time-series split and forecast schedule for M3."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

REQUIRED_COLUMNS = [
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

MODEL_READY_START = pd.Timestamp("2023-01-15")
MODEL_READY_END = pd.Timestamp("2024-12-30")
EXPECTED_MODEL_READY_ROWS = 716

SPLIT_DATES = {
    "Training Set": (
        pd.Timestamp("2023-01-15"),
        pd.Timestamp("2024-08-31"),
    ),
    "Validation Set": (
        pd.Timestamp("2024-09-01"),
        pd.Timestamp("2024-11-30"),
    ),
    "Test Set": (
        pd.Timestamp("2024-12-01"),
        pd.Timestamp("2024-12-30"),
    ),
}


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[2]
    default_input = (
        project_root
        / "1.data_engineering"
        / "3.data_feature"
        / "v5_location_demo_storage_unit_demo_features.csv"
    )

    parser = argparse.ArgumentParser(
        description="Create time-series datasets and evaluation schedules for M3 Task 3.3."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=default_input,
        help="Path to the feature CSV input.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory for local-only CSV and validation report outputs.",
    )
    return parser.parse_args()


def validate_input_data(df: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if "date" not in df.columns:
        raise ValueError("Missing required 'date' column.")
    if "daily_qty" not in df.columns:
        raise ValueError("Missing required 'daily_qty' column.")

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="raise")
    df = df.sort_values("date").reset_index(drop=True)

    if not df["date"].is_monotonic_increasing:
        raise ValueError("Date column is not ascending after sorting.")
    if df["date"].duplicated().any():
        raise ValueError("Duplicate dates detected in the feature dataset.")

    model_ready = df[
        (df["date"] >= MODEL_READY_START) & (df["date"] <= MODEL_READY_END)
    ].copy()

    if len(model_ready) != EXPECTED_MODEL_READY_ROWS:
        raise ValueError(
            "Model-ready period validation failed: "
            f"expected {EXPECTED_MODEL_READY_ROWS} rows, got {len(model_ready)}."
        )

    if model_ready["date"].min() != MODEL_READY_START:
        raise ValueError(
            f"Model-ready start date mismatch: expected {MODEL_READY_START.date()}, "
            f"got {model_ready['date'].min().date()}"
        )
    if model_ready["date"].max() != MODEL_READY_END:
        raise ValueError(
            f"Model-ready end date mismatch: expected {MODEL_READY_END.date()}, "
            f"got {model_ready['date'].max().date()}"
        )

    return model_ready


def split_datasets(model_ready: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    split_frames: Dict[str, pd.DataFrame] = {}
    for dataset_name, (start_date, end_date) in SPLIT_DATES.items():
        subset = model_ready[
            (model_ready["date"] >= start_date) & (model_ready["date"] <= end_date)
        ].copy()
        if subset.empty:
            raise ValueError(f"Dataset {dataset_name} is empty after filtering by date range.")
        subset = subset.sort_values("date").reset_index(drop=True)
        split_frames[dataset_name] = subset

    total_rows = sum(len(frame) for frame in split_frames.values())
    if total_rows != EXPECTED_MODEL_READY_ROWS:
        raise ValueError(
            "Split dataset total does not match model-ready rows: "
            f"expected {EXPECTED_MODEL_READY_ROWS}, got {total_rows}."
        )

    train_dates = split_frames["Training Set"]["date"]
    val_dates = split_frames["Validation Set"]["date"]
    test_dates = split_frames["Test Set"]["date"]

    if train_dates.iloc[0] != SPLIT_DATES["Training Set"][0]:
        raise ValueError("Training Set start date incorrect.")
    if train_dates.iloc[-1] != SPLIT_DATES["Training Set"][1]:
        raise ValueError("Training Set end date incorrect.")
    if val_dates.iloc[0] != SPLIT_DATES["Validation Set"][0]:
        raise ValueError("Validation Set start date incorrect.")
    if val_dates.iloc[-1] != SPLIT_DATES["Validation Set"][1]:
        raise ValueError("Validation Set end date incorrect.")
    if test_dates.iloc[0] != SPLIT_DATES["Test Set"][0]:
        raise ValueError("Test Set start date incorrect.")
    if test_dates.iloc[-1] != SPLIT_DATES["Test Set"][1]:
        raise ValueError("Test Set end date incorrect.")

    if train_dates.iloc[-1] + pd.Timedelta(days=1) != val_dates.iloc[0]:
        raise ValueError("Training and Validation partitions are not contiguous.")
    if val_dates.iloc[-1] + pd.Timedelta(days=1) != test_dates.iloc[0]:
        raise ValueError("Validation and Test partitions are not contiguous.")

    all_dates = pd.concat([train_dates, val_dates, test_dates], ignore_index=True)
    if all_dates.duplicated().any():
        raise ValueError("Date overlap detected across split datasets.")

    return split_frames


def build_forecast_schedule(
    partition_name: str,
    partition_start: pd.Timestamp,
    partition_end: pd.Timestamp,
) -> pd.DataFrame:
    origin_start = partition_start - pd.Timedelta(days=1)
    origin_end = partition_end - pd.Timedelta(days=1)

    records: List[Dict[str, object]] = []
    for origin in pd.date_range(start=origin_start, end=origin_end, freq="D"):
        max_target = min(origin + pd.Timedelta(days=7), partition_end)
        for target in pd.date_range(start=origin + pd.Timedelta(days=1), end=max_target, freq="D"):
            if not (partition_start <= target <= partition_end):
                continue
            horizon = (target - origin).days
            records.append(
                {
                    "evaluation_partition": partition_name,
                    "forecast_origin": origin,
                    "target_date": target,
                    "horizon": horizon,
                }
            )

    schedule = pd.DataFrame(records)
    if schedule.empty:
        raise ValueError(f"Forecast schedule for {partition_name} is empty.")

    schedule["forecast_origin"] = pd.to_datetime(schedule["forecast_origin"])
    schedule["target_date"] = pd.to_datetime(schedule["target_date"])
    schedule = schedule.sort_values(["forecast_origin", "target_date"]).reset_index(drop=True)
    return schedule


def validate_forecast_schedule(
    schedule: pd.DataFrame,
    partition_name: str,
    partition_start: pd.Timestamp,
    partition_end: pd.Timestamp,
) -> Dict[str, bool]:
    checks: Dict[str, bool] = {}

    checks["forecast_origin_lt_target_date"] = bool(
        (schedule["forecast_origin"] < schedule["target_date"]).all()
    )
    checks["horizon_matches_delta"] = bool(
        (schedule["horizon"] == (schedule["target_date"] - schedule["forecast_origin"]).dt.days).all()
    )
    checks["horizon_in_range_1_to_7"] = bool(
        ((schedule["horizon"] >= 1) & (schedule["horizon"] <= 7)).all()
    )
    checks["targets_in_partition"] = bool(
        schedule["target_date"].between(partition_start, partition_end).all()
    )
    checks["no_partition_crossing"] = bool(
        schedule["target_date"].between(partition_start, partition_end).all()
        and schedule["forecast_origin"].lt(partition_end).all()
    )
    checks["no_duplicate_exact_tasks"] = bool(
        not schedule.duplicated(subset=["evaluation_partition", "forecast_origin", "target_date", "horizon"]).any()
    )
    checks["no_future_data_eligible_violation"] = bool(
        (schedule["target_date"] > schedule["forecast_origin"]).all()
    )

    return checks


def save_local_outputs(
    output_dir: Path,
    split_frames: Dict[str, pd.DataFrame],
    validation_schedule: pd.DataFrame,
    test_schedule: pd.DataFrame,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    trainer = split_frames["Training Set"].copy()
    val = split_frames["Validation Set"].copy()
    test = split_frames["Test Set"].copy()

    trainer.to_csv(output_dir / "training_set.csv", index=False)
    val.to_csv(output_dir / "validation_set.csv", index=False)
    test.to_csv(output_dir / "test_set.csv", index=False)
    validation_schedule.to_csv(output_dir / "validation_forecast_schedule.csv", index=False)
    test_schedule.to_csv(output_dir / "test_forecast_schedule.csv", index=False)


def create_validation_report(
    output_dir: Path,
    input_path: Path,
    model_ready: pd.DataFrame,
    split_frames: Dict[str, pd.DataFrame],
    validation_schedule: pd.DataFrame,
    test_schedule: pd.DataFrame,
    dataset_checks: Dict[str, bool],
    validation_checks: Dict[str, bool],
    test_checks: Dict[str, bool],
) -> None:
    rows = {
        "Training Set": len(split_frames["Training Set"]),
        "Validation Set": len(split_frames["Validation Set"]),
        "Test Set": len(split_frames["Test Set"]),
    }

    split_table = "\n".join(
        [
            "| Dataset | Start | End | Rows |",
            "|---|---|---|---:|",
            f"| Training Set | {SPLIT_DATES['Training Set'][0].date()} | {SPLIT_DATES['Training Set'][1].date()} | {rows['Training Set']} |",
            f"| Validation Set | {SPLIT_DATES['Validation Set'][0].date()} | {SPLIT_DATES['Validation Set'][1].date()} | {rows['Validation Set']} |",
            f"| Test Set | {SPLIT_DATES['Test Set'][0].date()} | {SPLIT_DATES['Test Set'][1].date()} | {rows['Test Set']} |",
        ]
    )

    def format_check_table(checks: Dict[str, bool]) -> str:
        lines = ["| Check | Result |", "|---|---|"]
        for key, value in checks.items():
            lines.append(f"| {key} | {'PASS' if value else 'FAIL'} |")
        return "\n".join(lines)

    report = f'''# Milestone 3 - Data Split Validation

## 1. 目的

Task 3.3 の時系列データ分割と評価スケジュールを実装し、
Validation / Test の境界と future leakage のない設計を確認する。

## 2. 入力データ

- input file: {input_path}
- model-ready period: {MODEL_READY_START.date()} ～ {MODEL_READY_END.date()}
- model-ready rows: {len(model_ready)}
- feature schema: date, daily_qty, weekday, month, is_weekend, lag_1, lag_7, lag_14, rolling_mean_7, rolling_mean_14, rolling_std_7

## 3. Dataset Split Result

{split_table}

## 4. Forecast Schedule

- Validation: first origin = {validation_schedule['forecast_origin'].min().date()}, last origin = {validation_schedule['forecast_origin'].max().date()}, origins = {validation_schedule['forecast_origin'].nunique()}, tasks = {len(validation_schedule)}
- Test: first origin = {test_schedule['forecast_origin'].min().date()}, last origin = {test_schedule['forecast_origin'].max().date()}, origins = {test_schedule['forecast_origin'].nunique()}, tasks = {len(test_schedule)}

## 5. Expanding-window Rule

- training_window は forecast_origin 以前の実績のみを対象とする
- forecast_origin 以後のデータは training_window の候補としない
- Validation と Test の評価期間はそれぞれ独立に管理する

## 6. 7-Day Forecast / Leakage Control

- forecast schedule は未来実績 feature を保持しない
- evaluation_partition, forecast_origin, target_date, horizon のみを保持する
- period 外の target_date を含めない
- 7日先予測では horizon を 1 ～ 7 の範囲で管理する

## 7. Validation Results

### Dataset checks

{format_check_table(dataset_checks)}

### Validation schedule checks

{format_check_table(validation_checks)}

### Test schedule checks

{format_check_table(test_checks)}

## 8. 結論

Task 3.3 のデータ分割および評価スケジュールが設計どおり構築され、
未来情報を使用しない評価条件を確認した。
'''

    (output_dir / "M3_data_split_validation_task3.3.md").write_text(report, encoding="utf-8")


def main() -> int:
    args = parse_args()
    input_path = args.input
    output_dir = args.output_dir

    if not input_path.exists():
        raise FileNotFoundError(f"Input feature file not found: {input_path}")

    df = pd.read_csv(input_path)
    model_ready = validate_input_data(df)
    split_frames = split_datasets(model_ready)

    validation_schedule = build_forecast_schedule(
        "Validation Set",
        SPLIT_DATES["Validation Set"][0],
        SPLIT_DATES["Validation Set"][1],
    )
    test_schedule = build_forecast_schedule(
        "Test Set",
        SPLIT_DATES["Test Set"][0],
        SPLIT_DATES["Test Set"][1],
    )

    dataset_checks = {
        "model_ready_rows_match_expectation": len(model_ready) == EXPECTED_MODEL_READY_ROWS,
        "split_total_equals_model_ready_rows": sum(len(frame) for frame in split_frames.values()) == len(model_ready),
        "training_range_correct": split_frames["Training Set"]["date"].min() == SPLIT_DATES["Training Set"][0] and split_frames["Training Set"]["date"].max() == SPLIT_DATES["Training Set"][1],
        "validation_range_correct": split_frames["Validation Set"]["date"].min() == SPLIT_DATES["Validation Set"][0] and split_frames["Validation Set"]["date"].max() == SPLIT_DATES["Validation Set"][1],
        "test_range_correct": split_frames["Test Set"]["date"].min() == SPLIT_DATES["Test Set"][0] and split_frames["Test Set"]["date"].max() == SPLIT_DATES["Test Set"][1],
        "no_overlap_between_splits": not pd.concat([split_frames["Training Set"]["date"], split_frames["Validation Set"]["date"], split_frames["Test Set"]["date"]], ignore_index=True).duplicated().any(),
        "no_gap_between_splits": (
            split_frames["Training Set"]["date"].max() + pd.Timedelta(days=1) == split_frames["Validation Set"]["date"].min()
            and split_frames["Validation Set"]["date"].max() + pd.Timedelta(days=1) == split_frames["Test Set"]["date"].min()
        ),
        "all_dates_ascending": all(
            split_frames[name]["date"].is_monotonic_increasing for name in ("Training Set", "Validation Set", "Test Set")
        ),
        "no_duplicate_date_within_split": all(
            not frame["date"].duplicated().any() for frame in split_frames.values()
        ),
    }

    validation_checks = validate_forecast_schedule(
        validation_schedule,
        "Validation Set",
        SPLIT_DATES["Validation Set"][0],
        SPLIT_DATES["Validation Set"][1],
    )
    test_checks = validate_forecast_schedule(
        test_schedule,
        "Test Set",
        SPLIT_DATES["Test Set"][0],
        SPLIT_DATES["Test Set"][1],
    )

    for check_name, passed in dataset_checks.items():
        if not passed:
            raise ValueError(f"Dataset validation failed: {check_name}")
    for check_name, passed in validation_checks.items():
        if not passed:
            raise ValueError(f"Validation schedule validation failed: {check_name}")
    for check_name, passed in test_checks.items():
        if not passed:
            raise ValueError(f"Test schedule validation failed: {check_name}")

    save_local_outputs(output_dir, split_frames, validation_schedule, test_schedule)
    create_validation_report(
        output_dir,
        input_path,
        model_ready,
        split_frames,
        validation_schedule,
        test_schedule,
        dataset_checks,
        validation_checks,
        test_checks,
    )

    print("Dataset validation: PASS")
    print(f"Model-ready rows: {len(model_ready)}")
    print(f"Training Set rows: {len(split_frames['Training Set'])}")
    print(f"Validation Set rows: {len(split_frames['Validation Set'])}")
    print(f"Test Set rows: {len(split_frames['Test Set'])}")
    print(f"Validation forecast tasks: {len(validation_schedule)}")
    print(f"Test forecast tasks: {len(test_schedule)}")
    print(f"Outputs written to: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
