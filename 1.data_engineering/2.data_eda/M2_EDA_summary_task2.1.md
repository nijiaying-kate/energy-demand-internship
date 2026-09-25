# Milestone 2 - Exploratory Data Analysis

## 1. Data Quality and Coverage

- Data period: 2023-01-01 to 2024-12-30
- Sample size: 730 daily records
- Missing dates: 0
- Basic statistics: mean=516.62, median=516.87, std=53.27, min=353.86, max=653.53
- IQR outlier count: 1
- Observation: the dataset covers a continuous daily period without missing dates, and the daily target variable is suitable for the next EDA step.

## 2. How Does Demand Change Over Time?

- Observation: the daily series shows a multi-year pattern with visible fluctuations around a sustained level, rather than a single monotonic trend.
- Evidence: the 30-day rolling mean in Figure 1 smooths the short-term volatility while preserving the longer-run structure; several high-demand periods are easily visible above the baseline.
- Interpretation: the demand series appears to include both a broad level component and repeated short-term changes, while the outlier dates indicate brief bursts of unusually high demand.
- Implication for Task 2.2: a calendar-aware model is likely to benefit from a combination of time-of-week and time-of-year signals, while the temporal structure may also justify checking lag-based candidates if the evidence later supports them.

## 3. Does Demand Differ by Weekday?

- Observation: the weekday pattern is not flat. The weekly demand distribution indicates a visible difference in central tendency across Monday to Sunday.
- Evidence: the highest mean demand appears on Saturday (570.20), while the lowest mean demand appears on Monday (478.37).
- Interpretation: this observed difference is stronger than a random fluctuation and suggests that the weekly cycle is one of the main calendar patterns in the data.
- Implication for Task 2.2: weekday and is_weekend are reasonable candidate calendar features to evaluate, because the pattern is clearly visible in the observed data.

## 4. Is There Monthly Seasonality?

- Observation: month-level demand differs across the year, but the variation is more gradual than the weekday pattern.
- Evidence: the highest monthly mean is 4.0 (555.26) and the lowest is 9.0 (480.03).
- Interpretation: the monthly pattern indicates a seasonal component, but it is not as structurally dominant as the weekday pattern in the current sample.
- Implication for Task 2.2: month is a sensible calendar candidate for later feature screening, while it should be treated as a complementary signal rather than a replacement for weekday and weekend effects.

## 5. What Does the Demand Distribution Look Like?

- Observation: the overall daily distribution is right-skewed, with a long upper tail and a visible separation between the central mass and the highest-demand days.
- Evidence: the mean (516.62) is noticeably above the median (516.87), which is consistent with a skewed distribution.
- Interpretation: the shape suggests a heterogeneous daily-demand mixture, where the majority of days are moderate and a smaller set of days sit far into the upper tail.
- Implication for Task 2.2: the distribution supports retaining the original daily scale for supervised learning and checking whether a transformed or thresholded representation is needed only if later modeling evidence requires it.

## 6. How Should Outliers Be Interpreted?

- Observation: 1 days are flagged by the same IQR rule used in Milestone 1.
- Evidence: the outlier dates are concentrated in a limited number of high-demand periods, and the outlier subset has an observed weekend share of 0.00%.
- Interpretation: there is no evidence these observations are invalid data points; they are more consistent with real high-demand business episodes. The current EDA therefore retains them rather than removing or correcting them.
- Implication for Task 2.2: outliers should remain visible during feature exploration and can be considered when evaluating whether holiday/weekend interactions or extreme-demand cases deserve dedicated logic, but they should not be treated as data errors without an external validation source.

## 7. Implications for Feature Engineering

1. The data covers a continuous daily period with no missing dates and is reliable for EDA.
2. Demand varies visibly by weekday, with a clear weekly pattern and a higher observed mean on the weekend.
3. Monthly demand also varies, indicating a weaker but still visible seasonal component.
4. The daily distribution is right-skewed, with a long upper tail and several extreme high-demand observations.
5. The IQR outliers are retained because there is no current evidence that they are erroneous data.
