import argparse
import math
import unittest
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent


def load_forecast(input_path):
    """Load and validate a 7-day forecast result."""
    df = pd.read_csv(input_path)

    required_columns = [
        "forecast_origin",
        "target_date",
        "horizon",
        "location_id",
        "storage_unit_id",
        "model_name",
        "predicted_qty",
    ]

    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(missing_columns)}"
        )

    if df.empty:
        raise ValueError("Forecast data is empty.")

    if len(df) != 7:
        raise ValueError(
            f"Expected exactly 7 forecast rows, but found {len(df)}."
        )

    df["forecast_origin"] = pd.to_datetime(
        df["forecast_origin"],
        errors="raise",
    )
    df["target_date"] = pd.to_datetime(
        df["target_date"],
        errors="raise",
    )
    df["horizon"] = pd.to_numeric(
        df["horizon"],
        errors="raise",
    )
    df["predicted_qty"] = pd.to_numeric(
        df["predicted_qty"],
        errors="raise",
    )

    df = df.sort_values("target_date").reset_index(drop=True)

    expected_horizons = list(range(1, 8))
    actual_horizons = df["horizon"].astype(int).tolist()

    if actual_horizons != expected_horizons:
        raise ValueError(
            "Forecast horizon must contain exactly 1 through 7 "
            f"in target-date order, but found {actual_horizons}."
        )

    if df["forecast_origin"].nunique() != 1:
        raise ValueError(
            "Forecast data must contain exactly one forecast origin."
        )

    forecast_origin = df.loc[0, "forecast_origin"]
    expected_target_dates = pd.date_range(
        start=forecast_origin + pd.Timedelta(days=1),
        periods=7,
        freq="D",
    )

    actual_target_dates = df["target_date"].tolist()

    if actual_target_dates != expected_target_dates.tolist():
        raise ValueError(
            "Target dates must be continuous daily dates from "
            "forecast_origin + 1 day through forecast_origin + 7 days."
        )

    if df["predicted_qty"].isna().any():
        raise ValueError("Prediction values must not contain NaN.")

    return df


def apply_inventory_forecast(df):
    """
    M4.4:
    Keep original predictions for evaluation-related use.
    Use max(predicted_qty, 0) for inventory calculation.
    """
    result = df.copy()

    result["inventory_predicted_qty"] = result["predicted_qty"].clip(lower=0)

    return result


def calculate_inventory(
    df,
    initial_inventory,
    safety_stock,
    replenishment_qty,
):
    """
    M4.5 / M4.6:
    Calculate daily inventory and perform one replenishment
    on the first day when pre-replenishment inventory
    reaches or falls below safety stock.
    """
    result = df.copy()

    inventory_before_replenishment = []
    inventory_after_replenishment = []

    current_inventory = float(initial_inventory)
    replenishment_date = None

    for _, row in result.iterrows():
        demand = float(row["inventory_predicted_qty"])

        inventory_before = current_inventory - demand

        inventory_before_replenishment.append(inventory_before)

        current_inventory = inventory_before

        if (
            replenishment_date is None
            and current_inventory <= safety_stock
        ):
            current_inventory += replenishment_qty
            replenishment_date = row["target_date"]

        inventory_after_replenishment.append(current_inventory)

    result["inventory_before_replenishment"] = (
        inventory_before_replenishment
    )
    result["inventory_after_replenishment"] = (
        inventory_after_replenishment
    )

    result["replenishment"] = (
        result["target_date"] == replenishment_date
    ).astype(int)

    return result, replenishment_date


def validate_parameters(
    initial_inventory,
    safety_stock,
    replenishment_qty,
):
    parameters = {
        "initial_inventory": initial_inventory,
        "safety_stock": safety_stock,
        "replenishment_qty": replenishment_qty,
    }

    for name, value in parameters.items():
        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{name} must be numeric."
            ) from exc

        if not math.isfinite(numeric_value):
            raise ValueError(
                f"{name} must be a finite value."
            )

        if numeric_value < 0:
            raise ValueError(
                f"{name} must be non-negative."
            )


# ----------------------------------------------------------------------
# M4.7 Tests
# ----------------------------------------------------------------------

