# Energy Demand Internship - Engineering Skill v2.2

## 1. Role

本プロジェクトでは、要件準拠、正確性、データリーク防止、再現性、可読性を優先する。過度な実装は行わない。

## 2. Source of Truth

公開版では `Energy_Demand_Internship_開発工程.md` を設計上の参照資料とする。
内部要件定義書および実データは、この公開版には含めない。

## 3. Current Delivery Scope

現在の実装・レビュー範囲は以下とする。

- M1: データ理解・前処理
- M2: EDA・特徴量生成
- M3: モデリング・評価・誤差分析
- M4: 7日予測・在庫・1回補充シミュレーション
- M5: ローカル Web ダッシュボード（予測表示・指標表示・在庫シミュレーション）

公開リポジトリでは、合成データまたはローカル生成物のみを使用する。

## 4. Engineering Priorities

1. Requirement compliance
2. Correctness
3. Data leakage prevention
4. Reproducibility and portability
5. Reviewability
6. Simplicity and maintainability

## 5. Implementation Rules

- `date <= forecast_origin` 以外の実績を学習に使用しない。
- 7日予測では future actual を使わず、recursive forecasting を使用する。
- 評価値と在庫計算値を区別し、在庫計算では `max(predicted_qty, 0)` を使用する。
- Validation でモデル選択し、Test は最終評価専用とする。
- 絶対パスをコードまたは文書に残さない。
- 原始データ、生成 CSV、秘密情報を外部へ送信・公開しない。
- Web は `3.forecasting/export_web_dashboard_data.py` が生成するローカル JSON のみを読み込む。

## 6. Validation

変更後は、対象 Python の構文確認、対象スクリプトの実行、出力 schema の確認を行う。Web 変更後は `npm run build` を実行する。
