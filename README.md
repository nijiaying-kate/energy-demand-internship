# Energy Demand Internship

## 概要

拠点の日次販売実績から翌日以降7日間の需要を予測し、在庫推移と1回補充の影響を確認するローカル実行プロジェクトです。

## 解決する課題

エネルギー供給拠点では、日々の需要変動により、在庫不足と過剰在庫の両方が起こり得る。需要を過小に見積もると欠品リスクが高まり、過大に見積もると不要な在庫を抱えることになる。

本プロジェクトでは、過去の日次需要だけを用いて翌日から7日先までを予測し、その予測値を在庫シミュレーションへ接続する。これにより、予測精度だけでなく、安全在庫を下回る日と1回の補充が在庫推移へ与える影響を、同じワークフローで確認できる。

## 目的と動機

目的は、時系列予測を実務上の在庫判断につなげる、再現可能で説明しやすい最小構成の分析パイプラインを作ることである。

- 日次需要の前処理から特徴量生成、時系列評価、7日予測までを一貫して実装する。
- expanding-window と daily rolling origin により、未来情報を使わない評価を行う。
- Validation でモデルを選択し、Final Test を独立した最終評価として保持する。
- 予測結果を在庫・補充シミュレーションと Web ダッシュボードへ渡し、利用者が条件変更の影響を確認できるようにする。

## データソース

公開版には、実データではなく `0.original_raw_data/generate_synthetic_transactions.py` が固定シード（`20250301`）で生成した独立合成トランザクションデータを含める。生成される `location_demo_transactions.csv` は、単一の匿名化された `location_id` と `storage_unit_id`、日時、需要量を持つ学習用サンプルである。

この合成データは、公開用に新たに設計したものであり、実在する組織、拠点、個人、識別子、取引または需要実績を複製・変換したものではない。派生 CSV、評価結果、図表はローカルで再生成する成果物として扱う。

## 実装範囲

| Milestone | 内容 | 状態 |
|---|---|---|
| M1 | データ理解・前処理 | 完了 |
| M2 | EDA・特徴量生成・リーク確認 | 完了 |
| M3 | Baseline / ML / 時系列評価 / 誤差分析 | 完了 |
| M4 | 7日予測・在庫・1回補充シミュレーション | 完了 |
| M5 | ローカル Web ダッシュボード | 実装済み |

## 最終モデル

- Model: `StandardScaler → Ridge Regression`
- Alpha: `1.0`
- 選択方法: Validation Set の WAPE を優先し、同値時は MAE を比較する。
- Test Set はモデル選択に使用しない。

## 処理フロー

```text
Raw CSV → 日次需要データ → 特徴量 → 時系列評価 → 7日予測 CSV
                                                    ↓
                                         在庫・1回補充シミュレーション
                                                    ↓
                                     Web 用ローカル JSON → ダッシュボード
```

## Python 環境

```bash
python3 -m pip install -r requirements.txt
```

## 公開版の再現手順

この公開版には、元データとは無関係に作成した固定シードの合成入力データを含める。必要に応じて、次のコマンドで再生成できる。

```bash
python3 0.original_raw_data/generate_synthetic_transactions.py
python3 1.data_engineering/1.data_cleaning/M1_preprocess_daily_aggregation.py
python3 1.data_engineering/2.data_eda/generate_eda_task2.1.py
python3 1.data_engineering/3.data_feature/generate_features_task2.2.py
python3 1.data_engineering/3.data_feature/m2_check_feature_integrity_task2.3_task2.4.py
python3 1.data_engineering/4.data_split/split_dataset_task3.3.py
python3 2.modeling/1.baseline/run_baseline_task3.1.py
python3 2.modeling/2.ml_model/run_ml_model_task3.2.py
python3 2.modeling/3.model_evaluation/evaluate_models_task3.4_task3.6.py
python3 2.modeling/4.error_analysis/analyze_errors_task3.5.py
```

上記はリポジトリ直下から順に実行する。M2 以降は前段のローカル生成物を入力とし、Validation でモデル選択、Test で最終評価を行う。`local_outputs/`、EDA の図表・集計表および派生 CSV はローカル生成物であり、Git 管理しない。

## 主要な実行コマンド

```bash
# 7日予測
python3 3.forecasting/forecast_7days.py \
  --input 1.data_engineering/3.data_feature/v5_location_demo_storage_unit_demo_features.csv \
  --forecast-origin 2024-12-30 \
  --location-id location_demo \
  --storage-unit-id storage_unit_demo \
  --output 3.forecasting/local_outputs/forecast_7days_task4.2.csv

# 在庫・1回補充シミュレーション
python3 3.forecasting/inventory_simulation_task4.4_to_4.7.py \
  --input 3.forecasting/local_outputs/forecast_7days_task4.2.csv \
  --initial-inventory 5000 \
  --safety-stock 1800 \
  --replenishment-qty 4500

# Web 用データの更新
python3 3.forecasting/export_web_dashboard_data.py
```

## Web ダッシュボード

```bash
cd 4.web_app
npm ci
npm run dev
```

ブラウザで表示されるダッシュボードでは、7日需要予測、モデル指標、初期在庫・安全在庫・補充量の入力、日別在庫推移、最初の補充日を確認できます。

依存関係をインストールせずに画面だけを確認したい場合は、`4.web_app/static_demo/index.html` を直接開くか、同ディレクトリを静的ホスティングします。この静的デモは独立した合成値のみを使用します。

## データ取り扱い

実際の原始データ、特徴量 CSV、予測 CSV、評価結果およびローカル実行 JSON は外部サービスや公開リポジトリへアップロードしません。ただし、`0.original_raw_data/location_demo_transactions.csv` と `4.web_app/public/data/dashboard-data.json` は、公開デモの再現に必要な独立合成データとして明示的に含めます。

## 公開版に関する注記

本リポジトリには、機密保持義務により元の業務データ、識別子、実行結果および内部成果物を含めません。公開デモを作成する場合は、実レコード、実績値、識別子または業務結果を再現しない、独立して生成した合成データのみを使用します。
