# Milestone 3 - Data Split Validation

## 1. 目的

Task 3.3 の時系列データ分割と評価スケジュールを実装し、
Validation / Test の境界と future leakage のない設計を確認する。

## 2. 入力データ

- input file: `1.data_engineering/3.data_feature/v5_location_demo_storage_unit_demo_features.csv`
- model-ready period: 2023-01-15 ～ 2024-12-30
- model-ready rows: 716
- feature schema: date, daily_qty, weekday, month, is_weekend, lag_1, lag_7, lag_14, rolling_mean_7, rolling_mean_14, rolling_std_7

## 3. Dataset Split Result

| Dataset | Start | End | Rows |
|---|---|---|---:|
| Training Set | 2023-01-15 | 2024-08-31 | 595 |
| Validation Set | 2024-09-01 | 2024-11-30 | 91 |
| Test Set | 2024-12-01 | 2024-12-30 | 30 |

## 4. Forecast Schedule

- Validation: first origin = 2024-08-31, last origin = 2024-11-29, origins = 91, tasks = 616
- Test: first origin = 2024-11-30, last origin = 2024-12-29, origins = 30, tasks = 189

## 5. Expanding-window Rule

- training_window は forecast_origin 以前の実績のみを対象とする
- forecast_origin 以後のデータは training_window の候補としない
- Validation と Test の評価期間はそれぞれ独立に管理する

## 6. 7-Day Forecast / Leakage Control

- forecast schedule は未来実績 feature を保持しない
- evaluation_partition, forecast_origin, target_date, horizon のみを保持する
- period 外の target_date を含めない
- 7日先予測では horizon を 1 ～ 7 の範囲で管理する

## 7. Validation Results

### Dataset checks

| Check | Result |
|---|---|
| model_ready_rows_match_expectation | PASS |
| split_total_equals_model_ready_rows | PASS |
| training_range_correct | PASS |
| validation_range_correct | PASS |
| test_range_correct | PASS |
| no_overlap_between_splits | PASS |
| no_gap_between_splits | PASS |
| all_dates_ascending | PASS |
| no_duplicate_date_within_split | PASS |

### Validation schedule checks

| Check | Result |
|---|---|
| forecast_origin_lt_target_date | PASS |
| horizon_matches_delta | PASS |
| horizon_in_range_1_to_7 | PASS |
| targets_in_partition | PASS |
| no_partition_crossing | PASS |
| no_duplicate_exact_tasks | PASS |
| no_future_data_eligible_violation | PASS |

### Test schedule checks

| Check | Result |
|---|---|
| forecast_origin_lt_target_date | PASS |
| horizon_matches_delta | PASS |
| horizon_in_range_1_to_7 | PASS |
| targets_in_partition | PASS |
| no_partition_crossing | PASS |
| no_duplicate_exact_tasks | PASS |
| no_future_data_eligible_violation | PASS |

## 8. 結論

Task 3.3 のデータ分割および評価スケジュールが設計どおり構築され、
未来情報を使用しない評価条件を確認した。
