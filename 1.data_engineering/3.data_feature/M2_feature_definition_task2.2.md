# Feature Definition

## 1. 対象データ

| 項目 | 内容 |
|---|---|
| Location ID | `location_demo` |
| Storage Unit | `2` |
| 目的変数 | `daily_qty` |

---

## 2. 特徴量一覧

| Feature | Category | Definition | Source / Generation Rule | Prediction-Time Availability |
|---|---|---|---|---|
| `weekday` | Calendar | 対象日の曜日 | 対象日の `date` から生成 | Yes |
| `month` | Calendar | 対象日の月 | 対象日の `date` から生成 | Yes |
| `is_weekend` | Calendar | 土曜日・日曜日を1、それ以外を0 | 対象日の曜日から生成 | Yes |
| `lag_1` | Historical Demand | 1日前の日次需要量 | `daily_qty.shift(1)` | Yes |
| `lag_7` | Historical Demand | 7日前の日次需要量 | `daily_qty.shift(7)` | Yes |
| `lag_14` | Historical Demand | 14日前の日次需要量 | `daily_qty.shift(14)` | Yes |
| `rolling_mean_7` | Historical Demand | 対象日より前の7日間の日次需要量の平均 | `daily_qty.shift(1).rolling(window=7).mean()` | Yes |
| `rolling_mean_14` | Historical Demand | 対象日より前の14日間の日次需要量の平均 | `daily_qty.shift(1).rolling(window=14).mean()` | Yes |
| `rolling_std_7` | Historical Demand | 対象日より前の7日間の日次需要量の標準偏差 | `daily_qty.shift(1).rolling(window=7).std()` | Yes |

すべての特徴量は、予測時点で利用可能な情報のみを使用する。

- `weekday` / `month` / `is_weekend` は、対象日の既知のカレンダー情報から生成する。
- `lag_1` / `lag_7` / `lag_14` は、対象日より前の販売実績から生成する。
- `rolling_mean_7` / `rolling_mean_14` / `rolling_std_7` は、対象日より前の販売実績のみを使用して計算する。

---

## 3. 特徴量生成ルール

### 3.1 基本ルール

- `date` を昇順に並べた状態で特徴量を生成する。
- Lag特徴量は `shift()` を使用して生成する。
- Rolling特徴量は、`daily_qty.shift(1)` の後に `rolling()` を適用する。
- 当日の `daily_qty(t)` は、当日の特徴量計算に使用しない。
- 未来の `daily_qty` は使用しない。
- 特徴量生成時のデータ順序を保持する。

### 3.2 生成式

以下の定義を用いる。

- `lag_1(t) = daily_qty(t-1)`
- `lag_7(t) = daily_qty(t-7)`
- `lag_14(t) = daily_qty(t-14)`
- `rolling_mean_7(t) = mean(daily_qty(t-1), ..., daily_qty(t-7))`
- `rolling_mean_14(t) = mean(daily_qty(t-1), ..., daily_qty(t-14))`
- `rolling_std_7(t) = std(daily_qty(t-1), ..., daily_qty(t-7))`

これにより、対象日の需要実績そのものが特徴量に混入することを防止する。

---

## 4. 欠損値の扱い

LagおよびRolling特徴量では、データ開始時点で過去履歴が不足するため、初期行に `NaN` が発生する。

この `NaN` は特徴量生成上の正常な挙動であり、データ異常とはみなさない。

| Feature | Initial NaN Count |
|---|---:|
| `lag_1` | 1 |
| `lag_7` | 7 |
| `lag_14` | 14 |
| `rolling_mean_7` | 7 |
| `rolling_mean_14` | 14 |
| `rolling_std_7` | 7 |

最初にすべての特徴量が非 `NaN` となる日付は `YYYY-MM-DD` である。

本工程では、初期期間の `NaN` に対して以下の補完処理を行わない。

- 0埋め
- Forward Fill
- Backward Fill
- 補間

また、`NaN` を含む初期行は特徴量生成段階では削除しない。

---

## 5. EDA結果との対応

EDAで確認した需要特性を踏まえ、以下の特徴量を候補として採用した。

### カレンダー特徴量

- `weekday`
- `is_weekend`
- `month`

`weekday` および `is_weekend` は、曜日別および平日・週末の需要差が確認されたため採用した。

`month` は月別の需要変動が確認されたため、補助的なカレンダー特徴量として採用した。

### 時系列特徴量

- `lag_1`
- `lag_7`
- `lag_14`
- `rolling_mean_7`
- `rolling_mean_14`
- `rolling_std_7`

`lag_7` は曜日別の需要パターンを捉える特徴量として重要な候補である。

その他のLagおよびRolling特徴量は、短期的な需要水準や需要変動を捉える候補として採用した。

これらの特徴量の予測への有効性については、Milestone 3 のモデル評価で確認する。

---

## 6. データリーク防止

特徴量生成では、予測対象日以降の情報を使用しない。

特にRolling特徴量については、`daily_qty.shift(1)` を適用してから移動統計量を計算することで、予測対象日の `daily_qty` が計算範囲に含まれないようにする。

また、7日先予測などの多段予測では、予測基準日より後に実測された `daily_qty` を直接Lag・Rolling特徴量として使用しない。

予測時には、その時点で利用可能な履歴情報を基に特徴量を再計算する。

---

## 7. 7日先予測時の利用制約

本工程では、過去データに対する日次の教師あり学習用特徴量を生成する。

7日先予測を行う場合は、各予測時点で利用可能な情報のみを使用する。

- 予測基準日より後に実測された `daily_qty` は直接使用しない。
- 各予測日のLag・Rolling特徴量は、その時点までに利用可能な履歴から計算する。
- 多段予測では、先行する予測値を後続予測の履歴として利用する場合がある。

具体的な7日間多段予測およびRecursive Forecastの実装方法は、Milestone 3 の予測設計で定義する。

---

## 8. Task 2.3・2.4との関係

本工程で生成した特徴量について、Task 2.3 および Task 2.4 において以下を確認する。

- 予測時点より未来の情報が使用されていないこと
- Lag特徴量の生成値が正しいこと
- Rolling特徴量の生成値が正しいこと
- 初期期間の `NaN` が想定どおりであること
- 最初の完全な特徴量行が `YYYY-MM-DD` となること

以上の確認により、特徴量の定義と生成処理の整合性を検証する。