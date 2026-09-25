# Milestone 3 - Data Split / Evaluation Design

## 1. 目的

本設計では、Milestone 3 における時系列データ分割、training window、評価方法、および7日先予測の設計を定義する。

主な目的は以下のとおりである。

- 時系列の順序を維持した評価設計を定義する
- 未来情報が学習や特徴量生成に混入しないようにする
- Baseline と ML を同一条件で比較できるようにする
- Validation Set と Test Set の役割を明確に分離する
- forecast origin と forecast horizon の定義を明確にする
- 学習・評価処理を再現可能な形で設計する
- 後続の Python 実装が一貫した条件で実行できるようにする

本設計は設計文書であり、モデル学習、評価処理、7日先予測処理そのものの実装は本書では行わない。具体的な実装は、本設計に基づいて各 Task の Python スクリプトで実施する。

---

## 2. 入力データ

入力データには、Milestone 2 で生成した以下の特徴量データを使用する。

- `1.data_engineering/3.data_feature/v5_location_demo_storage_unit_demo_features.csv`

### 2.1 対象データ

| 項目 | 値 |
|---|---|
| Location ID | `location_demo` |
| Storage Unit | `2` |
| 対象データ | 日次需要量および生成済み特徴量 |
| 目的変数 | `daily_qty` |

### 2.2 主な特徴量

#### Calendar Features

- `weekday`
- `month`
- `is_weekend`

#### Lag Features

- `lag_1`
- `lag_7`
- `lag_14`

#### Rolling Features

- `rolling_mean_7`
- `rolling_mean_14`
- `rolling_std_7`

Milestone 2 の Feature Integrity Check により、Lag および Rolling の計算結果、データリークの有無、NaN 境界を確認済みである。

すべての特徴量が利用可能となる最初の日付は `YYYY-MM-DD` である。

---

## 3. Model-ready Data Period

### 3.1 実データの確認結果

v5 feature dataset を確認した結果、以下を確認した。

| 項目 | 値 |
|---|---|
| Original date range | YYYY-MM-DD ～ YYYY-MM-DD |
| First fully available feature date | YYYY-MM-DD |
| Last date | YYYY-MM-DD |
| Total rows | 730 |
| Model-ready rows | 716 |

### 3.2 Model-ready Period の定義

Lag および Rolling 特徴量では、データ開始直後は十分な過去履歴が存在しないため、初期行に `NaN` が発生する。

そのため、すべての主要特徴量が利用可能となる `YYYY-MM-DD` 以降を Model-ready Period とする。

- Model-ready Period: `YYYY-MM-DD` ～ `YYYY-MM-DD`
- `YYYY-MM-DD` ～ `YYYY-MM-DD` は、主要特徴量が完全ではないため M3 のモデル学習・評価対象から除外する。

### 3.3 結論

M3 以降の時系列モデルでは、`2023-01-15` ～ `2024-12-30` の 716 行を Model-ready Data として使用する。

---

## 4. 時系列分割の基本方針

本プロジェクトでは、random split を使用せず、時系列順を維持した Chronological Split を採用する。

### 4.1 Random Split を使用しない理由

時系列予測では、予測時点より未来の観測値を過去の学習データへ混入させないことが重要である。

Random split を使用すると、未来の観測値が学習データに含まれる可能性があり、実際の予測環境と異なる評価条件になる。

7日先需要予測では、各 forecast origin の時点までに利用可能な情報のみを使用して予測する必要がある。

したがって、本プロジェクトでは以下を組み合わせた評価設計を採用する。

- Chronological Dataset Split
- Expanding-window training
- Daily rolling forecast origin
- 7-day forecast horizon

### 4.2 Dataset と training_window の区別

本プロジェクトでは、静的 Dataset と動的な training_window を明確に区別する。

#### Dataset

静的に定義されたデータ区間を表す。

- Training Set
- Validation Set
- Test Set

#### training_window

各 forecast origin において、実際にモデル学習へ利用する過去履歴を表す。

