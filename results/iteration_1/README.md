## Iteration 1 — Original Model

- **Stations:** 586 (including 1 residential)
- **Features:** 31 (with leaky rolling features)
- **Best model:** XGBoost (tuned), R² = 0.827
- **Issue found:** `contract_type_code` dominated feature importance at 88%, driven by a single residential station (ID 811236417, mean load 132.59 kWh) among 585 commercial stations (mean load 38.04 kWh)
- **Note:** Model files were overwritten before iteration tracking was implemented. Metrics are recorded from notebook outputs.
