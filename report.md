# Hourly Load Forecasting for EV Charging Stations on Jeju Island

## 1. Problem Definition

As EV adoption accelerates, charging infrastructure is becoming a significant load on power grids. Unlike fixed household or industrial demand, EV charging is inherently flexible — most vehicles can charge at different times without affecting mobility. This makes EV chargers an ideal resource for demand response (DR): with accurate load forecasts, operators can shift charging to off-peak windows, flatten demand peaks, and reduce the need for infrastructure upgrades. Forecasting also supports renewable energy integration — by steering charging into periods of solar or wind surplus, operators can absorb clean energy that would otherwise be curtailed.

This project asks: **Can we predict the next-hour electricity consumption (kWh) of EV charging stations using historical load patterns, temporal features, and weather data?** We use Jeju Island — with its high EV density, active DR programs, and public data — as a case study, but the methodology is transferable to any city with growing EV adoption.

## 2. Dataset

We use the **PlusDR dataset** (Park et al., 2025, Figshare), which contains operational records from 873 EV charging stations on Jeju Island covering January 2021 to December 2022 at hourly resolution. The dataset includes station metadata (charger type, power rating, location, contract type), demand response event records, and per-station load time series.

**Preprocessing pipeline.** Raw data consisted of 873 individual CSV files in wide format (one row per day, columns per 15-min interval). We reshaped these into proper time series, aggregated to hourly resolution, and merged with station metadata. After filtering stations with excessive missing data, 585 commercial stations remained (~7.2M rows). One residential station (ID 811236417) was excluded as its load profile (mean 132.6 kWh vs. 38.0 kWh for commercial stations) was not comparable to the rest of the fleet. Hourly weather data (temperature, humidity, precipitation, wind speed, cloud cover) from Open-Meteo was joined by city (Jeju-si / Seogwipo-si) to capture the microclimate difference caused by Mt. Hallasan.

**Feature engineering.** The final feature set contains 36 variables: cyclical time encodings (hour, day-of-week, month as sin/cos pairs), per-station lag features (1h, 2h, 3h, 24h, 168h), rolling statistics (mean and standard deviation at 6h, 12h, 24h, and 7-day windows, shifted by one hour to prevent target leakage), load momentum, load ratio vs. 24h baseline, weather variables, and encoded station attributes.

## 3. Model Implementation and Evaluation

**Validation strategy.** We use a temporal train/test split: January 2021 – June 2022 for training (65%) and July – December 2022 for testing (35%). This respects the time-series nature of the data and avoids future information leaking into training. During hyperparameter tuning, Optuna's internal validation split (85/15 of training data) serves as an effective third partition for model selection and early stopping.

**Models.** We train seven models in total — five baselines and two tuned variants:

- **Persistence (lag 24h):** predicts load as "same hour yesterday." Serves as a naive forecast baseline.
- **Station Hourly Mean:** predicts the historical average load for each station-hour combination.
- **Ridge Regression:** linear model with L2 regularization.
- **LightGBM and XGBoost (defaults):** gradient-boosted tree models with default hyperparameters.
- **LightGBM and XGBoost (tuned):** hyperparameters optimized via Optuna (Bayesian optimization, 30 trials on a 50% subsample for memory efficiency), then retrained on the full training set with early stopping.

**Evaluation metrics.** We report MAE, RMSE, and R², chosen for their interpretability in the energy domain. MAE gives the average prediction error in kWh, directly meaningful for grid operators. RMSE penalizes large errors — critical since peak-hour mispredictions are costly. R² measures the proportion of variance explained relative to predicting the mean.

| Model | MAE (kWh) | RMSE (kWh) | R² |
|---|---|---|---|
| Persistence (lag 24h) | 3.79 | 8.74 | −0.038 |
| Station Hourly Mean | 3.25 | 6.58 | 0.412 |
| Ridge Regression | 3.14 | 6.28 | 0.463 |
| LightGBM (default) | 2.76 | 5.99 | 0.513 |
| XGBoost (default) | 2.76 | 5.99 | 0.512 |
| LightGBM (tuned) | 2.78 | 6.00 | 0.510 |
| **XGBoost (tuned)** | **2.76** | **5.98** | **0.514** |

The best model, XGBoost (tuned), achieves an R² of 0.514 with an overfitting gap of just 0.001 (train R² = 0.515). Gradient-boosted models significantly outperform baselines, while tuning provides only marginal improvement over defaults — suggesting the default configurations are already well-suited for this data structure.

**Feature importance.** The top features for the final model are: `load_lag_1h` (28.9%), `load_roll_mean_7d` (12.1%), `load_roll_std_7d` (9.9%), and `load_roll_mean_6h` (9.4%). Lag and rolling features dominate, confirming that station-level autoregressive patterns are the strongest predictors. Weather features contribute minimally, consistent with Jeju's mild, stable climate having limited impact on charging behavior.

## 4. Classification Reframing (Iteration 4)

Examining the regression model's predictions on individual stations revealed a pattern: the model consistently tracked the *timing* of charging events but systematically underpredicted their *magnitude*. Predicted curves followed actual curves up and down but flattened the peaks. This suggested the model had learned *when* stations are active but not *how much* load to expect — a limitation of predicting exact kWh for event-driven demand.

This observation motivated reframing the problem as multi-class classification: instead of predicting exact load, predict the **demand level**.

