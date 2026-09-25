# Energy Demand Internship
## インターンシップ成果報告

**公開版ステータス：M1〜M5 完了 / 独立合成データ・静的 Web デモを含む**

### 今回のゴール

拠点の販売実績データから、

> **今後7日間の需要を予測し、在庫・補給判断につなげる**

一連の処理を構築する。

---

## 全体開発フロー

```text
Raw Data
   ↓
[M1] データ理解・前処理
   ↓
日次需要データ
   ↓
[M2] EDA・特徴量生成
   ↓
学習用データ
   ↓
[M3] モデル構築・評価・選択
   ↓
7日需要予測モデル
   ↓
[M4] 7日予測・在庫シミュレーション
   ↓
補給判断
```

### 今回の実装範囲

| Milestone | 内容 | 状態 |
|---|---|---|
| M1 | データ理解・前処理 | 完了 |
| M2 | EDA・特徴量生成 | 完了 |
| M3 | モデル構築・評価 | 完了 |
| M4 | 7日予測・在庫判定 | 完了 |

---

# Milestone 1
## データ理解・前処理

### 1. 目的

Raw Dataをそのままモデルに入力するのではなく、

> **予測対象を明確にし、モデルで利用できる日次需要データを作る**

ことを目的とした。

### 2. 予測対象

| 項目 | 設定 |
|---|---|
| location_id | `location_demo` |
| storage_unit_id | `2` |
| Target | `t_qty` |
| 粒度 | 日次 |
| Forecast Horizon | 7日 |

#### なぜ日次？

今回の最終目的が **「翌日から7日間の需要予測」** であるため、取引単位のデータを日次需要単位へ集約した。

### 3. Target Variableの確認

候補：

- `t_qty`
- `t_pure_qty`

実データを比較した結果、対象データでは両者が同一であることを確認した。

そのため、`t_qty` をTargetとして採用した。

> 項目名だけで決めず、実データを確認してから目的変数を決定する。

### 4. Data Quality Check

日次集計前に以下を確認した。

- 必須列
- データ型
- 欠損
- 完全一致重複
- 負値
- 0販売
- 極端値
- データ期間
- レコード数
- 拠点数
- タンク数

特に重複データについては、同一販売実績を二重計上する可能性があるため、完全一致行を処理してから日次集計する構成とした。

### 5. M1 Processing Flow

```text
Raw Data
   ↓
必須列・型確認
   ↓
対象Location / Storage Unit抽出
   ↓
Data Quality Check
   ↓
完全一致重複処理
   ↓
日次集計
   ↓
daily_qty
```

### 6. M1 Output

モデル開発の基礎となる **日次需要データ** を作成した。

---

# Milestone 2
## EDA・特徴量生成

### 1. 目的

M1で作成した日次データから、

> **需要の時間的な特徴を理解し、予測に利用できる情報へ変換する**

ことを目的とした。

### 2. EDA

確認した主な観点：

- 時系列推移
- 曜日別需要
- 月別需要

EDAはグラフを作ること自体を目的とせず、後続の特徴量設計・Baseline・モデル設計の根拠として利用した。

```text
需要データを理解
      ↓
時間的パターンを確認
      ↓
特徴量設計
      ↓
Baseline / ML Model
```

### 3. Feature Engineering

基本方針：

> **予測時点で取得できる情報だけを使用する**

主に以下を利用した。

- 過去の販売実績
- 曜日・月などのカレンダー情報

過去の需要パターンや曜日周期などを将来需要の予測に利用するためである。

### 4. Data Leakage Check

未来の販売実績がFeatureに混入すると、評価精度が不自然に高くなり、実運用では再現できない。

そのため、各予測時点より未来の販売実績を使用しないことを確認した。

### 5. M2 Processing Flow

```text
Daily Data
   ↓
EDA
   ↓
Feature Engineering
   ↓
Leakage Check
   ↓
Integrity Check
   ↓
Feature Generation Test
   ↓
Modeling Dataset
```

### 6. M2 Output

**時系列モデル学習に利用できる特徴量データ** を作成した。

---

# Milestone 3
## モデル構築・評価・選択

### 1. 目的

一つのモデルを最初から採用するのではなく、

> **異なる予測方法を同じ条件で比較し、Validation結果からモデルを選択する**

ことを目的とした。

### 2. Baseline

Machine Learningモデルの性能を判断する比較基準としてBaselineを作成した。

