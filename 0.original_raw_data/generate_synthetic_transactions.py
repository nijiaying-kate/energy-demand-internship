"""Generate an independently created public demonstration dataset.

This generator uses invented rules and a fixed seed.  It does not read, sample,
transform, or approximate any private operational dataset.
"""
from __future__ import annotations

import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path


OUTPUT = Path(__file__).with_name("location_demo_transactions.csv")
SEED = 20250301


def main() -> None:
    rng = random.Random(SEED)
    start = datetime(2023, 1, 1)
    rows: list[dict[str, object]] = []
    for day_index in range(730):
        day = start + timedelta(days=day_index)
        weekly = [0, 12, 18, 28, 45, 85, 70][day.weekday()]
        yearly = 35 * math.sin(2 * math.pi * day.timetuple().tm_yday / 365)
        daily_total = max(120, 480 + weekly + yearly + rng.gauss(0, 35))
        weights = [0.22 + rng.random() * 0.1, 0.31 + rng.random() * 0.1, 0.37 + rng.random() * 0.1]
        weight_sum = sum(weights)
        for transaction_index, weight in enumerate(weights):
            qty = round(daily_total * weight / weight_sum, 2)
            rows.append({
                "t_location_id": "location_demo",
            "t_storage_unit_id": 2,
                "t_start_datetime": (day + timedelta(hours=7 + transaction_index * 5)).isoformat(),
                "t_qty": qty,
                "t_pure_qty": qty,
            })
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Synthetic transactions written to {OUTPUT}")


if __name__ == "__main__":
    main()
