#!/usr/bin/env python3
"""Task 3.5: inspect large forecast errors and summarize observed patterns."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[2]

    ml_dir = project_root / "2.modeling" / "2.ml_model" / "local_outputs"
    daily_data = (
        project_root
        / "1.data_engineering"
        / "2.data_eda"
        / "v4_location_demo_storage_unit_demo_date_daily_qty.csv"
    )
    outlier_data = (
        project_root
        / "1.data_engineering"
        / "2.data_eda"
        / "tables"
        / "04_outlier_days.csv"
    )

    parser = argparse.ArgumentParser(
        description="Analyze large ML forecast errors."
    )
    parser.add_argument("--ml-dir", type=Path, default=ml_dir)
    parser.add_argument("--daily-data", type=Path, default=daily_data)
    parser.add_argument("--outlier-data", type=Path, default=outlier_data)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
    )

    return parser.parse_args()


def load_predictions(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    df["forecast_origin"] = pd.to_datetime(df["forecast_origin"])
    df["target_date"] = pd.to_datetime(df["target_date"])
    df["actual"] = pd.to_numeric(df["actual"], errors="coerce")
    df["prediction"] = pd.to_numeric(df["prediction"], errors="coerce")

    df["absolute_error"] = (
        df["actual"] - df["prediction"]
    ).abs()

    df["signed_error"] = (
        df["prediction"] - df["actual"]
    )

    df["weekday"] = df["target_date"].dt.day_name()

    return df.sort_values(
        ["target_date", "forecast_origin"]
    ).reset_index(drop=True)


def aggregate_daily_errors(df: pd.DataFrame) -> pd.DataFrame:
    daily = (
        df.groupby("target_date", as_index=False)
        .agg(
            actual=("actual", "first"),
            mean_prediction=("prediction", "mean"),
            mean_absolute_error=("absolute_error", "mean"),
            max_absolute_error=("absolute_error", "max"),
            forecast_count=("prediction", "count"),
            weekday=("weekday", "first"),
        )
    )


    return daily.sort_values(
        "mean_absolute_error",
        ascending=False,
    ).reset_index(drop=True)


def load_daily_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    df["date"] = pd.to_datetime(df["date"])
    df["daily_qty"] = pd.to_numeric(
        df["daily_qty"],
        errors="coerce",
    )
    df["weekday"] = df["date"].dt.day_name()
    df["month"] = df["date"].dt.month
    df["season"] = ((df["date"].dt.month % 12) // 3 + 1).astype(int)
    df["is_weekend"] = df["date"].dt.weekday.ge(5)

    return df


def load_outlier_dates(path: Path) -> set[pd.Timestamp]:
    if not path.exists():
        return set()

    df = pd.read_csv(path)

    if "date" not in df.columns:
        return set()

    return set(pd.to_datetime(df["date"], errors="coerce").dropna())


def enrich_error_analysis(
    error_days: pd.DataFrame,
    daily_data: pd.DataFrame,
    outlier_dates: set[pd.Timestamp],
) -> pd.DataFrame:

    data = error_days.merge(
        daily_data[
            [
                "date",
                "daily_qty",
                "weekday",
                "month",
                "season",
                "is_weekend",
            ]
        ],
        left_on="target_date",
        right_on="date",
        how="left",
        suffixes=("", "_daily"),
    )

    data["daily_qty_match"] = (
        data["actual"] - data["daily_qty"]
    ).abs() < 1e-9

    data["outlier_flag"] = data["target_date"].isin(
        outlier_dates
    )

    return data


def save_error_barplot(
    daily_errors: pd.DataFrame,
    out_path: Path,
) -> None:

    top = daily_errors.head(10).copy()

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.bar(
        top["target_date"].dt.strftime("%Y-%m-%d"),
        top["mean_absolute_error"],
    )

    ax.set_title("Top 10 large-error days")
    ax.set_ylabel("Mean absolute error")
    ax.set_xlabel("Target date")

    plt.xticks(rotation=45)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def write_report(
    output_dir: Path,
    validation_days: pd.DataFrame,
    daily_data: pd.DataFrame,
) -> None:

    output_dir.mkdir(parents=True, exist_ok=True)

    top3 = validation_days.head(3)

    lines = [
        "# Milestone 3 - Error Analysis",
        "",
        "## 1. 目的",
        "",
        "Validation Set の予測結果を target_date 単位で集計し、誤差の大きい日を抽出する。曜日、販売量、データ品質を確認し、観測された誤差パターンを整理する。",
        "",
        "## 2. Large-error days",
        "",
        "| target_date | weekday | actual | mean_prediction | mean_absolute_error | max_absolute_error | forecast_count |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]

    for _, row in top3.iterrows():
        lines.append(
            f"| {row['target_date'].strftime('%Y-%m-%d')} "
            f"| {row['weekday']} "
            f"| {row['actual']:.2f} "
            f"| {row['mean_prediction']:.2f} "
            f"| {row['mean_absolute_error']:.2f} "
            f"| {row['max_absolute_error']:.2f} "
            f"| {int(row['forecast_count'])} |"
        )

    lines.extend(
        [
            "",
            "## 3. Sales volume and weekday",
            "",
            "| target_date | weekday | daily_qty | percentile context |",
            "|---|---|---:|---|",
        ]
    )

    daily_sales = daily_data["daily_qty"].dropna()

    for _, row in top3.iterrows():
        percentile = float(
            (daily_sales <= row["actual"]).mean() * 100.0
        )

        lines.append(
            f"| {row['target_date'].strftime('%Y-%m-%d')} "
            f"| {row['weekday']} "
            f"| {row['actual']:.2f} "
            f"| {percentile:.1f} percentile |"
        )

    lines.extend(
        [
            "",
            "## 4. Data quality check",
            "",
            "| target_date | daily_qty match | outlier flag |",
            "|---|---|---|",
        ]
    )

    for _, row in top3.iterrows():
        lines.append(
            f"| {row['target_date'].strftime('%Y-%m-%d')} "
            f"| {'Yes' if row['daily_qty_match'] else 'No'} "
            f"| {'Yes' if row['outlier_flag'] else 'No'} |"
        )

    lines.extend(
        [
            "",
            "## 5. Observed error pattern",
            "",
            "- The three largest-error days correspond to relatively high-demand days.",
            "- The Ridge model consistently underpredicts demand on these dates across multiple forecast origins.",
            "- The three dates occur on different weekdays: Wednesday, Thursday, and Monday.",
            "- The three dates were not flagged in the existing outlier-day analysis.",
            "- The available daily data does not show an obvious data-quality issue for these dates.",
            "",
            "The observed results indicate a tendency toward underprediction on relatively high-demand days. However, the analysis does not establish that all high-demand days produce large errors or identify a specific external cause.",
        ]
    )

    report_path = (
        output_dir / "M3_error_analysis_task3.5.md"
    )

    report_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()

    validation_df = load_predictions(
        args.ml_dir / "validation_ridge_predictions.csv"
    )

    validation_days = aggregate_daily_errors(
        validation_df
    )

    daily_data = load_daily_data(args.daily_data)

    outlier_dates = load_outlier_dates(
        args.outlier_data
    )

    validation_days = enrich_error_analysis(
        validation_days,
        daily_data,
        outlier_dates,
    )

    save_error_barplot(
        validation_days,
        args.output_dir / "validation_top_error_barplot.png",
    )

    write_report(
        args.output_dir,
        validation_days,
        daily_data,
    )

    print("\nTop 3 large-error days:")

    print(
        validation_days.head(3)[
            [
                "target_date",
                "weekday",
                "actual",
                "mean_prediction",
                "mean_absolute_error",
                "max_absolute_error",
                "forecast_count",
                "daily_qty_match",
                "outlier_flag",
            ]
        ].to_string(index=False)
    )

    print("\nReport:")
    print(
        args.output_dir
        / "M3_error_analysis_task3.5.md"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
