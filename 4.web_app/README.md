# Energy Demand Internship Web Dashboard

## 目的

ローカルで生成した7日需要予測とモデル評価結果を表示し、初期在庫・安全在庫・1回補充量を変更して在庫推移を確認する。

## 表示内容

- 7日累計需要、補充日、7日後在庫
- 日別需要予測の棒グラフ
- 安全在庫線を含む在庫推移グラフ
- 在庫条件の入力と日別明細表
- Ridge Regression の評価指標

## 起動

```bash
npm install
npm run dev
```

## データ更新

プロジェクトルートで以下を実行する。

```bash
python3 3.forecasting/export_web_dashboard_data.py
```

この処理は `3.forecasting/local_outputs/forecast_7days_task4.2.csv` と `2.modeling/3.model_evaluation/local_outputs/model_comparison_summary.csv` を読み込み、`public/data/dashboard-data.json` を更新する。

## データ取り扱い

本画面はローカル用途に限定する。原始データ、予測 CSV、Web 用 JSON を外部サービスまたは公開リポジトリへ送信しない。