training_window は forecast origin の進行に応じて変化し、forecast origin 時点までに利用可能なデータのみを含む。

Training Set と training_window は同一概念ではないため、両者を区別して扱う。

---

## 5. Dataset Split

本プロジェクトでは、Model-ready Data を以下の3つに分割する。

| Dataset | Start | End | Purpose |
|---|---|---|---|
| Training Set | YYYY-MM-DD | YYYY-MM-DD | 初期モデル学習 |
| Validation Set | YYYY-MM-DD | YYYY-MM-DD | モデル選択・主要パラメータ比較 |
| Test Set | YYYY-MM-DD | YYYY-MM-DD | 最終評価 |

### 5.1 分割理由

Validation Set と Test Set にそれぞれ約1年間を確保し、季節変動を含む期間でモデル性能を評価できるようにした。

- Training Set は可能な限り十分な学習履歴を確保する。
- Validation Set はモデル選択および主要パラメータ比較に使用する。
- Test Set は最終評価専用とし、モデル選択や主要パラメータの再調整には使用しない。
- 3つの Dataset は時系列順に連続している。
- Dataset 間に重複はない。
- Dataset 間に期間上の欠落はない。
- Random split は使用しない。

---

## 6. Training Set と training_window の定義

### 6.1 Training Set

Training Set は静的に定義された初期学習区間である。

- Start: `YYYY-MM-DD`
- End: `YYYY-MM-DD`

### 6.2 training_window

training_window は、各 forecast origin において実際に学習へ使用する過去データの範囲である。

以下のルールを適用する。

- forecast origin 時点までに実際に観測済みのデータのみを使用する。
- forecast origin より後のデータは使用しない。
- forecast origin の進行に応じて利用可能な履歴を追加する。
- 学習時点で利用できない未来情報を含めない。
- Dataset の静的な区間定義と、各予測時点における動的な学習履歴を区別する。

---

## 7. Expanding-window 設計

本プロジェクトでは、過去の観測データを追加しながら学習範囲を拡張する Expanding-window を採用する。

### 7.1 Validation Set 段階

Validation Set を用いる段階では、Training Set を初期学習範囲とする。

- 初期学習範囲: `YYYY-MM-DD` ～ `YYYY-MM-DD`
- forecast origin の進行に応じて、利用可能な過去データを training_window に追加する。
- forecast origin より後のデータは使用しない。
- Validation Set の結果はモデル選択および主要パラメータ比較に使用する。

### 7.2 Test Set 段階

Test Set に入る前に、以下の条件を固定する。

- model type
- feature set
- main hyperparameters
- forecasting strategy
- evaluation rules

Test Set の各 forecast origin では、forecast origin までに実際に観測されたデータを training_window に追加する。

ただし、Test Set の結果を用いて以下を行ってはならない。

- モデル再選択
- 主要パラメータの再調整
- feature set の再設計
- forecasting strategy の変更
- 評価ルールの変更

---

## 8. Forecast Origin と7日予測

### 8.1 Forecast Origin の定義

forecast origin は、予測基準日 `t` を表す。

本プロジェクトでは以下のように定義する。

- forecast origin = `t`
- forecast horizon = `1` ～ `7`
- prediction targets = `t+1` ～ `t+7`

すなわち、予測基準日の翌日から7日間を予測対象とする。

### 8.2 Daily Rolling Origin

Daily rolling origin では、forecast origin を日単位で更新する。

- 各予測時点に対して forecast origin を設定する。
- 次の日には新しい forecast origin を設定する。
- 同一の `target_date` が複数の forecast origin に対応する場合がある。
- 各予測結果には `forecast_origin`、`target_date`、`horizon` を保持する。
- forecast origin 間で同一 target date が存在すること自体は重複エラーではない。

### 8.3 7日予測の定義

「7日先予測」は、`t+1` のみを予測することではなく、`t+1` ～ `t+7` の7日間を予測することを意味する。

