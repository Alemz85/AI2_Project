# AI2 Project — EV Charging Load Forecasting

Demand response and load forecasting for EV charging stations on Jeju Island, South Korea, using the PlusDR dataset (873 stations, Jan 2021 – Dec 2022).

## Project layout

```
data/
├── raw/          # Original source files (not tracked by git)
├── interim/      # Intermediate outputs: unified parquets, station summary, coordinates
└── processed/    # Final model-ready datasets only

scripts/
├── 01 - Merge Raw.ipynb          # Reshape + merge 873 CSVs and metadata into unified parquets
├── 02 - Geocode Stations.ipynb   # Geocode station addresses → station_coordinates.csv (run once)
├── 02 - Data Cleaning.ipynb      # Clean hourly dataset: filtering, imputation, outlier flags, time features
└── 03 - EDA.ipynb                # Exploratory analysis: temporal patterns, station variation, map, DR analysis

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
   - `01 - Merge Raw` → builds `data/interim/ev_unified_hourly.parquet` and `ev_unified_15min.parquet`
   - `02 - Geocode Stations` → builds `data/interim/station_coordinates.csv` (one-time, ~15 min)
   - `02 - Data Cleaning` → builds `data/processed/ev_cleaned_hourly.parquet`
   - `03 - EDA` → exploratory analysis on the cleaned dataset

## Dataset

- **Source:** PlusDR — 873 EV charging stations, Jeju Island, South Korea
- **Period:** January 2021 – December 2022
- **Primary dataset:** hourly resolution (`ev_cleaned_hourly.parquet`) — 586 usable stations, 39 columns
- **Backup:** 15-minute resolution (`ev_unified_15min.parquet`) — kept for detailed analysis if needed

## Git workflow notes

- Raw data and generated parquet files are not tracked by git.
- Notebook checkpoints, OS clutter, and virtual environments are ignored.
- If you decide to version large datasets, prefer Git LFS over regular commits.
