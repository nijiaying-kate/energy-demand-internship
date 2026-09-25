from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
EXPECTED_INPUT_PATH = ROOT / "location_demo_storage_unit_demo_features.csv"
FALLBACK_INPUT_PATH = ROOT / "v5_location_demo_storage_unit_demo_features.csv"
REPORT_PATH = ROOT / "M2_feature_integrity_check_task2.3_task2.4.md"

REQUIRED_COLUMNS = [
    "date",
    "daily_qty",
    "lag_1",
    "lag_7",
    "lag_14",
    "rolling_mean_7",
    "rolling_mean_14",
    "rolling_std_7",
]

EXPECTED_NAN_COUNTS = {
    "lag_1": 1,
    "lag_7": 7,
    "lag_14": 14,
    "rolling_mean_7": 7,
    "rolling_mean_14": 14,
    "rolling_std_7": 7,
}

EXPECTED_FIRST_COMPLETE_DATE = pd.Timestamp("2023-01-15")
TOLERANCE = dict(rtol=1e-9, atol=1e-9)


def find_feature_file() -> Path:
    candidates = [EXPECTED_INPUT_PATH, FALLBACK_INPUT_PATH]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        f"Feature dataset not found. Checked: {EXPECTED_INPUT_PATH} and {FALLBACK_INPUT_PATH}."
    )