```text
Forecast origin: t

Horizon 1 → t+1
Horizon 2 → t+2
Horizon 3 → t+3
Horizon 4 → t+4
Horizon 5 → t+5
Horizon 6 → t+6
Horizon 7 → t+7
```

## 9. Feature Availability と Data Leakage Control

### 9.1 Calendar Features

以下の Calendar Features は対象日の既知のカレンダー情報から生成する。

- `weekday`
- `month`
- `is_weekend`

これらは対象日のカレンダー情報として事前に把握できるため、予測時点で利用可能な情報として扱う。

### 9.2 Historical Demand Features

以下の特徴量は対象日より前の販売実績のみを使用する。

- `lag_1(t) = daily_qty(t-1)`
- `lag_7(t) = daily_qty(t-7)`
- `lag_14(t) = daily_qty(t-14)`
- `rolling_mean_7(t)` = `t` より前の7日間の平均
- `rolling_mean_14(t)` = `t` より前の14日間の平均
- `rolling_std_7(t)` = `t` より前の7日間の標準偏差

当日の `daily_qty(t)` および未来の `daily_qty` は特徴量生成に使用しない。

### 9.3 7日予測における Leakage Risk

7日先予測では、未来の日付について事前に計算された特徴量をそのまま使用すると、未来の実績値が混入する可能性がある。

例えば forecast origin が `t` の場合、

- `lag_1(t+2) = daily_qty(t+1)`
- `rolling_mean_7(t+2)` は `t+1` を含む過去期間から計算される

が、`daily_qty(t+1)` は `t` 時点では未観測である。

したがって、予測基準日 `t` の時点で未来の実績値を直接使用して `t+2` 以降の特徴量を作成することは Data Leakage となる。

### 9.4 Leakage Control の基本ルール

以下のルールを適用する。

1. Calendar Features は対象日に対して事前に利用可能な情報から生成する。
2. Historical Demand Features は予測時点までに利用可能な情報のみを使用する。
3. forecast origin より後の実績 `daily_qty` は直接使用しない。
4. 7日先予測では、未来日に対する特徴量を必要に応じて予測値から再帰的に生成する。
5. 事前計算済みの未来日付の特徴量を Dataset 全体からそのまま取得しない。
6. forecast origin と horizon の関係を明示的に管理する。

---

## 10. Validation Set の用途

Validation Set は、モデル選択および主要パラメータ比較のために使用する。

主な用途は以下のとおりである。

- Model comparison
- Main hyperparameter comparison
- Forecasting strategy の確認
- Evaluation design の確認

Validation Set の結果に基づいてモデルおよび主要パラメータを選択する。

ただし、Validation Set に対して過度な反復調整を行い、その結果だけに適合したモデルにならないよう注意する。

---

## 11. Test Set の用途と隔離

Test Set は、最終的なモデル性能を評価するための holdout data として使用する。

Test Set に入る前に、以下を固定する。

- model type
- feature set
- main hyperparameters
- forecasting strategy
- evaluation rules

Test Set の結果は、最終性能確認のためにのみ使用する。

Test Set の結果を用いて以下を行わない。

- モデル再選択
- 主要パラメータ再調整
- Feature 再設計
- Forecasting Strategy の変更
- 評価ルールの変更
- 反復的なモデル改善

---

## 12. Baseline / ML 共通評価条件

Baseline と ML の比較可能性を確保するため、以下の条件を共通化する。

- 同一の forecast origin
- 同一の forecast horizon
- 同一の target date
- 同一の evaluation partition
- 同一定義の評価指標

### 12.1 共通評価指標

- MAE
- RMSE
- R²
- WAPE

### 12.2 共通原則

- 予測対象は7日先需要
- forecast origin は日単位で設定する
- 学習・評価期間は同一の時系列分割基準に従う
- Baseline と ML は同一条件で比較する
- 評価結果にはモデル名、評価期間、horizon、seed 等のメタデータを記録する

---

## 13. Forecast Result の保持

各予測結果には、以下の情報を保持する。

- `forecast_origin`
- `target_date`
- `horizon`
- model
- actual value
- predicted value

