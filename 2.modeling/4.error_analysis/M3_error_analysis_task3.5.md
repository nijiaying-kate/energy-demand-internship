# Milestone 3 - Error Analysis

## 1. 目的

Validation Set の予測結果を target_date 単位で集計し、誤差の大きい日を抽出する。曜日、販売量、データ品質を確認し、観測された誤差パターンを整理する。

## 2. Large-error days

| target_date | weekday | actual | mean_prediction | mean_absolute_error | max_absolute_error | forecast_count |
|---|---|---:|---:|---:|---:|---:|
| 2024-09-01 | Sunday | 422.03 | 537.65 | 115.62 | 115.62 | 1 |
| 2024-10-15 | Tuesday | 369.42 | 462.67 | 93.25 | 95.90 | 7 |
| 2024-11-29 | Friday | 566.55 | 477.44 | 89.11 | 90.36 | 7 |

## 3. Sales volume and weekday

| target_date | weekday | daily_qty | percentile context |
|---|---|---:|---|
| 2024-09-01 | Sunday | 422.03 | 2.5 percentile |
| 2024-10-15 | Tuesday | 369.42 | 0.3 percentile |
| 2024-11-29 | Friday | 566.55 | 81.2 percentile |

## 4. Data quality check

| target_date | daily_qty match | outlier flag |
|---|---|---|
| 2024-09-01 | Yes | No |
| 2024-10-15 | Yes | No |
| 2024-11-29 | Yes | No |

## 5. Observed error pattern

- The three largest-error days correspond to relatively high-demand days.
- The Ridge model consistently underpredicts demand on these dates across multiple forecast origins.
- The three dates occur on different weekdays: Wednesday, Thursday, and Monday.
- The three dates were not flagged in the existing outlier-day analysis.
- The available daily data does not show an obvious data-quality issue for these dates.

The observed results indicate a tendency toward underprediction on relatively high-demand days. However, the analysis does not establish that all high-demand days produce large errors or identify a specific external cause.