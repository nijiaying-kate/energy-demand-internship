# Milestone 1 - Data Quality Report

## 1. 対象データ

- Source file: location_demo_transactions.csv
- location_id: location_demo
- storage_unit_id: 2
- Target: t_qty
- Period: 2023-01-01 to 2024-12-30
- Number of daily records: 730

## 2. 目的変数の選定

`t_qty` と `t_pure_qty` の値を比較した結果、対象データでは両者が同一であることを確認したため、目的変数には `t_qty` を採用した。

## 3. 日次集計

`t_start_datetime` を日付単位に変換し、対象データを日付ごとに集計して `daily_qty` を生成した。

## 4. 品質確認結果

| Check | Result |
|---|---:|
| missing_date | 0 |
| missing_qty | 0 |
| duplicate_date | 0 |
| negative_qty | 0 |
| zero_qty | 0 |
| invalid_qty | 0 |
| missing_calendar_dates | 0 |
| outlier_iqr | 1 |

## 5. 処理結果

- raw_transaction_rows: 2190
- filtered_transaction_rows: 2190
- filtered_out_rows: 0
- daily_record_rows: 730
- filled_rows: 0
- corrected_rows: 0

対象 location_id / storage_unit_id によるフィルタリングを実施した。IQR で検出した外れ値は削除・補正していない。

## 6. 結論

データ品質確認を完了し、後続の分析に利用可能な日次需要データを生成した。
