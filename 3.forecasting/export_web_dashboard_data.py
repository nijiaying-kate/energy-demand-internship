#!/usr/bin/env python3
"""Export local forecasting artifacts to the Web dashboard JSON contract."""

from __future__ import annotations

import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FORECAST_CSV = PROJECT_ROOT / "3.forecasting" / "local_outputs" / "forecast_7days_task4.2.csv"
COMPARISON_CSV = PROJECT_ROOT / "2.modeling" / "3.model_evaluation" / "local_outputs" / "model_comparison_summary.csv"
OUTPUT_JSON = PROJECT_ROOT / "4.web_app" / "public" / "data" / "dashboard-data.json"


def main() -> None:
    with FORECAST_CSV.open(encoding="utf-8", newline="") as file:
        forecast_rows = list(csv.DictReader(file))
    if len(forecast_rows) != 7:
        raise ValueError(f"Expected exactly 7 forecast rows, got {len(forecast_rows)}.")

    with COMPARISON_CSV.open(encoding="utf-8", newline="") as file:
        comparison_rows = list(csv.DictReader(file))
    ridge = next((row for row in comparison_rows if row["model"] == "Ridge"), None)
    if ridge is None:
        raise ValueError("Ridge model metrics are missing from comparison summary.")

    first = forecast_rows[0]
    payload = {
        "forecastOrigin": first["forecast_origin"],
        "locationId": first["location_id"],
        "storageUnitId": first["storage_unit_id"],
        "modelName": first["model_name"],
        "metrics": {
            "validationWape": float(ridge["validation_WAPE"]),
            "testWape": float(ridge["test_WAPE"]),
            "testMae": float(ridge["test_MAE"]),
        },
        "forecast": [
            {"targetDate": row["target_date"], "predictedQty": float(row["predicted_qty"])}
            for row in forecast_rows
        ],
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Web dashboard data written to: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
