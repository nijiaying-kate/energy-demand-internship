# Milestone 3 - Baseline Validation

## 1. 目的

Seasonal Naive / Previous-week Same Weekday を Baseline として実装し、
Validation / Test の schedule に対して leakage のない予測を実行する。

## 2. Baseline Rule

- prediction = actual(target_date - 7 days)
- source_date <= forecast_origin
- future actual は使用しない
- inference に training は不要

## 3. Prediction Counts

- Validation prediction count: 616
- Test prediction count: 189

## 4. Timing

| Partition | Train seconds | Inference seconds |
|---|---:|---:|
| Validation | 0.000000 | 0.021133 |
| Test | 0.000000 | 0.007777 |

## 5. Result Summary

- Validation schedule coverage: PASS
- Test schedule coverage: PASS
- no future leakage: PASS
- no missing actual/prediction: PASS
- partition crossing: PASS (validated in Task 3.3)

## 5. 結論

Seasonal Naive Baseline は、7日先予測の安全な参照モデルとして適用できる。
