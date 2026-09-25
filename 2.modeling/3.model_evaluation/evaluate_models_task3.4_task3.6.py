#!/usr/bin/env python3
"""Task 3.4/3.6: compare baseline vs ML forecast accuracy and select the recommended model."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.metrics import compute_metrics


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[2]
    baseline_dir = project_root / "2.modeling" / "1.baseline" / "local_outputs"
    ml_dir = project_root / "2.modeling" / "2.ml_model" / "local_outputs"
    parser = argparse.ArgumentParser(description="Compare Baseline and ML models on Validation/Test sets.")
    parser.add_argument("--baseline-dir", type=Path, default=baseline_dir)
    parser.add_argument("--ml-dir", type=Path, default=ml_dir)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "local_outputs")
    return parser.parse_args()


def load_prediction_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Prediction CSV not found: {path}")
    df = pd.read_csv(path)
    for col in ["forecast_origin", "target_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    df["actual"] = pd.to_numeric(df["actual"], errors="coerce")
    df["prediction"] = pd.to_numeric(df["prediction"], errors="coerce")
    df["absolute_error"] = (df["actual"] - df["prediction"]).abs()
    return df.sort_values(["forecast_origin", "target_date"]).reset_index(drop=True)


def summarize_model(model_name: str, validation_df: pd.DataFrame, test_df: pd.DataFrame) -> dict:
    validation_metrics = {
        "records": int(len(validation_df)),
        **compute_metrics(
            validation_df["actual"],
            validation_df["prediction"],
        ),
    }
    test_metrics = {
        "records": int(len(test_df)),
        **compute_metrics(
            test_df["actual"],
            test_df["prediction"],
        ),
    }
    return {
        "model": model_name,
        "validation_records": validation_metrics["records"],
        "validation_MAE": validation_metrics["MAE"],
        "validation_RMSE": validation_metrics["RMSE"],
        "validation_R2": validation_metrics["R2"],
        "validation_WAPE": validation_metrics["WAPE"],
        "test_records": test_metrics["records"],
        "test_MAE": test_metrics["MAE"],
        "test_RMSE": test_metrics["RMSE"],
        "test_R2": test_metrics["R2"],
        "test_WAPE": test_metrics["WAPE"],
    }


def load_timing(path: Path, model_name: str) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"Timing CSV not found: {path}. "
            "Re-run the corresponding prediction script."
        )

    timing_df = pd.read_csv(path)

    required_columns = [
        "model",
        "partition",
        "train_seconds",
        "inference_seconds",
    ]
    missing_columns = [
        column
        for column in required_columns
        if column not in timing_df.columns
    ]
    if missing_columns:
        raise ValueError(
            f"Missing required timing columns: {', '.join(missing_columns)}"
        )

    model_rows = timing_df[
        timing_df["model"] == model_name
    ].set_index("partition")

    required_partitions = ["Validation", "Test"]
    missing_partitions = [
        partition
        for partition in required_partitions
        if partition not in model_rows.index
    ]
    if missing_partitions:
        raise ValueError(
            f"Missing timing partitions for {model_name}: "
            f"{', '.join(missing_partitions)}"
        )

    timing_values = {
        "validation_train_seconds": float(
            model_rows.loc["Validation", "train_seconds"]
        ),
        "validation_inference_seconds": float(
            model_rows.loc["Validation", "inference_seconds"]
        ),
        "test_train_seconds": float(
            model_rows.loc["Test", "train_seconds"]
        ),
        "test_inference_seconds": float(
            model_rows.loc["Test", "inference_seconds"]
        ),
    }

    for name, value in timing_values.items():
        if not pd.notna(value) or value < 0:
            raise ValueError(
                f"{name} must be a non-negative finite value."
            )

    return timing_values


def choose_recommended(summary_df: pd.DataFrame) -> str:
    ranked = summary_df.sort_values(["validation_WAPE", "validation_MAE"]).reset_index(drop=True)
    return ranked.iloc[0]["model"]


def save_comparison_plot(summary_df: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = ["steelblue", "forestgreen", "darkorange", "crimson"]
    ax.bar(summary_df["model"], summary_df["validation_WAPE"], color=colors[: len(summary_df)])
    ax.set_title("Validation WAPE by model")
    ax.set_ylabel("WAPE (%)")
    ax.set_xlabel("Model")
    for label, val in zip(summary_df["model"], summary_df["validation_WAPE"]):
        ax.text(label, val + 1.0, f"{val:.2f}%", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(output_dir / "validation_model_wape_comparison.png", dpi=200)
    plt.close(fig)


    
def main() -> int:
    args = parse_args()
    model_specs = [
        ("Baseline", args.baseline_dir / "validation_baseline_predictions.csv", args.baseline_dir / "test_baseline_predictions.csv", args.baseline_dir / "baseline_timing_summary.csv", "Baseline"),
        ("Ridge", args.ml_dir / "validation_ridge_predictions.csv", args.ml_dir / "test_ridge_predictions.csv", args.ml_dir / "ml_timing_summary.csv", "Ridge"),
        ("Random Forest", args.ml_dir / "validation_randomforest_predictions.csv", args.ml_dir / "test_randomforest_predictions.csv", args.ml_dir / "ml_timing_summary.csv", "RandomForest"),
        ("Gradient Boosting", args.ml_dir / "validation_gradientboosting_predictions.csv", args.ml_dir / "test_gradientboosting_predictions.csv", args.ml_dir / "ml_timing_summary.csv", "GradientBoosting"),
    ]

    summary_rows = []
    for name, val_path, test_path, timing_path, timing_model_name in model_specs:
        summary_rows.append({**summarize_model(name, load_prediction_csv(val_path), load_prediction_csv(test_path)), **load_timing(timing_path, timing_model_name)})
    summary_df = pd.DataFrame(summary_rows)
    summary_df = summary_df.sort_values(["validation_WAPE", "validation_MAE"]).reset_index(drop=True)
    recommended_model = choose_recommended(summary_df)
    save_comparison_plot(summary_df, args.output_dir)
    summary_df.to_csv(args.output_dir / "model_comparison_summary.csv", index=False)

    print("Model comparison summary:")
    print(summary_df[["model", "validation_WAPE", "validation_MAE", "test_WAPE", "test_MAE"]].to_string(index=False))
    print("Recommended model:", recommended_model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