複雑なモデルで一定の精度が得られても、単純な予測方法から改善していなければ、MLモデルを導入するメリットを判断できないためである。

今回のデータでは曜日による需要パターンも考えられるため、前週同曜日の販売実績を利用するSeasonal Naive系のBaselineを比較対象とした。

```text
Simple Baseline
       ↓
Machine Learning
       ↓
本当に改善したか比較
```

### 3. Machine Learning Models

比較したモデル：

| Model | 選択理由 |
|---|---|
| Ridge Regression | シンプルな線形モデル・正則化 |
| Random Forest | 非線形関係・Feature Interaction |
| Gradient Boosting | 誤差を逐次改善するTree Model |

最初から複雑なモデルだけを使用せず、異なる特性を持つモデルを同一条件で比較した。

### 4. Time-Series Split

Random Splitは使用せず、時間順に以下へ分割した。

```text
Past                                    Future
──────────────────────────────────────────→

[ Training ] → [ Validation ] → [ Test ]
```

Random Splitでは未来データがTraining側に入る可能性があり、実際の「過去から未来を予測する」条件と異なるためである。

### 5. Walk-forward / Expanding-window

各予測時点までに利用可能な過去データを使用し、学習可能なデータを順次増やしながら将来を評価する方式とした。

```text
Train ──────────→ Predict
Train ─────────────→ Predict
Train ────────────────→ Predict
```

未来情報を学習に利用せず、実運用に近い条件で評価することを目的とした。

### 6. Evaluation Metrics

| 指標 | 確認したいこと |
|---|---|
| MAE | 平均的にどの程度外れるか |
| RMSE | 大きな誤差が発生していないか |
| R² | 全体変動をどの程度説明できるか |
| WAPE | 総需要に対して誤差がどの程度か |
| Training Time | 学習コスト |
| Inference Time | 推論コスト |

モデル選択ルール：

- **Primary：WAPE**
- **Secondary：MAE**

WAPEは需要規模に対する誤差割合として解釈しやすく、MAEは実際の販売量と同じ単位で誤差を確認できるためである。

### 7. Validation / Testの役割分離

```text
Training
   ↓
モデル学習

Validation
   ↓
モデル比較・選択

Test
   ↓
最終評価のみ
```

Test結果を見てモデルを変更すると、Test Set自体がモデル選択に利用されてしまう。

そのため、モデル選択はValidation Setのみで行い、Test Setは独立した最終評価データとして保持した。

### 8. Model Comparison

#### Validation

| Model | MAE | RMSE | R² | WAPE |
|---|---:|---:|---:|---:|
| Ridge | **29.92** | **36.46** | **0.3267** | **6.2094%** |
| Gradient Boosting | 30.59 | 36.85 | 0.3125 | 6.3475% |

事前に設定したValidationのモデル選択ルールに基づき、**Ridge Regressionを採用**した。

#### Final Test Evaluation：Ridge Regression

| Metric | Result |
|---|---:|
| MAE | 30.37 |
| RMSE | 38.67 |
| R² | 0.3751 |
| WAPE | 5.9043% |

TestではGradient Boostingの一部指標がRidgeより良かったが、Test結果を見てモデルを変更せず、Validationで決定したRidgeを最終モデルとして維持した。

### 9. Error Analysis

平均指標だけでは「いつ大きく外したのか」が分からないため、予測誤差が大きい日を抽出し、ActualとPredictionを確認した。

```text
Prediction Results
       ↓
Absolute Error
       ↓
Large-error Days
       ↓
Actual vs Prediction
```

モデルの平均性能だけでなく、失敗ケースも確認できる構成とした。

### 10. M3 Output

```text
Baseline
   ↓
ML Models
   ↓
Time-Series Validation
   ↓
Model Evaluation
   ↓
Error Analysis
   ↓
Model Comparison
   ↓
Ridge Regression
```

**7日需要予測に使用するモデルを決定した。**

---

# Milestone 4
## 7日需要予測・在庫判定

### 1. 目的

M3までのモデル評価を、実際の業務判断につながる形へ変換することを目的とした。

```text
Selected Model
      ↓
7-Day Forecast
      ↓
Inventory Simulation
      ↓
Safety Stock Check
      ↓
Replenishment Decision
```

### 2. 7-Day Forecast

`forecast_origin`を指定し、その翌日から7日間の需要を予測する処理を実装した。

```text
Forecast Origin
      ↓
Day 1 → Day 2 → Day 3 → Day 4 → Day 5 → Day 6 → Day 7
```

