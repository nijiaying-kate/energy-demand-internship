import argparse
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(
        description="Export standardized evaluation results for Task 4.3."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=SCRIPT_DIR / "local_outputs" / "model_comparison_summary.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=SCRIPT_DIR / "local_outputs" / "evaluation_results_task4.3.csv",
    )
    parser.add_argument("--evaluation-start", default="2024-12-01")
    parser.add_argument("--evaluation-end", default="2024-12-30")
    parser.add_argument("--horizon-days", type=int, default=7)
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()

    if args.horizon_days != 7:
        raise ValueError(
            "horizon_days must be 7 for the current M4.3 evaluation design."
        )

    input_path = args.input
    output_path = args.output

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df = pd.read_csv(input_path)

    required_columns = [
        "model",
        "test_MAE",
        "test_RMSE",
        "test_R2",
        "test_WAPE",
        "test_train_seconds",
        "test_inference_seconds",
    ]

    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(missing_columns)}"
        )

    result = pd.DataFrame(
        {
            "model_name": df["model"],
            "evaluation_start": args.evaluation_start,
            "evaluation_end": args.evaluation_end,
            "horizon_days": args.horizon_days,
            "mae": df["test_MAE"],
            "rmse": df["test_RMSE"],
            "r2": df["test_R2"],
            "wape": df["test_WAPE"],
            "train_seconds": df["test_train_seconds"],
            "inference_seconds": df["test_inference_seconds"],
            "seed": args.seed,
        }
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)

    print("Evaluation Results Export")
    print(f"Evaluation Period : {args.evaluation_start} to {args.evaluation_end}")
    print(f"Horizon           : {args.horizon_days} days")
    print(f"Seed              : {args.seed}")
    print(f"Output            : {output_path}")
    print()
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
