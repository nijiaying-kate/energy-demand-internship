# Milestone 3 - ML Model Definition

## 1. 目的

M2 で確定した特徴量を使用し、同一の expanding-window および daily rolling origin 条件のもとで複数の機械学習モデルを比較する。

モデル選択は Validation Set の WAPE を第一評価指標とし、WAPE が同値の場合は MAE を比較する。Test Set は最終評価専用とし、モデル選択およびパラメータ調整には使用しない。

---

## 2. 対象モデル

比較対象モデルと固定設定は以下の通りである。

| Model Family | Fixed Configuration |
|---|---|
| Ridge Regression | `StandardScaler` → `Ridge(alpha=1.0)` |
| Random Forest | `random_state=42`, `n_jobs=-1`, `n_estimators=300`, `max_depth=None`, `min_samples_leaf=2`, `max_features=0.8` |
| Gradient Boosting | `random_state=42`, `n_estimators=150`, `learning_rate=0.05`, `max_depth=3`, `min_samples_leaf=3` |

全モデルで使用する特徴量は以下の10項目とする。

- `weekday`
- `month`
- `is_weekend`
- `lag_1`
- `lag_7`
- `lag_14`
- `rolling_mean_7`
- `rolling_mean_14`
- `rolling_std_7`

目的変数は `daily_qty` とする。

---

## 3. 時系列学習条件

各 forecast origin において、forecast origin 以前に利用可能なデータのみを学習に使用する。

### 3.1 Expanding-window

Training data は forecast origin に応じて拡張される。

```text
training data: date <= forecast_origin
```


### 3.2 Daily rolling origin

Forecast origin を1日ずつ前進させ、各 origin でモデルを再学習する。

各 forecast origin では、対象モデルを `fit()` した後、将来の予測対象に対して予測を実行する。

---

## 4. 7日先予測

各 forecast origin では、以下の7つの horizon を対象とする。

- `horizon = 1`
- `horizon = 2`
- `horizon = 3`
- `horizon = 4`
- `horizon = 5`
- `horizon = 6`
- `horizon = 7`

予測対象日は以下のように定義する。

`target_date = forecast_origin + horizon`

予測に使用する特徴量は、forecast origin 時点で利用可能な履歴から生成する。

---

## 5. Leakage Control

時系列予測で未来情報が学習・予測処理に混入しないよう、以下のルールを適用する。

- training data は `date <= forecast_origin` に限定する。
- forecast origin より後の実績値を学習データとして使用しない。
- 予測対象日の実績値を、その対象日の予測特徴量生成に使用しない。
- Test Set の実績値をモデル選択やパラメータ調整に使用しない。
- Forecast Schedule と実績データの日時関係を維持する。

Recursive Forecasting では、予測時点で生成された予測値を temporary history に追加し、後続 horizon の特徴量生成に使用する。

これにより、将来実績値ではなく、予測時点で利用可能な情報のみを用いて7日間の予測を行う。

---

## 6. Validation によるモデル選択

モデル選択は Validation Set のみを使用して行う。

評価指標の優先順位は以下の通りとする。

1. WAPE
2. MAE

WAPE が小さいモデルを選択し、WAPE が同値の場合は MAE が小さいモデルを選択する。

Validation における比較の結果、最終モデルには以下を採用する。

`Ridge Regression (alpha=1.0)`

StandardScaler を前処理として適用し、Ridge Regression を実行する。

---

## 7. Test Set の扱い

Test Set は最終評価専用とする。

Test Set に対して以下の処理は行わない。

- モデル選択
- ハイパーパラメータ調整
- Validation 結果に基づく追加のモデル変更

Validation で固定した最終モデルおよび設定をそのまま Test Set に適用し、未知データに対する予測性能を評価する。

---

## 8. Partition 境界における予測

Validation Set および Test Set の partition 境界付近では、7日先のすべての target date が同一 partition 内に存在するとは限らない。

そのため、partition 最後の6 forecast origin については、各 partition 内で利用可能な horizon のみを予測対象として保持する。

この処理により、partition を越えた未来実績を使用することを防ぎ、各予測タスクを実際に利用可能な範囲で評価する。

指標は forecast task 単位で集計し、各 partition の365個の forecast origin がすべて完全な7日間予測を持つものとして扱わない。

---

## 9. 時間計測

各モデルおよび各 partition について、以下の処理時間を記録する。

| Metric | Definition |
|---|---|
| `train_seconds` | 各 forecast origin における `fit()` の合計時間 |
| `inference_seconds` | 各 forecast origin における `predict()` の合計時間 |

Timing Summary は local-only の出力として保存し、モデルの学習および推論に要した時間を記録する。

---

## 10. 出力と比較条件

Validation および Test では、各モデルについて同一の forecast schedule を使用する。

これにより、モデル間で以下の条件を統一する。

- forecast origin
- target date
- horizon
- actual value
- prediction
- evaluation metric

同一の予測対象と評価条件を使用することで、モデル性能を比較可能な状態にする。

---

## 11. 結論

本 Task 3.2 では、M2 で確定した10個の特徴量を使用し、Ridge Regression、Random Forest、Gradient Boosting の3モデルを同一の時系列条件で比較する設計とした。

Expanding-window および daily rolling origin を採用し、forecast origin より後の実績値を学習に使用しないことで、時系列予測における future leakage を防止する。

モデル選択は Validation Set の WAPE、同値時は MAE に基づいて行い、最終モデルとして Ridge Regression（`alpha=1.0`）を固定する。

Test Set はモデル選択から分離し、固定した最終モデルの最終評価にのみ使用する。