予測期間を7日間としたのは、今回の要件定義に合わせるためである。

### 3. Forecast Output

主な出力項目：

- `forecast_origin`
- `target_date`
- `location_id`
- `storage_unit_id`
- `model_name`
- `actual_qty`
- `predicted_qty`

予測値だけでなく、**いつ・何を・どのモデルで予測した結果か**を後から追跡できる構造とした。

### 4. Evaluation Output

評価結果についても以下を記録した。

- `model_name`
- `evaluation_start`
- `evaluation_end`
- `horizon_days`
- `mae`
- `rmse`
- `r2`
- `wape`
- `train_seconds`
- `inference_seconds`
- `seed`

目的は、**再現性・比較可能性・追跡可能性**を確保することである。

### 5. Negative Prediction Handling

Ridge Regressionのような回帰モデルでは、理論上、負の需要量を出力する可能性がある。

#### Model Evaluation

元の`predicted_qty`をそのまま使用する。

モデルが実際に出力した結果を正しく評価するためである。

#### Inventory Simulation

需要量が負になることは業務上成立しないため、在庫計算時のみ以下の補正を行う。

```python
inventory_predicted_qty = max(predicted_qty, 0)
```

> **モデル評価ロジックと業務ロジックを分離する。**

### 6. Inventory Simulation

基本ロジック：

```text
Current Inventory
        ↓
－ Predicted Demand
        ↓
Inventory after Demand
```

これをDay 1からDay 7まで順番に計算し、予測需要に基づく在庫推移を確認できるようにした。

### 7. Safety Stock / Replenishment

各日の需要消費後在庫をSafety Stockと比較する。

```text
Inventory after Demand
        ↓
Safety Stockと比較
        ↓
<= Safety Stock ?
     /        \
   Yes         No
    ↓           ↓
Replenish    Continue
```

今回の要件では、**最初に安全在庫以下となったタイミングで1回補給**する仕様として実装した。

最終的に以下を確認できる。

- 7日間の予測需要
- 日次在庫推移
- 補給の必要性
- 補給日
- Day 7終了時の在庫

### 8. Automated Test

7日予測、負値処理、在庫計算、補給判定などについて自動テストを実装した。

予測値を出力できることだけでなく、業務ロジックが想定した条件で動作することを確認するためである。

### 9. M4 Output

```text
Demand Prediction
        ↓
Inventory Risk
        ↓
Replenishment Decision
```

モデルの予測結果を在庫・補給判断まで接続した。

---

# 最終到達点

## 今回構築したPipeline

```text
Raw Data
   ↓
Data Quality Check
   ↓
Daily Aggregation
   ↓
EDA
   ↓
Feature Engineering
   ↓
Leakage Check
   ↓
Baseline
   ↓
ML Models
   ↓
Time-Series Validation
   ↓
Model Selection
   ↓
7-Day Forecast
   ↓
Inventory Simulation
   ↓
Replenishment Decision
```

## 実装状況

**Milestone 1–5：完了**

- コード実装
- 評価結果出力
- Error Analysis
- Automated Test
- README / Markdown Documentation
- 公開版 README / Markdown Documentation
- 独立合成データ生成器
- 静的 Web デモ

---

# 今回の実装で重視したこと

| 観点 | 方針 |
|---|---|
| Data Quality | モデル構築前にデータ品質を確認する |
| Data Leakage Prevention | 未来情報を予測に利用しない |
| Fair Model Comparison | Baselineを含め同一条件で比較する |
| Validation / Test Separation | モデル選択と最終評価を分離する |
| Reproducibility | 条件・評価結果・Seed・処理を記録する |
| Business Logic | 予測結果を在庫・補給判断まで接続する |

---

# Scope

## 今回実装

**Milestone 1 → Milestone 2 → Milestone 3 → Milestone 4 → Milestone 5**

## 公開版に含めないもの

- 内部要件文書
- 実データ、実行結果、実運用向けの外部連携
- 公開デプロイと認証機能

---

# まとめ

今回のインターンシップでは、

> **「モデルを作る」だけでなく、Raw Dataから業務判断までの一連の需要予測Pipelineを構築した。**

```text
Data
 ↓
Feature
 ↓
Model
 ↓
Evaluation
 ↓
Forecast
 ↓
Inventory
 ↓
Replenishment Decision
```

コード・評価結果・テスト・ドキュメントを整理し、GitHubのPull Requestとして共有した。
