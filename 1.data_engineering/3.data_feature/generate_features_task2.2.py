from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent

INPUT_PATH = (
    ROOT.parent
    / "2.data_eda"
    / "v4_location_demo_storage_unit_demo_date_daily_qty.csv"
)

OUTPUT_PATH = (
    ROOT
    / "v5_location_demo_storage_unit_demo_features.csv"
)

EXPECTED_COLUMNS = [
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


def build_feature_frame(
    df: pd.DataFrame,
) -> pd.DataFrame:
    required_columns = {
        "date",
        "daily_qty",
    }
    missing_columns = sorted(
        required_columns - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Required columns missing: "
            + ", ".join(missing_columns)
        )

    result = df.copy()

    result["date"] = pd.to_datetime(
        result["date"],
        errors="raise",
    )

    result["daily_qty"] = pd.to_numeric(
        result["daily_qty"],
        errors="raise",
    )

    result = (
        result
        .sort_values("date")
        .reset_index(drop=True)
    )

    if result["date"].duplicated().any():
        raise ValueError(
            "Duplicate dates found in input data."
        )

    result["weekday"] = (
        result["date"].dt.day_name()
    )

    result["month"] = (
        result["date"].dt.month.astype(int)
    )

    result["is_weekend"] = (
        result["date"].dt.weekday >= 5
    ).astype(int)

    result["lag_1"] = (
        result["daily_qty"].shift(1)
    )

    result["lag_7"] = (
        result["daily_qty"].shift(7)
    )

    result["lag_14"] = (
        result["daily_qty"].shift(14)
    )

    shifted_daily_qty = (
        result["daily_qty"].shift(1)
    )

    result["rolling_mean_7"] = (
        shifted_daily_qty
        .rolling(window=7)
        .mean()
    )

    result["rolling_mean_14"] = (
        shifted_daily_qty
        .rolling(window=14)
        .mean()
    )

    result["rolling_std_7"] = (
        shifted_daily_qty
        .rolling(window=7)
        .std()
    )

    output_df = result[
        EXPECTED_COLUMNS
    ].copy()

    output_df["date"] = (
        pd.to_datetime(output_df["date"])
        .dt.strftime("%Y-%m-%d")
    )

    return output_df


def check_reproduction(
    generated_df: pd.DataFrame,
) -> tuple[str, str | None]:
    if not OUTPUT_PATH.exists():
        return "PASS", None

    existing_df = pd.read_csv(
        OUTPUT_PATH
    )

    try:
        pd.testing.assert_frame_equal(
            existing_df,
            generated_df,
            check_dtype=False,
            check_exact=False,
            rtol=1e-9,
            atol=1e-9,
        )
        return "PASS", None

    except AssertionError as exc:
        return "FAIL", str(exc)


def main() -> int:
    print(f"input path: {INPUT_PATH}")
    print(f"output path: {OUTPUT_PATH}")

    if not INPUT_PATH.exists():
        print(
            "input file not found: "
            f"{INPUT_PATH}"
        )
        return 1

    raw_df = pd.read_csv(
        INPUT_PATH
    )

    generated_df = build_feature_frame(
        raw_df
    )

    rows = len(generated_df)
    columns = list(
        generated_df.columns
    )

    print(f"rows: {rows}")
    print(f"columns: {columns}")

    feature_columns = [
        "lag_1",
        "lag_7",
        "lag_14",
        "rolling_mean_7",
        "rolling_mean_14",
        "rolling_std_7",
    ]

    complete_mask = (
        generated_df[feature_columns]
        .notna()
        .all(axis=1)
    )

    if complete_mask.any():
        first_complete_row = (
            generated_df
            .loc[complete_mask, "date"]
            .iloc[0]
        )
    else:
        first_complete_row = "N/A"

    print(
        "first complete row: "
        f"{first_complete_row}"
    )

    nan_counts = {
        column: int(
            generated_df[column]
            .isna()
            .sum()
        )
        for column in feature_columns
    }

    print(
        f"NaN counts: {nan_counts}"
    )

    reproduction_check, mismatch_message = (
        check_reproduction(
            generated_df
        )
    )

    print(
        "reproduction_check: "
        f"{reproduction_check}"
    )

    if reproduction_check == "FAIL":
        print("mismatch details:")
        print(mismatch_message)
        return 1

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    generated_df.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(
        f"output written: {OUTPUT_PATH}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())