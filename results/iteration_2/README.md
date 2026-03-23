## Iteration 2 — Dropped Residential Station + New Features

- **Stations:** 585 (residential station 811236417 removed)
- **Features:** 36 (added load_lag_168h, load_change_1h, load_ratio_24h, hour_x_weekend, is_cold)
- **Tuning:** Optuna 50 trials, 60% subsample
- **Best model:** XGBoost (tuned), R² = 0.742
- **Change from iteration 1:** Removing the residential station eliminated the contract_type dominance. Feature importance now led by load_roll_mean_6h (35.9%) and hour_cos (10.0%).
- **Rolling features still include current value (leaky)**
