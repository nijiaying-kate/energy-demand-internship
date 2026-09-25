# Feature Integrity Check

## 1. 対応タスク

- Task 2.3 データリーク確認
- Task 2.4 特徴量生成処理のテスト

## 2. 確認目的

Task 2.2 で生成した特徴量について、参照時点の妥当性と生成処理の正しさを確認する。

本確認では、データリーク、Lag計算、Rolling計算、Availability / NaN境界を対象とする。

## 3. 確認方法

### 3.1 データリーク
Lag / Rolling を期待式から再計算し、対象日当日および対象日以降の `daily_qty` が使用されていないことを確認した。

### 3.2 Lag計算
`shift(1)`, `shift(7)`, `shift(14)` と全量照合した。

### 3.3 Rolling計算
`shift(1).rolling(...)` と全量照合した。

### 3.4 Availability
NaN 数と最初の完全行を確認した。

## 4. 確認結果

| Check | Target | Mismatches | Result |
|---|---|---:|---|
| Data Leakage | Lag / Rolling reference timing | 0 | PASS |
| Lag Calculation | lag_1 / lag_7 / lag_14 | 0 | PASS |
| Rolling Calculation | rolling_mean_7 / rolling_mean_14 / rolling_std_7 | 0 | PASS |
| Availability | NaN boundary | 0 | PASS |

- Input: `v5_location_demo_storage_unit_demo_features.csv`（本ディレクトリ内のローカル生成物）
- Total rows: 730
- Total mismatches: 0
- First complete row: 2023-01-15
- Overall: PASS

## 5. 必要な詳細

- lag_1: checked_rows=729, mismatch_count=0, result=PASS
- lag_7: checked_rows=723, mismatch_count=0, result=PASS
- lag_14: checked_rows=716, mismatch_count=0, result=PASS
- rolling_mean_7: checked_rows=723, mismatch_count=0, result=PASS
- rolling_mean_14: checked_rows=716, mismatch_count=0, result=PASS
- rolling_std_7: checked_rows=723, mismatch_count=0, result=PASS

| Feature | Expected NaN | Actual NaN | Result |
|---|---:|---:|---|
| lag_1 | 1 | 1 | PASS |
| lag_7 | 7 | 7 | PASS |
| lag_14 | 14 | 14 | PASS |
| rolling_mean_7 | 7 | 7 | PASS |
| rolling_mean_14 | 14 | 14 | PASS |
| rolling_std_7 | 7 | 7 | PASS |

- 最初に全ての特徴量が利用可能となる日付: Expected=2023-01-15 / Actual=2023-01-15 / Result=PASS

## 6. 結論

データリーク、Lag計算、Rolling計算、Availability の全項目で問題がないことを確認した。

- Task 2.3: PASS
- Task 2.4: PASS
