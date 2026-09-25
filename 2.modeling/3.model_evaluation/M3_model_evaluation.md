# Milestone 3 - Model Evaluation and Comparison

## 1. 目的

M3.1 で実装した Baseline と M3.2 で実装した機械学習モデルについて、同一の時系列評価条件で Validation Set と Test Set の性能を比較する。

評価対象は以下の4モデルとする。

- Seasonal Naive / Previous-week Same Weekday Baseline
- Ridge Regression
- Random Forest
- Gradient Boosting

評価指標として MAE、RMSE、R²、WAPE を使用し、あわせて学習時間および推論時間を記録する。

モデル選択は Validation Set の結果に基づいて行い、Test Set は最終評価専用とする。

---

## 2. 評価条件

Validation Set と Test Set では、同一の時系列評価条件を使用する。

- Expanding-window を使用する。
- Daily rolling origin により forecast origin を1日ずつ前進させる。
- 各 forecast origin では `date <= forecast_origin` のデータのみを学習に使用する。
- Validation Set と Test Set を分離する。
- Test Set の結果をモデル選択やパラメータ調整に使用しない。
- Forecast horizon は `1` ～ `7` 日とする。
- Baseline、Ridge、Random Forest、Gradient Boosting を同一の forecast schedule で評価する。
- Partition 境界付近では、各 partition 内で利用可能な horizon のみを評価対象として保持する。

Validation および Test の予測 task 数は、それぞれ 616 件、189 件である。

---

## 3. 評価指標

以下の4つの指標を算出する。

| Metric | Description |
|---|---|
| MAE | Mean Absolute Error |
| RMSE | Root Mean Squared Error |
| R² | Coefficient of Determination |
| WAPE | Weighted Absolute Percentage Error |

あわせて、各モデルおよび各 partition について以下の時間を記録する。

| Metric | Description |
|---|---|
| `train_seconds` | モデルの学習に要した時間 |
| `inference_seconds` | モデルの推論に要した時間 |

---

## 4. Validation 結果

Validation Set における各モデルの評価結果は以下の通りである。

| Model | MAE | RMSE | R² | WAPE (%) | Train Time (s) | Inference Time (s) |
|---|---:|---:|---:|---:|---:|---:|
| Ridge | **29.92** | **36.46** | **0.3267** | **6.2094** | **0.17** | **0.38** |
| GradientBoosting | 30.59 | 36.85 | 0.3125 | 6.3475 | 23.49 | 0.35 |
| RandomForest | 32.00 | 38.55 | 0.2473 | 6.6392 | 33.70 | 22.18 |
| Baseline | 37.09 | 46.32 | -0.0867 | 7.6957 | 0.00 | 0.02 |

Validation では、Ridge が4モデルの中で最も低い WAPE および MAE を示した。

Ridge の WAPE は 6.2094%、MAE は 29.92 であった。

---

## 5. Test 結果

Test Set における各モデルの評価結果は以下の通りである。

| Model | MAE | RMSE | R² | WAPE (%) | Train Time (s) | Inference Time (s) |
|---|---:|---:|---:|---:|---:|---:|
| Ridge | 30.37 | 38.67 | 0.3751 | 5.9043 | 0.05 | 0.10 |
| GradientBoosting | **30.31** | **37.72** | **0.4055** | **5.8922** | 8.22 | 0.10 |
| RandomForest | 31.64 | 39.41 | 0.3511 | 6.1521 | 11.54 | 6.35 |
| Baseline | 34.23 | 44.68 | 0.1660 | 6.6546 | 0.00 | 0.01 |

Test では、Gradient Boosting が MAE、RMSE、R²、WAPE の4指標で Ridge を含む他のモデルを下回る誤差値または高い決定係数を示した。

ただし、Test Set は最終評価専用として扱っているため、この結果をモデル選択には使用しない。

---

## 6. モデル比較と選択

モデル選択は Validation Set の WAPE を第一評価指標とし、WAPE が同値の場合は MAE を使用する。