def validate_schema(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    return (len(missing) == 0, missing)


def compare_full_series(
    df: pd.DataFrame,
    expected: pd.Series,
    actual: pd.Series,
    feature_name: str,
) -> Dict[str, Any]:
    valid_mask = expected.notna() & actual.notna()
    checked_rows = int(valid_mask.sum())
    if checked_rows == 0:
        return {
            "feature": feature_name,
            "checked_rows": 0,
            "mismatch_count": 0,
            "result": "PASS",
        }

    expected_vals = pd.to_numeric(expected[valid_mask], errors="coerce").to_numpy(dtype=float)
    actual_vals = pd.to_numeric(actual[valid_mask], errors="coerce").to_numpy(dtype=float)
    mismatch_mask = ~np.isclose(expected_vals, actual_vals, **TOLERANCE)
    mismatch_count = int(mismatch_mask.sum())
    mismatched_dates = df.loc[valid_mask].iloc[mismatch_mask, :]["date"].dt.strftime("%Y-%m-%d").tolist()[:5]

    return {
        "feature": feature_name,
        "checked_rows": checked_rows,
        "mismatch_count": mismatch_count,
        "mismatch_dates": mismatched_dates,
        "result": "PASS" if mismatch_count == 0 else "FAIL",
    }


def evaluate_data_leakage(df: pd.DataFrame) -> Dict[str, Any]:
    checks = {
        "lag_1": compare_full_series(df, df["daily_qty"].shift(1), df["lag_1"], "lag_1"),
        "lag_7": compare_full_series(df, df["daily_qty"].shift(7), df["lag_7"], "lag_7"),
        "lag_14": compare_full_series(df, df["daily_qty"].shift(14), df["lag_14"], "lag_14"),
        "rolling_mean_7": compare_full_series(
            df,
            df["daily_qty"].shift(1).rolling(window=7).mean(),
            df["rolling_mean_7"],
            "rolling_mean_7",
        ),
        "rolling_mean_14": compare_full_series(
            df,
            df["daily_qty"].shift(1).rolling(window=14).mean(),
            df["rolling_mean_14"],
            "rolling_mean_14",
        ),
        "rolling_std_7": compare_full_series(
            df,
            df["daily_qty"].shift(1).rolling(window=7).std(),
            df["rolling_std_7"],
            "rolling_std_7",
        ),
    }

    total_mismatches = sum(item["mismatch_count"] for item in checks.values())
    result = "PASS" if total_mismatches == 0 else "FAIL"
    return {"checks": checks, "total_mismatches": total_mismatches, "result": result}


def evaluate_nan_boundary(df: pd.DataFrame) -> Dict[str, Any]:
    actual = {feature: int(df[feature].isna().sum()) for feature in EXPECTED_NAN_COUNTS}
    details = []
    all_pass = True
    for feature, expected in EXPECTED_NAN_COUNTS.items():
        result = "PASS" if actual[feature] == expected else "FAIL"
        all_pass = all_pass and (result == "PASS")
        details.append({
            "feature": feature,
            "expected_nan": expected,
            "actual_nan": actual[feature],
            "result": result,
        })

    full_mask = df[["lag_1", "lag_7", "lag_14", "rolling_mean_7", "rolling_mean_14", "rolling_std_7"]].notna().all(axis=1)
    first_complete = df.loc[full_mask, "date"].iloc[0] if full_mask.any() else None
    first_complete_result = "PASS" if first_complete == EXPECTED_FIRST_COMPLETE_DATE else "FAIL"
    all_pass = all_pass and (first_complete_result == "PASS")

    return {
        "details": details,
        "first_complete_date": first_complete,
        "expected_first_complete_date": EXPECTED_FIRST_COMPLETE_DATE,
        "result": "PASS" if all_pass else "FAIL",
    }


def write_report(
    report_path: Path,
    input_path: Path,
    total_rows: int,
    leakage_summary: Dict[str, Any],
    nan_summary: Dict[str, Any],
    overall_result: str,
) -> None:
    lines: List[str] = []
    lines.append("# Feature Integrity Check")
    lines.append("")
    lines.append("## 1. 対応タスク")
    lines.append("")
    lines.append("- Task 2.3 データリーク確認")
    lines.append("- Task 2.4 特徴量生成処理のテスト")
    lines.append("")
    lines.append("## 2. 確認目的")
    lines.append("")
    lines.append("Task 2.2 で生成した特徴量について、参照時点の妥当性と生成処理の正しさを確認する。")
    lines.append("")
    lines.append("本確認では、データリーク、Lag計算、Rolling計算、Availability / NaN境界を対象とする。")
    lines.append("")
    lines.append("## 3. 確認方法")
    lines.append("")
    lines.append("### 3.1 データリーク")
    lines.append("Lag / Rolling を期待式から再計算し、対象日当日および対象日以降の `daily_qty` が使用されていないことを確認した。")
    lines.append("")
    lines.append("### 3.2 Lag計算")
    lines.append("`shift(1)`, `shift(7)`, `shift(14)` と全量照合した。")
    lines.append("")
    lines.append("### 3.3 Rolling計算")
    lines.append("`shift(1).rolling(...)` と全量照合した。")
    lines.append("")
    lines.append("### 3.4 Availability")
    lines.append("NaN 数と最初の完全行を確認した。")
    lines.append("")
    lines.append("## 4. 確認結果")
    lines.append("")
    lines.append("| Check | Target | Mismatches | Result |")
    lines.append("|---|---|---:|---|")
    lines.append(f"| Data Leakage | Lag / Rolling reference timing | {leakage_summary['total_mismatches']} | {leakage_summary['result']} |")
    lines.append(f"| Lag Calculation | lag_1 / lag_7 / lag_14 | {sum(v['mismatch_count'] for v in leakage_summary['checks'].values() if v['feature'] in ['lag_1','lag_7','lag_14'])} | {'PASS' if sum(v['mismatch_count'] for v in leakage_summary['checks'].values() if v['feature'] in ['lag_1','lag_7','lag_14']) == 0 else 'FAIL'} |")
    lines.append(f"| Rolling Calculation | rolling_mean_7 / rolling_mean_14 / rolling_std_7 | {sum(v['mismatch_count'] for v in leakage_summary['checks'].values() if v['feature'] in ['rolling_mean_7','rolling_mean_14','rolling_std_7'])} | {'PASS' if sum(v['mismatch_count'] for v in leakage_summary['checks'].values() if v['feature'] in ['rolling_mean_7','rolling_mean_14','rolling_std_7']) == 0 else 'FAIL'} |")
    lines.append(f"| Availability | NaN boundary | {sum(item['expected_nan'] != item['actual_nan'] for item in nan_summary['details'])} | {nan_summary['result']} |")
    lines.append("")
    lines.append(f"- Input: {input_path}")
    lines.append(f"- Total rows: {total_rows}")
    lines.append(f"- Total mismatches: {leakage_summary['total_mismatches']}")
    lines.append(f"- First complete row: {nan_summary['first_complete_date'].strftime('%Y-%m-%d') if nan_summary['first_complete_date'] is not None else 'None'}")
    lines.append(f"- Overall: {overall_result}")
    lines.append("")
    lines.append("## 5. 必要な詳細")
    lines.append("")
    for item in leakage_summary["checks"].values():
        lines.append(f"- {item['feature']}: checked_rows={item['checked_rows']}, mismatch_count={item['mismatch_count']}, result={item['result']}")
    lines.append("")
    lines.append("| Feature | Expected NaN | Actual NaN | Result |")
    lines.append("|---|---:|---:|---|")
    for item in nan_summary["details"]:
        lines.append(f"| {item['feature']} | {item['expected_nan']} | {item['actual_nan']} | {item['result']} |")
    lines.append("")
    lines.append("- 最初に全ての特徴量が利用可能となる日付: Expected=2023-01-15 / Actual=" + (nan_summary['first_complete_date'].strftime('%Y-%m-%d') if nan_summary['first_complete_date'] is not None else 'None') + f" / Result={nan_summary['result']}")
    lines.append("")
    lines.append("## 6. 結論")
    lines.append("")
    if overall_result == "PASS":
        lines.append("データリーク、Lag計算、Rolling計算、Availability の全項目で問題がないことを確認した。")
        lines.append("")
        lines.append("- Task 2.3: PASS")
        lines.append("- Task 2.4: PASS")
    else:
        lines.append("少なくとも1項目で不一致が確認されたため、Task 2.3 / Task 2.4 は FAIL と判定した。")
        lines.append("")
        lines.append("- Task 2.3: FAIL")
        lines.append("- Task 2.4: FAIL")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    try:
        input_path = find_feature_file()
    except FileNotFoundError as exc:
        print("Milestone 2 Feature Integrity Check")
        print(f"Input: {EXPECTED_INPUT_PATH}")
        print("Task 2.3 Data Leakage: FAIL")
        print("Task 2.4 Feature Generation Test: FAIL")
        print("Lag mismatches: N/A")
        print("Rolling mismatches: N/A")
        print("NaN boundary: FAIL")
        print("First complete row: N/A")
        print("Modified dataset: No")
        print("Generated files:")
        print("- M2_check_feature_integrity_task2.3_task2.4.py")
        print("- M2_feature_integrity_check_task2.3_task2.4.md")
        print(str(exc))
        return 1

    df = pd.read_csv(input_path)
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="raise")
    df = df.sort_values("date").reset_index(drop=True)

    schema_ok, missing_cols = validate_schema(df)
    if not schema_ok:
        print("Milestone 2 Feature Integrity Check")
        print(f"Input: {input_path}")
        print("Task 2.3 Data Leakage: FAIL")
        print("Task 2.4 Feature Generation Test: FAIL")
        print("Lag mismatches: N/A")
        print("Rolling mismatches: N/A")
        print("NaN boundary: FAIL")
        print("First complete row: N/A")
        print("Modified dataset: No")
        print("Generated files:")
        print("- M2_check_feature_integrity_task2.3_task2.4.py")
        print("- M2_feature_integrity_check_task2.3_task2.4.md")
        print(f"Missing required columns: {missing_cols}")
        return 1

    leakage_summary = evaluate_data_leakage(df)
    nan_summary = evaluate_nan_boundary(df)

    total_lag_mismatches = sum(
        v["mismatch_count"] for v in leakage_summary["checks"].values() if v["feature"] in ["lag_1", "lag_7", "lag_14"]
    )
    total_rolling_mismatches = sum(
        v["mismatch_count"] for v in leakage_summary["checks"].values() if v["feature"] in ["rolling_mean_7", "rolling_mean_14", "rolling_std_7"]
    )

    task_23_ok = leakage_summary["result"] == "PASS"
    task_24_ok = (
        total_lag_mismatches == 0
        and total_rolling_mismatches == 0
        and nan_summary["result"] == "PASS"
    )
    overall_result = "PASS" if task_23_ok and task_24_ok else "FAIL"

    write_report(
        report_path=REPORT_PATH,
        input_path=input_path,
        total_rows=len(df),
        leakage_summary=leakage_summary,
        nan_summary=nan_summary,
        overall_result=overall_result,
    )

    print("Milestone 2 Feature Integrity Check")
    print(f"Task 2.3 Data Leakage: {'PASS' if task_23_ok else 'FAIL'}")
    print(f"Task 2.4 Feature Generation Test: {'PASS' if task_24_ok else 'FAIL'}")
    print(f"Lag mismatches: {total_lag_mismatches}")
    print(f"Rolling mismatches: {total_rolling_mismatches}")
    print(f"NaN boundary: {nan_summary['result']}")
    print(f"First complete row: {nan_summary['first_complete_date'].strftime('%Y-%m-%d') if nan_summary['first_complete_date'] is not None else 'None'}")
    print("Modified dataset: No")
    print("Generated files:")
    print("- M2_check_feature_integrity_task2.3_task2.4.py")
    print("- M2_feature_integrity_check_task2.3_task2.4.md")
    print(f"Overall: {overall_result}")

    return 0 if overall_result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
