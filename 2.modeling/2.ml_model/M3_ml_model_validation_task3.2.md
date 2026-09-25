# Milestone 3 - ML Validation

## 1. 目的

Ridge, RandomForest, GradientBoosting を同一条件で比較し、
Validation Set で candidate selection を行い、Test Set で最終評価を実施する。

## 2. Model families and features

- models: Ridge, RandomForestRegressor, GradientBoostingRegressor
- features: weekday, month, is_weekend, lag_1, lag_7, lag_14, rolling_mean_7, rolling_mean_14, rolling_std_7
- target: daily_qty
- selection rule: lower Validation WAPE first, then lower Validation MAE

## 3. Selected configuration

- model family: Ridge
- candidate: alpha_1.0
- config: {'alpha': 1.0}

## 4. Validation results

- validation prediction count: 616
- validation WAPE: 6.2094
- validation MAE: 29.9240
- validation RMSE: 36.4627
- validation R²: 0.3267
- validation train time (s): 0.170355
- validation inference time (s): 0.379029

## 5. Final Test summary

- test prediction count: 189
- test train time (s): 0.046566
- test inference time (s): 0.102742

## 6. Leakage control

- training_window uses date <= forecast_origin only
- recursive feature generation is used for horizon 1～7
- future actual is not used directly
- selected configuration is frozen before Test execution