Validation の結果では Ridge が最も低い WAPE を示したため、Task 3.2 で定義した選択ルールに基づき、Ridge Regression (`alpha=1.0`) を最終モデルとして採用する。

| 観点 | Ridge | GradientBoosting | RandomForest | Baseline |
|---|---:|---:|---:|---:|
| Validation WAPE (%) | **6.2094** | 6.3475 | 6.6392 | 7.6957 |
| Validation MAE | **29.92** | 30.59 | 32.00 | 37.09 |
| Validation Train Time (s) | **0.17** | 23.49 | 33.70 | 0.00 |
| Validation Inference Time (s) | **0.38** | 0.35 | 22.18 | 0.02 |

本表では、Validation Set における予測性能および計算時間を比較した。

Test Set では Gradient Boosting がより低い誤差を示したが、Test Set はモデル選択から分離しているため、最終モデルの選択は Validation Set の結果に基づいて行う。

---

## 7. 最終モデル

Validation Set の結果に基づき、最終モデルとして以下を固定する。

| Item | Configuration |
|---|---|
| Model Family | Ridge Regression |
| Alpha | `1.0` |
| Preprocessing | `StandardScaler` |
| Selection Metric | Validation WAPE → Validation MAE |

Validation における最終モデルの主要結果は以下の通りである。

- WAPE: `6.2094%`
- MAE: `29.92`
- RMSE: `36.46`
- R²: `0.3267`
- Train Time: `0.59 s`
- Inference Time: `1.26 s`

Test Set では Ridge に加えて他のモデルの結果も記録するが、Test 結果を用いてモデルを変更しない。

---

## 8. Leakage Control

Validation および Test の評価では、時系列予測における future leakage を防止するため、以下の条件を適用する。

- 各 forecast origin における学習データは `date <= forecast_origin` に限定する。
- forecast origin より後の実績値を学習に使用しない。
- 予測対象日の実績値を予測時点の特徴量生成に使用しない。
- Recursive Forecasting では、後続 horizon の特徴量生成に future actual を使用せず、それまでに生成した prediction を temporary history に追加する。
- Test Set の結果を Validation におけるモデル選択に使用しない。
- Validation で選択したモデル設定を Test 実行前に固定する。

これにより、各 forecast task では予測時点で利用可能な情報のみを使用する。

---

## 9. Partition 境界における評価

Validation Set および Test Set の partition 境界付近では、すべての forecast origin が7日分の完全な予測 horizon を持つとは限らない。

そのため、partition 最後の6 forecast origin については、各 partition 内で利用可能な horizon のみを評価対象として保持する。

したがって、予測 task 数は単純な `365 × 7` ではなく、partition 境界条件を考慮した実際の評価 task 数として集計する。

| Partition | Prediction Count |
|---|---:|
| Validation | 616 |
| Test | 189 |

---

## 10. 出力

評価結果は以下のファイルに保存する。

```text
2.modeling/3.model_evaluation/
├── local_outputs/
│   ├── model_comparison_summary.csv
│   └── evaluation_results_task4.3.csv
└── figures/
    └── validation_model_wape_comparison.png
```

`model_comparison_summary.csv` にはモデル比較結果を保存し、`validation_model_wape_comparison.png` には Validation Set における WAPE の比較結果を保存する。

---

## 11. 結論

本 Task では、Seasonal Naive Baseline、Ridge Regression、Random Forest、Gradient Boosting を同一の時系列評価条件で比較した。

Validation Set では Ridge Regression が最も低い WAPE を示し、WAPE 6.2094%、MAE 29.92、RMSE 36.46、R² 0.3267 となった。

Validation のモデル選択ルールである WAPE → MAE に基づき、最終モデルには Ridge Regression (`alpha=1.0`) を採用する。

Test Set では Gradient Boosting が WAPE、MAE、RMSE、R² の各指標で Ridge を含む他モデルより良い結果を示したが、Test Set はモデル選択に使用しない。

以上により、Validation Set を用いて最終モデルを固定し、Test Set を独立した最終評価として扱う時系列モデル比較を実施した。
