# AI2 Project — EV Charging Load Forecasting

Demand response and load forecasting for EV charging stations on Jeju Island, South Korea, using the PlusDR dataset (873 stations, Jan 2021 – Dec 2022).

## Project layout

```
data/
├── raw/          # Original source files (not tracked by git)
├── interim/      # Intermediate outputs: unified parquets, station summary, coordinates
└── processed/    # Final model-ready datasets only

scripts/
├── 00 - Merge Raw.ipynb          # Reshape + merge 873 CSVs and metadata into unified parquets
├── 00 - Geocode Stations.ipynb   # Geocode station addresses → station_coordinates.csv (run once)
├── 01 - Data Cleaning.ipynb      # Clean hourly dataset: filtering, imputation, outlier flags, time features
├── 02 - Weather Data.ipynb       # Fetch hourly weather from Open-Meteo and join to EV dataset
├── 03 - EDA.ipynb                # Exploratory analysis: temporal patterns, station variation, map, DR analysis
└── 04 - Feature Engineering.ipynb # Build model-ready features: cyclical time, lags, rolling stats, encoding

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
   - `00 - Merge Raw` → builds `data/interim/ev_unified_hourly.parquet` and `ev_unified_15min.parquet`
   - `00 - Geocode Stations` → builds `data/interim/station_coordinates.csv` (one-time, ~15 min)
   - `01 - Data Cleaning` → builds `data/processed/ev_cleaned_hourly.parquet`
   - `02 - Weather Data` → builds `data/processed/ev_cleaned_hourly_weather.parquet`
   - `03 - EDA` → exploratory analysis on the cleaned dataset
   - `04 - Feature Engineering` → builds `data/processed/ev_features.parquet`

## Dataset

- **Source:** PlusDR — 873 EV charging stations, Jeju Island, South Korea
- **Period:** January 2021 – December 2022
- **Primary dataset:** hourly resolution with weather (`ev_cleaned_hourly_weather.parquet`) — 586 stations, 45 columns
- **Model-ready:** feature-engineered (`ev_features.parquet`) — lag features, cyclical time, encoded categoricals
- **Backup:** 15-minute resolution (`ev_unified_15min.parquet`) — kept for detailed analysis if needed

## Git workflow notes

- Raw data and generated parquet files are not tracked by git.
- Notebook checkpoints, OS clutter, and virtual environments are ignored.
- If you decide to version large datasets, prefer Git LFS over regular commits.