| Class | Load Range | Dataset Share |
|---|---|---|
| Idle | < 0.1 kWh | 56.4% |
| Low | 0.1 – 5 kWh | 25.3% |
| Medium | 5 – 20 kWh | 13.8% |
| High | ≥ 20 kWh | 4.5% |

We trained LightGBM and XGBoost classifiers with class-imbalance handling (`is_unbalance=True`, sample weighting) and Optuna tuning (30 trials, 50% subsample, optimizing macro F1).

| Model | Accuracy | F1 (macro) | F1 (weighted) |
|---|---|---|---|
| Majority class baseline | 0.569 | 0.181 | 0.413 |
| LightGBM (default) | 0.806 | 0.667 | 0.799 |
| XGBoost (default) | 0.761 | 0.632 | 0.775 |
| **LightGBM (tuned)** | **0.808** | **0.670** | **0.800** |
| XGBoost (tuned) | 0.770 | 0.640 | 0.782 |

The best classifier (LightGBM tuned) achieves 81% accuracy with zero overfitting (F1 gap = −0.009, i.e., test outperforms train). Per-class performance confirms the model's strength lies in detecting station activity:

| Class | Precision | Recall | F1 |
|---|---|---|---|
| Idle | 0.88 | 0.95 | 0.92 |
| Low | 0.74 | 0.70 | 0.72 |
| Medium | 0.62 | 0.55 | 0.58 |
| High | 0.59 | 0.38 | 0.46 |

A head-to-head comparison — binning the regression model's continuous predictions into the same four classes — shows the dedicated classifier dramatically outperforms: 80.8% accuracy vs. 42.3%, and 0.670 vs. 0.440 macro F1. Confusion matrix analysis reveals that 71.3% of misclassifications are between adjacent classes (e.g., Idle↔Low, Medium↔High), indicating the model understands the demand ordering but is imprecise at class boundaries. Confidence analysis shows correct predictions are made with mean probability 0.847 vs. 0.600 for incorrect ones — the model reliably signals when it is uncertain.

## 5. Data Refinement Process

The final results reflect three modeling iterations, each driven by a data-quality discovery:

| Iter. | R² | Stations | Features | Key change |
|---|---|---|---|---|
| 1 | 0.827 | 586 | 31 | Original model — `contract_type_code` at 88% feature importance |
| 2 | 0.742 | 585 | 36 | Dropped residential station, added 5 features — importance balanced |
| 3 | 0.514 | 585 | 36 | Fixed rolling feature leakage (`.shift(1)`) — honest performance |

**Iteration 1 → 2:** Feature importance analysis revealed that `contract_type_code` dominated at 88%, driven by a single residential station with a distinctive load profile inflating apparent model performance. After removing it and adding five new features (load momentum, load ratio, hour×weekend interaction, cold weather flag, 7-day rolling statistics), feature importance rebalanced with `load_roll_mean_6h` leading at 36%.

**Iteration 2 → 3:** Peer review identified that rolling statistics (e.g., `rolling(6).mean()` at time *t*) included the current observation — the very value being predicted. Adding `.shift(1)` so the window covers only past values (load[t−6] through load[t−1]) dropped R² by 0.23 points, confirming the leakage was responsible for that artificial performance boost.

These were correctness and data-quality fixes, not test-metric optimization. Each iteration produced a more honest model, and we consider the lower R² a more trustworthy measure of real predictive ability.

## 6. Critical Reflection

**Why R² = 0.514 is reasonable.** EV charging is fundamentally event-driven: a driver either plugs in or does not, and this binary decision is influenced by individual schedules, trip patterns, and battery state — none of which appear in our features. Our model is a single global model across 585 heterogeneous stations, each with different usage patterns, charger types, and locations. Comparable studies using the same PlusDR dataset (Park et al., 2025) focus on station classification rather than hourly load regression, and published load forecasting work that reports R² > 0.9 typically uses synthetic datasets or includes features that leak future information.

**Construct validity.** The target variable `load_kwh_clean` aggregates all charger activity at a station per hour. This masks individual session dynamics and makes the prediction problem harder, but it is the operationally relevant quantity for grid management. A session-level model would likely achieve higher R² but would require predicting session arrivals — a separate, arguably harder problem.

**Distributional shift.** The test period (Jul–Dec 2022) may differ structurally from training (Jan 2021–Jun 2022) due to growing EV adoption, new station openings, and seasonal tourism patterns on Jeju Island. The near-zero overfitting gap (0.001) suggests the model generalizes well within this timeframe, but performance could degrade as the EV landscape evolves.

**Limitations and potential improvements.** Time-of-use (TOU) electricity tariffs, identified in the literature (Lim et al., 2023) as significantly influencing Jeju charging behavior, are not included as features. Tourist arrival data, EV registration counts, and holiday calendars could also improve predictions but are available only at daily or monthly resolution, limiting their value for hourly forecasting. A per-station or clustered modeling approach — rather than a single global model — could better capture heterogeneous usage patterns but would require substantially more compute and risk overfitting on stations with sparse data.

**Fairness and societal considerations.** Load forecasts that systematically underpredict certain station types could lead to unequal DR burden distribution. Our error analysis shows higher MAE during peak hours (8–18h), which are precisely the hours when accurate forecasts matter most for DR. If deployed, the model's predictions should be supplemented with uncertainty estimates to avoid overconfident DR dispatch decisions.
