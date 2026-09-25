# Milestone 3 - Baseline Definition

## 1. 目的

Task 3.1 では、7日先需要予測における Baseline として、Seasonal Naive / Previous-week Same Weekday を採用する。

本 Baseline の目的は、曜日周期を利用したシンプルかつ再現可能な参照予測を定義し、後続の ML モデルと同一条件で比較できる基準を設定することである。

---

## 2. Baseline の定義

forecast origin を `t`、forecast horizon を `h` とすると、予測対象日の需要量を7日前の同曜日の実績値から推定する。

$$
prediction(t+h) = actual(t+h-7), \quad h = 1,2,\dots,7
$$

ここで、

- `t`：forecast origin
- `h`：forecast horizon
- `t+h`：予測対象日
- `t+h-7`：7日前の対応日

を表す。

`t+h-7` は forecast origin 時点で既に観測済みの過去日であるため、未来の実績値を使用しない。

---

## 3. Baseline を採用する理由

本 Baseline は、以下の理由から7日先需要予測の参照モデルとして採用する。

- EDA により曜日ごとの需要差が確認されている。
- 7日前は予測基準日時点で利用可能な実績データである。
- 前週同曜日の需要を利用することで、1週間周期の変動を簡潔に反映できる。
- モデル学習やパラメータ推定を必要としないため、実装と説明が容易である。
- forecast origin より後の実績値を使用しないため、Data Leakage を防止できる。
- ML モデルと同一の forecast origin、target date、horizon を用いて比較できる。

---

## 4. 7日予測の実装方法

各 forecast origin `t` に対して、以下の手順で予測する。

1. `horizon = 1, 2, ..., 7` を設定する。
2. `target_date = t + h` を求める。
3. `source_date = target_date - 7 days` を求める。
4. `prediction = actual(source_date)` とする。

形式的には以下のとおりである。

```text
Forecast origin: t

Horizon 1
  target_date = t + 1
  source_date = t - 6
  prediction  = actual(t - 6)

Horizon 2
  target_date = t + 2
  source_date = t - 5
  prediction  = actual(t - 5)

...

Horizon 7
  target_date = t + 7
  source_date = t
  prediction  = actual(t)
```

## 5. Forecast Origin Safety と Leakage Control

本 Baseline では、予測対象日の未来実績を直接使用しない。

各予測について、以下の条件を満たす。

- `source_date <= forecast_origin`
- `source_date < target_date`
- 予測対象日以降の `actual` を使用しない
- 予測対象期間中の未来実績を使用しない
- 未来データを利用した特徴量生成を行わない

この設計により、Validation Set および Test Set の両方で、forecast origin 時点の情報だけを用いた予測を実施できる。

---

## 6. Validation / Test における共通条件

Baseline は Validation Schedule と Test Schedule の両方に対して同一の予測ルールを適用する。

各予測結果では、少なくとも以下の情報を保持する。

- `evaluation_partition`
- `forecast_origin`
- `target_date`
- `horizon`
- `actual`
- `prediction`
- `absolute_error`

これにより、Baseline と ML モデルを同一の予測タスク単位で比較できる。

---

## 7. 出力 Schema

Baseline の予測結果には、以下の項目を保持する。

| Column | Description |
|---|---|
| `evaluation_partition` | Validation または Test |
| `forecast_origin` | 予測基準日 |
| `target_date` | 予測対象日 |
| `horizon` | 予測日数（1～7） |
| `actual` | 実際の需要量 |
| `prediction` | Baseline による予測値 |
| `absolute_error` | `abs(actual - prediction)` |

追加列を保持する場合も、予測時点で利用できない未来情報を含めない。

---

## 8. 学習および推論時間

本 Baseline は、機械学習モデルの学習処理を行わない。

そのため、学習時間は以下のとおりである。

- `train_seconds = 0.0`

推論時間については、実際の予測処理に要した時間を測定して記録する。

本 Baseline はモデル fitting を行う機械学習モデルではなく、前週同曜日の実績値を参照するルールベースの予測方法である。

---

## 9. 評価時の位置付け

Baseline は、ML モデルの性能を評価するための参照基準として使用する。

Model selection 自体は Validation Set の結果に基づいて行い、Test Set は最終評価に使用する。

Baseline と ML は、以下の条件を統一して比較する。

- 同一の forecast origin
- 同一の target date
- 同一の forecast horizon
- 同一の evaluation partition
- 同一定義の評価指標

共通評価指標は以下のとおりである。

- MAE
- RMSE
- R²
- WAPE

---

## 10. 結論

Seasonal Naive / Previous-week Same Weekday は、7日先需要予測におけるシンプルな参照モデルとして採用する。

forecast origin `t` に対して `t+1` ～ `t+7` を予測し、それぞれの予測値には7日前の同曜日の実績値を使用する。

この方法は、forecast origin 時点で利用可能な過去実績のみを使用するため、未来実績による Data Leakage を防止できる。

また、Validation Set と Test Set に対して同一の予測ルールを適用することで、ML モデルとの性能差を同一条件で比較できる。
