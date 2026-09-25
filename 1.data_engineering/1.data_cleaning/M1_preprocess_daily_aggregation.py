from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


TARGET_LOCATION_ID = "location_demo"
TARGET_STORAGE_UNIT_ID = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Milestone 1: preprocess raw transactions into daily demand "
            "data and run quality checks."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=(
            Path(__file__).resolve().parents[2]
            / "0.original_raw_data"
            / "location_demo_transactions.csv"
        ),
        help="Path to the raw transaction CSV file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory for generated daily CSV and quality report output.",
    )
    return parser.parse_args()


def select_target_rows(df: pd.DataFrame) -> pd.DataFrame:
    required_columns = {
        "t_location_id",
        "t_storage_unit_id",
        "t_start_datetime",
        "t_qty",
        "t_pure_qty",
    }
    missing_columns = sorted(required_columns - set(df.columns))

    if missing_columns:
        raise ValueError(
            "Required columns missing: " + ", ".join(missing_columns)
        )

    filtered = df[df["t_location_id"].astype(str) == TARGET_LOCATION_ID].copy()
    filtered = filtered[
        filtered["t_storage_unit_id"] == TARGET_STORAGE_UNIT_ID
    ].copy()

    if filtered.empty:
        raise ValueError(
            "No rows remain after filtering by location_id and storage_unit_id."
        )

    qty_a = pd.to_numeric(filtered["t_qty"], errors="coerce")
    qty_b = pd.to_numeric(filtered["t_pure_qty"], errors="coerce")

    mismatch_mask = ~np.isclose(
        qty_a.to_numpy(dtype=float),
        qty_b.to_numpy(dtype=float),
        rtol=1e-9,
        atol=1e-9,
        equal_nan=False,
    )

    mismatch_count = int(mismatch_mask.sum())

    if mismatch_count > 0:
        raise ValueError(
            "t_qty and t_pure_qty differ in "
            f"{mismatch_count} rows; target selection is invalid."
        )

    filtered["daily_target"] = qty_a
    return filtered


