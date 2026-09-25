# Milestone 3 - 7-Day Forecast CLI

## 1. 目的

Milestone 3 で選定した最終モデルを用いて、指定した forecast origin から将来7日間の需要予測をコマンドラインで実行できるようにする。

本 CLI は、モデル評価用のスクリプトではなく、実際の7日予測を再現可能な形で実行するための入口として使用する。

## 2. 使用モデル

最終モデルには以下を使用する。

- Model: Ridge Regression
- Alpha: 1.0
- Preprocessing: StandardScaler
- Pipeline: StandardScaler → Ridge

このモデルは Validation Set 上の比較結果に基づいて選定した。

Validation Set では、Ridge Regression が Random Forest Regressor および Gradient Boosting Regressor と比較して最も低い WAPE および MAE を示したため、最終モデルとして採用した。

Test Set はモデル選択やハイパーパラメータ調整には使用していない。

## 3. 入力

CLI は以下を入力として受け取る。

### 必須引数

- `--input`
  - M2 で生成した feature dataset の CSV パス
- `--forecast-origin`
  - 予測基準日
  - 形式: `YYYY-MM-DD`

### 任意引数

- `--output`
  - 予測結果をローカル CSV として保存する場合の出力先
- `--location-id` / `--storage-unit-id`
  - 出力契約に含める対象識別子（入力データに列がない場合は任意指定）

生成された CSV はローカル利用のみとし、Git には含めない。

## 4. 使用 Feature

Task 3.2 と同じ feature set を使用する。

### Calendar Features

- `weekday`
- `month`
- `is_weekend`

### Historical Demand Features

- `lag_1`
- `lag_7`
- `lag_14`
- `rolling_mean_7`
- `rolling_mean_14`
- `rolling_std_7`

### Target

- `daily_qty`

Feature definition は M2 で確定した定義を変更しない。

## 5. 実行方法

例:

```bash
python 3.forecasting/forecast_7days.py \
  --input 1.data_engineering/3.data_feature/v5_location_demo_storage_unit_demo_features.csv \
  --forecast-origin YYYY-MM-DD
```

ローカル CSV に保存する場合:

```bash
python 3.forecasting/forecast_7days.py \
  --input 1.data_engineering/3.data_feature/v5_location_demo_storage_unit_demo_features.csv \
  --forecast-origin YYYY-MM-DD \
  --output 3.forecasting/forecast_20260305.csv
```

## 6. 7日予測ロジック

forecast origin を `t` とした場合、以下の7日間を予測する。

- t+1
- t+2
- t+3
- t+4
- t+5
- t+6
- t+7

将来日付の calendar feature は target date から直接計算する。

一方、lag および rolling feature は future actual を使用せず、recursive forecasting により生成する。

### Recursive Forecasting

- t+1: t までの実績値を使用
- t+2: t+1 の予測値を一時的な履歴として使用
- t+3: t+1, t+2 の予測値を使用
- 同様に t+7 まで繰り返す

これにより、forecast origin 時点で利用できない未来の実績値を使用しない。

## 7. Leakage Control

以下を禁止している。

- forecast origin より未来の `daily_qty` の使用
- 将来 target date に対して事前計算された lag / rolling feature の直接利用
- forecast origin より未来の日付を training data に含めること

training window は必ず以下を満たす。

`date <= forecast_origin`

## 8. 学習時間・推論時間

CLI では以下を個別に計測する。

### Train Time

`Pipeline.fit()` に要した時間。

StandardScaler の fitting と Ridge Regression の fitting を含む。

### Inference Time

7日間の recursive forecasting に要した時間。

feature reconstruction および `model.predict()` を含む。

2024-12-30 を forecast origin とした合成データ検証では以下を確認した。

- Train Time: 0.002128 seconds
- Inference Time: 0.006588 seconds

実行環境により時間は変動する。

## 9. 実行結果

forecast origin:

`2024-12-30`

7日予測結果:

| Horizon | Target Date | Predicted Demand |
|---:|---|---:|
| 1 | 2024-12-31 | 478.94 |
| 2 | 2025-01-01 | 507.69 |
| 3 | 2025-01-02 | 513.28 |
| 4 | 2025-01-03 | 528.39 |
| 5 | 2025-01-04 | 565.66 |
| 6 | 2025-01-05 | 569.26 |
| 7 | 2025-01-06 | 485.04 |

7件の連続した予測結果が正常に生成された。

出力 CSV は `forecast_origin`, `target_date`, `horizon`, `location_id`, `storage_unit_id`, `model_name`, `predicted_qty` を保持する。

## 10. エラー処理

CLI では以下を検証する。

- input file の存在
- 必須 column の存在
- date の parse
- duplicate date
- `daily_qty` の存在
- forecast origin の有効性
- 十分な履歴データの存在
- training feature 内の NaN

異常がある場合は silent fallback を行わず、明示的なエラーを返す。

## 11. Git / Local Data Rule

CLI 自体および本 Markdown は Git に含めてよい。

一方、以下は Git に含めない。

- forecast output CSV
- raw data
- processed data
- feature dataset
- prediction CSV
- schedule CSV

Git submission では CSV = 0 とする。

## 12. 検証結果

以下を確認した。

- `py_compile`: PASS
- runtime: PASS
- 7 predictions generated: Yes
- horizons 1～7: Yes
- target dates consecutive: Yes
- future actual usage: No
- recursive forecasting: Yes
- Ridge alpha = 1.0: Yes
- train time recorded: Yes
- inference time recorded: Yes
- hard-coded user absolute path: No

## 13. 結論

Validation Set の結果に基づいて選定した Ridge Regression を使用し、forecast origin 時点で利用可能な情報のみを用いた leakage-safe な7日需要予測 CLI を実装した。

CLI により、モデル学習から recursive 7-day forecasting までを再現可能な形で実行できることを確認した。
