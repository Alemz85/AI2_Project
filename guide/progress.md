> **Note:** Only update this file when a new notebook is added or its core purpose changes. Do not document structural, folder, or config changes here.

---

# Project Progress

## Dataset
- **Source:** PlusDR dataset — 873 EV charging stations in South Korea (Jan 2021 – Dec 2022)
- **Raw format:** 873 individual CSV files (one per station) + 3 Excel metadata files
- **Two resolutions available:** 15-minute intervals and hourly aggregated
- **Primary dataset for modeling:** hourly (`ev_cleaned_hourly.parquet`)
- **Backup / detailed analysis:** 15-minute (`ev_unified_15min.parquet`)

## Notebooks

### 01 - Merge Raw
Takes the raw data (873 separate CSVs + metadata Excel files) and combines everything into two unified parquet datasets (15-min and hourly). Each station CSV is reshaped from wide format (one row per day, 96 columns for each 15-min slot) into a proper time series. Station metadata (location, charger info, business type) and demand response event records are merged in.

### 02 - Geocode Stations
One-time notebook that geocodes the 873 station addresses using Nominatim (free, no API key). Saves results to `data/interim/station_coordinates.csv`. Resume-aware — if interrupted, re-running skips already-geocoded stations. Stations on outlying islands (Udo, Chuja) are handled and flagged separately.

### 02 - Data Cleaning
Takes the unified hourly dataset and produces a clean, model-ready version. Drops stations with too much missing data (287 dropped, 586 kept), handles gaps and partial hours, flags outliers, and adds time-based features (hour, day of week, season, holidays, etc.).

### 03 - EDA
Exploratory analysis on the cleaned hourly dataset. Covers temporal patterns (hourly, daily, seasonal, year-over-year), station-level variation, spatial distribution map of stations on Jeju Island, load distribution, demand response event analysis, and feature correlations. Ends with a key takeaways section to inform feature engineering and modeling decisions.

## Next Steps
- Weather data collection and join (Open-Meteo API for Jeju, Jan 2021 – Dec 2022)
- Feature engineering (04 - Feature Engineering)
- Model training and evaluation (05 - Modeling)
