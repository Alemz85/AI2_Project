## Iteration 3 — Fixed Rolling Feature Leakage

- **Stations:** 585
- **Features:** 36 (rolling features now use .shift(1) to exclude current value)
- **Tuning:** Optuna 30 trials, 50% subsample
- **Best model:** XGBoost (tuned), R² = 0.514
- **Overfitting gap:** 0.0007 (essentially zero)
- **Change from iteration 2:** Rolling features shifted by 1 hour. R² dropped from 0.742 to 0.514, confirming the leaky rolling features were responsible for ~0.23 R² points of artificial performance.
- **Top features:** load_lag_1h (28.9%), load_roll_mean_7d (12.1%), load_roll_std_7d (9.9%), load_roll_mean_6h (9.4%)