同一の `target_date` に複数の forecast origin が存在する場合も、それぞれ独立した予測結果として保持する。

これにより、forecast origin ごとの予測性能および horizon ごとの誤差を追跡できる。

---

## 14. Dataset Split の検証項目

実装時には、以下の条件を自動的に確認する。

### 14.1 Dataset Boundary

- Training Set の開始日・終了日が設計どおりであること
- Validation Set の開始日・終了日が設計どおりであること
- Test Set の開始日・終了日が設計どおりであること

### 14.2 Dataset Continuity

- Dataset 間に予期しない期間重複がないこと
- Dataset 間に予期しない期間欠落がないこと
- 各 Dataset の日付が時系列順に並んでいること

### 14.3 Forecast Schedule

- forecast origin < target date
- horizon が `1` ～ `7` であること
- target date が forecast origin + horizon 日となっていること
- 同一 forecast origin 内で target date が適切に連続していること
- 未来データが forecast origin より前の学習データに混入していないこと

---

## 15. ローカル生成物

Task 3.3 の実装では、以下の Dataset および Forecast Schedule を生成する。

- `training_set.csv`
- `validation_set.csv`
- `test_set.csv`
- `validation_forecast_schedule.csv`
- `test_forecast_schedule.csv`

これらは M3 のモデル学習および評価処理で利用する中間データとして保存する。

各 CSV の構造および期間は、本設計書の Dataset Split と Forecast Origin の定義に従う。

---

## 16. 採用する最終評価設計

本プロジェクトでは、以下の評価設計を採用する。

| 項目 | 採用方式 |
|---|---|
| Model-ready Period | YYYY-MM-DD ～ YYYY-MM-DD |
| Training Set | YYYY-MM-DD ～ YYYY-MM-DD |
| Validation Set | YYYY-MM-DD ～ YYYY-MM-DD |
| Test Set | YYYY-MM-DD ～ YYYY-MM-DD |
| Data Split | Chronological Split |
| Window Strategy | Expanding-window |
| Forecast Origin | Daily rolling origin |
| Forecast Horizon | t+1 ～ t+7 |
| Model Selection | Validation Set |
| Final Evaluation | Test Set |
| Leakage Control | forecast origin 時点で利用可能な情報のみを使用 |
| Future Demand Handling | 未来の実績 `daily_qty` を直接使用しない |

---

## 17. 実装時の基本ルール

本設計に基づく Python 実装では、以下の原則を守る。

- 入力データと出力データのパスはプロジェクト相対パスまたは CLI 引数で指定する。
- forecast origin より未来のデータを学習に使用しない。
- Validation Set と Test Set を混同しない。
- Test Set の結果をモデル選択に使用しない。
- 同一条件で Baseline と ML を比較する。
- forecast origin、target date、horizon を明示的に保持する。
- 予測時点で利用できない未来実績を特徴量として使用しない。
- 生成した Dataset および Forecast Schedule の整合性を検証する。
- 実装時のデータ処理、モデル学習、評価条件は本設計書と一致させる。

---

## 18. 最終結論

本プロジェクトでは、Model-ready Data を Training Set、Validation Set、Test Set に時系列順で分割し、Chronological Split を採用する。

Training Set は初期学習区間として定義し、各 forecast origin における学習履歴は Expanding-window により過去側から拡張する。

Validation Set はモデル選択および主要パラメータ比較に使用し、Test Set は最終評価専用とする。Test Set の結果を用いたモデル再選択や主要パラメータ再調整は行わない。

forecast origin `t` に対して `t+1` ～ `t+7` を予測対象とし、Daily rolling origin により予測基準日を日単位で更新する。

また、7日先予測では forecast origin より後の未来実績 `daily_qty` を直接特徴量として使用せず、予測時点で利用可能な情報から必要な特徴量を再計算することで Data Leakage を防止する。

以上の設計により、Baseline と ML を同一条件で比較可能な時系列評価環境を構築し、実際の予測環境に近い条件で再現可能なモデル評価を実施する。