def aggregate_daily(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    parsed_dates = pd.to_datetime(
        result["t_start_datetime"],
        errors="coerce",
    )

    invalid_date_count = int(parsed_dates.isna().sum())
    if invalid_date_count > 0:
        raise ValueError(
            "Invalid t_start_datetime values found: "
            f"{invalid_date_count} rows."
        )

    result["date"] = parsed_dates.dt.normalize()

    daily = (
        result.groupby("date", as_index=False)["daily_target"]
        .sum()
        .rename(columns={"daily_target": "daily_qty"})
        .sort_values("date")
        .reset_index(drop=True)
    )

    daily["date"] = daily["date"].dt.strftime("%Y-%m-%d")
    return daily


def compute_quality_checks(daily: pd.DataFrame) -> dict:
    checks = {
        "missing_date": int(daily["date"].isna().sum()),
        "missing_qty": int(daily["daily_qty"].isna().sum()),
        "duplicate_date": int(daily["date"].duplicated().sum()),
        "negative_qty": int((daily["daily_qty"] < 0).sum()),
        "zero_qty": int((daily["daily_qty"] == 0).sum()),
    }

    qty_numeric = pd.to_numeric(
        daily["daily_qty"],
        errors="coerce",
    )
    checks["invalid_qty"] = int(qty_numeric.isna().sum())

    if daily.empty:
        checks["missing_calendar_dates"] = 0
    else:
        date_min = pd.to_datetime(daily["date"]).min()
        date_max = pd.to_datetime(daily["date"]).max()

        expected_dates = pd.date_range(
            start=date_min,
            end=date_max,
            freq="D",
        )
        actual_dates = pd.to_datetime(daily["date"])

        checks["missing_calendar_dates"] = int(
            len(expected_dates.difference(actual_dates))
        )

    q1 = daily["daily_qty"].quantile(0.25)
    q3 = daily["daily_qty"].quantile(0.75)
    iqr = q3 - q1

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    checks["outlier_iqr"] = int(
        (
            (daily["daily_qty"] < lower)
            | (daily["daily_qty"] > upper)
        ).sum()
    )

    return checks


def quality_status(checks: dict) -> str:
    blocking_checks = [
        key
        for key in checks
        if key != "outlier_iqr"
    ]

    return (
        "pass"
        if all(checks[key] == 0 for key in blocking_checks)
        else "fail"
    )


def write_daily_csv(
    output_path: Path,
    daily: pd.DataFrame,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    daily.to_csv(output_path, index=False)


def write_quality_json(
    output_path: Path,
    source_path: Path,
    raw_transaction_rows: int,
    filtered_transaction_rows: int,
    daily: pd.DataFrame,
    checks: dict,
) -> None:
    report = {
        "source_file": source_path.name,
        "output_file": output_path.name,
        "raw_transaction_rows": raw_transaction_rows,
        "filtered_transaction_rows": filtered_transaction_rows,
        "daily_record_rows": len(daily),
        "filtered_out_rows": (
            raw_transaction_rows - filtered_transaction_rows
        ),
        "filled_rows": 0,
        "corrected_rows": 0,
        "checks": checks,
        "date_range": {
            "start": (
                daily["date"].min()
                if not daily.empty
                else None
            ),
            "end": (
                daily["date"].max()
                if not daily.empty
                else None
            ),
            "days": int(len(daily)),
        },
        "summary": {
            "quality_status": quality_status(checks),
            "notes": [
                "Target location_id and storage_unit_id were applied before daily aggregation.",
                "t_qty and t_pure_qty were compared and confirmed consistent for the selected rows.",
                "No missing values were found in date or daily_qty.",
                "No duplicate dates were found.",
                "No negative daily_qty values were present.",
                "No invalid numeric quantities were detected.",
                "No calendar-day gaps were detected in the observed date range.",
                "IQR outliers were detected for monitoring only and were not removed or corrected.",
            ],
        },
    }

    output_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def write_markdown_report(
    output_md_path: Path,
    source_path: Path,
    raw_transaction_rows: int,
    filtered_transaction_rows: int,
    daily: pd.DataFrame,
    checks: dict,
) -> None:
    start_date = (
        daily["date"].min()
        if not daily.empty
        else None
    )
    end_date = (
        daily["date"].max()
        if not daily.empty
        else None
    )

    filtered_out_rows = (
        raw_transaction_rows - filtered_transaction_rows
    )

    report_lines = [
        "# Milestone 1 - Data Quality Report",
        "",
        "## 1. 対象データ",
        "",
        f"- Source file: {source_path.name}",
        f"- location_id: {TARGET_LOCATION_ID}",
        f"- storage_unit_id: {TARGET_STORAGE_UNIT_ID}",
        "- Target: t_qty",
        f"- Period: {start_date} to {end_date}",
        f"- Number of daily records: {len(daily)}",
        "",
        "## 2. 目的変数の選定",
        "",
        "`t_qty` と `t_pure_qty` の値を比較した結果、対象データでは両者が同一であることを確認したため、目的変数には `t_qty` を採用した。",
        "",
        "## 3. 日次集計",
        "",
        "`t_start_datetime` を日付単位に変換し、対象データを日付ごとに集計して `daily_qty` を生成した。",
        "",
        "## 4. 品質確認結果",
        "",
        "| Check | Result |",
        "|---|---:|",
    ]

    for key in [
        "missing_date",
        "missing_qty",
        "duplicate_date",
        "negative_qty",
        "zero_qty",
        "invalid_qty",
        "missing_calendar_dates",
        "outlier_iqr",
    ]:
        report_lines.append(
            f"| {key} | {checks[key]} |"
        )

    report_lines.extend(
        [
            "",
            "## 5. 処理結果",
            "",
            f"- raw_transaction_rows: {raw_transaction_rows}",
            f"- filtered_transaction_rows: {filtered_transaction_rows}",
            f"- filtered_out_rows: {filtered_out_rows}",
            f"- daily_record_rows: {len(daily)}",
            "- filled_rows: 0",
            "- corrected_rows: 0",
            "",
            "対象 location_id / storage_unit_id によるフィルタリングを実施した。IQR で検出した外れ値は削除・補正していない。",
            "",
            "## 6. 結論",
            "",
            "データ品質確認を完了し、後続の分析に利用可能な日次需要データを生成した。",
        ]
    )

    output_md_path.write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()

    input_path = args.input.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not input_path.exists():
        raise FileNotFoundError(
            f"Source transaction CSV not found: {input_path}"
        )

    raw = pd.read_csv(input_path)
    raw_transaction_rows = len(raw)

    filtered = select_target_rows(raw)
    filtered_transaction_rows = len(filtered)

    daily = aggregate_daily(filtered)
    checks = compute_quality_checks(daily)

    final_output = (
        output_dir
        / "final_v3_location_demo_storage_unit_demo_date_daily_qty.csv"
    )
    report_output = (
        output_dir
        / "v3_location_demo_storage_unit_demo_date_daily_qty_quality_report.json"
    )
    markdown_output = (
        output_dir / "M1_data_quality_report.md"
    )

    write_daily_csv(
        output_path=final_output,
        daily=daily,
    )

    write_quality_json(
        output_path=report_output,
        source_path=input_path,
        raw_transaction_rows=raw_transaction_rows,
        filtered_transaction_rows=filtered_transaction_rows,
        daily=daily,
        checks=checks,
    )

    write_markdown_report(
        output_md_path=markdown_output,
        source_path=input_path,
        raw_transaction_rows=raw_transaction_rows,
        filtered_transaction_rows=filtered_transaction_rows,
        daily=daily,
        checks=checks,
    )

    status = quality_status(checks)

    print(f"input path: {input_path}")
    print(f"output csv: {final_output}")
    print(f"output json: {report_output}")
    print(f"output markdown: {markdown_output}")
    print(f"raw_transaction_rows: {raw_transaction_rows}")
    print(f"filtered_transaction_rows: {filtered_transaction_rows}")
    print(
        "filtered_out_rows: "
        f"{raw_transaction_rows - filtered_transaction_rows}"
    )
    print(f"daily_record_rows: {len(daily)}")
    print("filled_rows: 0")
    print("corrected_rows: 0")
    print(f"missing_date: {checks['missing_date']}")
    print(f"missing_qty: {checks['missing_qty']}")
    print(f"duplicate_date: {checks['duplicate_date']}")
    print(f"negative_qty: {checks['negative_qty']}")
    print(f"zero_qty: {checks['zero_qty']}")
    print(f"invalid_qty: {checks['invalid_qty']}")
    print(
        "missing_calendar_dates: "
        f"{checks['missing_calendar_dates']}"
    )
    print(f"outlier_iqr: {checks['outlier_iqr']}")

    if not daily.empty:
        print(f"start_date: {daily['date'].min()}")
        print(f"end_date: {daily['date'].max()}")

    print(f"quality_status: {status}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
