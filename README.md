# AI2 Project — EV Charging Load Forecasting

Demand response and load forecasting for EV charging stations on Jeju Island, South Korea, using the PlusDR dataset (873 stations, Jan 2021 – Dec 2022).

## Project layout

```
data/
├── raw/          # Original source files (not tracked by git)
├── interim/      # Intermediate outputs: unified hourly parquet, station summary, coordinates, weather
└── processed/    # Final datasets: cleaned, weather-joined, feature-engineered

scripts/
├── 00 - Merge Raw.ipynb            # Reshape + merge 873 CSVs and metadata into unified hourly parquet
├── 00 - Geocode Stations.ipynb     # Geocode station addresses → station_coordinates.csv (run once)
├── 01 - Data Cleaning.ipynb        # Clean hourly dataset: filtering, imputation, outlier flags, time features
├── 02 - Weather Data.ipynb         # Fetch hourly weather from Open-Meteo and join to EV dataset
├── 03 - EDA.ipynb                  # Exploratory analysis: temporal patterns, station variation, map, DR analysis
├── 04 - Feature Engineering.ipynb  # Build model-ready features: cyclical time, lags, rolling stats, encoding
├── 05 - Modeling (Baseline).ipynb  # Baseline models: persistence, station mean, Ridge, LightGBM, XGBoost
├── 06 - Modeling (Tuned).ipynb     # Optuna hyperparameter tuning for LightGBM and XGBoost
├── 07 - Summary & Error Analysis.ipynb  # Overfitting check, feature importance, error analysis (regression)
├── 08 - Modeling (Classification).ipynb # Classification reframing: predict demand level (Idle/Low/Medium/High)
└── 09 - Classification Error Analysis.ipynb  # Classification error analysis: confusion matrix, confidence, comparison

results/          # Model outputs (not tracked by git)
├── iteration_1/  # Original model (with residential station, leaky rolling)
├── iteration_2/  # Dropped residential station + new features
├── iteration_3/  # Fixed rolling feature leakage (final regression)
├── iteration_4/  # Classification reframing (Idle/Low/Medium/High)
└── iterations_summary.csv

guide/
└── progress.md   # High-level summary of what each notebook does
```

## Getting started

1. Clone the repository.
2. Install dependencies with either:
   - `pip install -r requirements.txt`
   - `conda env create -f environment.yml` then `conda activate ai2-project`
3. Place the source data in `data/raw/`.
4. Run the notebooks in order:
   - `00 - Merge Raw` → builds `data/interim/ev_unified_hourly.parquet`
   - `00 - Geocode Stations` → builds `data/interim/station_coordinates.csv` (one-time, ~15 min)
   - `01 - Data Cleaning` → builds `data/processed/ev_cleaned_hourly.parquet`
   - `02 - Weather Data` → builds `data/processed/ev_cleaned_hourly_weather.parquet`
   - `03 - EDA` → exploratory analysis on the cleaned dataset
   - `04 - Feature Engineering` → builds `data/processed/ev_features.parquet`
   - `05 - Modeling (Baseline)` → trains 5 models with defaults, saves to `results/`
   - `06 - Modeling (Tuned)` → Optuna tuning, final comparison of all 7 models
   - `07 - Summary & Error Analysis` → overfitting check, feature importance, error analysis (regression)
   - `08 - Modeling (Classification)` → classification models: predict demand level
   - `09 - Classification Error Analysis` → classification error analysis and regression comparison

## Dataset

- **Source:** [PlusDR — EV Charging Infrastructure & Demand Response Dataset (Figshare)](https://figshare.com/articles/dataset/EV_charging_infrastructure_demand_response_dataset_integrated_operational_and_market_data_from_Jeju_island/29617100) — 873 EV charging stations, Jeju Island, South Korea
- **Period:** January 2021 – December 2022
- **Primary dataset:** hourly resolution with weather (`ev_cleaned_hourly_weather.parquet`) — 585 stations, 45 columns
- **Model-ready:** feature-engineered (`ev_features.parquet`) — 36 features, ~7.2M rows

## Results

| Model | MAE (kWh) | RMSE (kWh) | R² |
|-------|-----------|------------|-----|
| Persistence (lag 24h) | 3.79 | 8.74 | -0.038 |
| Station Hourly Mean | 3.25 | 6.58 | 0.412 |
| Ridge Regression | 3.14 | 6.28 | 0.463 |
| LightGBM (default) | 2.76 | 5.99 | 0.513 |
| XGBoost (default) | 2.76 | 5.99 | 0.512 |
| LightGBM (tuned) | 2.78 | 6.00 | 0.510 |
| **XGBoost (tuned)** | **2.76** | **5.98** | **0.514** |

Train/test split: Jan 2021 – Jun 2022 / Jul – Dec 2022 (65/35). No overfitting (R² gap = 0.001).

### Model iterations

| Iteration | R² | Change | Key finding |
|---|---|---|---|
| 1 | 0.827 | Original | `contract_type_code` dominated feature importance at 88% — one residential station inflating metrics |
| 2 | 0.742 | Dropped residential station | Feature importance balanced, `load_roll_mean_6h` leads at 36% |
| 3 | 0.514 | Fixed rolling feature leakage | Rolling features were contributing ~0.23 R² through data leakage |
| 4 | 81% acc | Classification reframing | Demand-level prediction: Idle F1=0.92, macro F1=0.67, zero overfitting |

## Git workflow notes

- Raw data, processed parquets, and model results are not tracked by git.
- Notebook checkpoints, OS clutter, and virtual environments are ignored.