class TestInventorySimulation(unittest.TestCase):

    def test_negative_forecast_becomes_zero(self):
        df = pd.DataFrame(
            {
                "forecast_origin": ["2024-12-30"],
                "target_date": ["2026-03-06"],
                "location_id": ["test_site"],
                "storage_unit_id": ["test_storage_unit"],
                "model_name": ["Ridge Regression"],
                "predicted_qty": [-100.0],
            }
        )

        result = apply_inventory_forecast(df)

        self.assertEqual(
            result.loc[0, "inventory_predicted_qty"],
            0.0,
        )

    def test_inventory_subtraction(self):
        df = pd.DataFrame(
            {
                "target_date": pd.to_datetime(
                    ["2026-03-06", "2026-03-07"]
                ),
                "inventory_predicted_qty": [100.0, 200.0],
            }
        )

        result, replenishment_date = calculate_inventory(
            df,
            initial_inventory=1000,
            safety_stock=100,
            replenishment_qty=500,
        )

        self.assertEqual(
            result.loc[0, "inventory_before_replenishment"],
            900.0,
        )

        self.assertEqual(
            result.loc[1, "inventory_before_replenishment"],
            700.0,
        )

        self.assertIsNone(replenishment_date)

    def test_safety_stock_date(self):
        df = pd.DataFrame(
            {
                "target_date": pd.to_datetime(
                    [
                        "2026-03-06",
                        "2026-03-07",
                        "2026-03-08",
                    ]
                ),
                "inventory_predicted_qty": [
                    300.0,
                    400.0,
                    200.0,
                ],
            }
        )

        result, replenishment_date = calculate_inventory(
            df,
            initial_inventory=1000,
            safety_stock=300,
            replenishment_qty=500,
        )

        self.assertEqual(
            replenishment_date,
            pd.Timestamp("2026-03-07"),
        )

    def test_one_replenishment(self):
        df = pd.DataFrame(
            {
                "target_date": pd.to_datetime(
                    [
                        "2026-03-06",
                        "2026-03-07",
                        "2026-03-08",
                    ]
                ),
                "inventory_predicted_qty": [
                    300.0,
                    400.0,
                    200.0,
                ],
            }
        )

        result, replenishment_date = calculate_inventory(
            df,
            initial_inventory=1000,
            safety_stock=300,
            replenishment_qty=500,
        )

        self.assertEqual(
            result["replenishment"].sum(),
            1,
        )

        self.assertEqual(
            replenishment_date,
            pd.Timestamp("2026-03-07"),
        )

    def test_day_7_inventory(self):
        df = pd.DataFrame(
            {
                "target_date": pd.to_datetime(
                    [
                        "2026-03-06",
                        "2026-03-07",
                        "2026-03-08",
                        "2026-03-09",
                        "2026-03-10",
                        "2026-03-11",
                        "2026-03-12",
                    ]
                ),
                "inventory_predicted_qty": [
                    100.0,
                    100.0,
                    100.0,
                    100.0,
                    100.0,
                    100.0,
                    100.0,
                ],
            }
        )

        result, replenishment_date = calculate_inventory(
            df,
            initial_inventory=1000,
            safety_stock=300,
            replenishment_qty=500,
        )

        day_7_inventory = result.iloc[-1][
            "inventory_after_replenishment"
        ]

        self.assertEqual(day_7_inventory, 800.0)


def run_tests():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestInventorySimulation
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    return result.wasSuccessful()


def main():
    parser = argparse.ArgumentParser(
        description="M4.4-M4.7 inventory simulation."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=SCRIPT_DIR / "local_outputs" / "forecast_7days_task4.2.csv",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=SCRIPT_DIR / "local_outputs" / "inventory_simulation_task4.4_to_4.7.csv",
    )

    parser.add_argument(
        "--initial-inventory",
        type=float,
        required=True,
    )

    parser.add_argument(
        "--safety-stock",
        type=float,
        required=True,
    )

    parser.add_argument(
        "--replenishment-qty",
        type=float,
        required=True,
    )

    parser.add_argument(
        "--run-tests",
        action="store_true",
    )

    args = parser.parse_args()

    if args.run_tests:
        print("M4.7 Automated Tests")
        print("=" * 60)

        if not run_tests():
            raise SystemExit(1)

        print()

    validate_parameters(
        args.initial_inventory,
        args.safety_stock,
        args.replenishment_qty,
    )

    input_path = args.input
    output_path = args.output

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}"
        )

    df = load_forecast(input_path)

    df = apply_inventory_forecast(df)

    result, replenishment_date = calculate_inventory(
        df,
        initial_inventory=args.initial_inventory,
        safety_stock=args.safety_stock,
        replenishment_qty=args.replenishment_qty,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)

    day_7_inventory = result.iloc[-1][
        "inventory_after_replenishment"
    ]

    print("Inventory Simulation")
    print("=" * 60)
    print(f"Forecast Origin       : {result.iloc[0]['forecast_origin']}")
    print(f"Model                 : {result.iloc[0]['model_name']}")
    print(f"Initial Inventory     : {args.initial_inventory}")
    print(f"Safety Stock          : {args.safety_stock}")
    print(f"Replenishment Qty     : {args.replenishment_qty}")

    if replenishment_date is not None:
        print(
            f"Replenishment Date    : "
            f"{replenishment_date.strftime('%Y-%m-%d')}"
        )
    else:
        print("Replenishment Date    : None")

    print(f"Day-7 Inventory       : {day_7_inventory:.2f}")
    print(f"Output                : {output_path}")
    print()
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
