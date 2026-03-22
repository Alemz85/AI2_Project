> **Note:** Only update this file when a new notebook is added or its core purpose changes. Do not document structural, folder, or config changes here.

---

# Project Progress

## Dataset
- **Source:** PlusDR dataset — 873 EV charging stations in South Korea (Jan 2021 – Dec 2022)
- **Raw format:** 873 individual CSV files (one per station) + 3 Excel metadata files
- **Resolution:** hourly aggregated
- **Primary dataset for modeling:** `ev_cleaned_hourly_weather.parquet` (weather-joined)
- **Model-ready:** `ev_features.parquet` (33 features, ~7.3M rows)
- **Note:** One residential station (ID 811236417) was excluded — see notebook 07 for analysis

## Notebooks

### 00 - Merge Raw
Takes the raw data (873 separate CSVs + metadata Excel files) and combines everything into a unified hourly parquet dataset. Each station CSV is reshaped from wide format (one row per day, 96 columns for each 15-min slot) into a proper time series, then aggregated to hourly. Station metadata (location, charger info, business type) and demand response event records are merged in.

### 00 - Geocode Stations
One-time notebook that geocodes the 873 station addresses using Nominatim (free, no API key). Saves results to `data/interim/station_coordinates.csv`. Resume-aware — if interrupted, re-running skips already-geocoded stations. Stations on outlying islands (Udo, Chuja) are handled and flagged separately.

### 01 - Data Cleaning
Takes the unified hourly dataset and produces a clean, model-ready version. Drops stations with too much missing data (287 dropped) and one residential station (ID 811236417) that is not comparable to the 585 commercial stations. Handles gaps and partial hours, flags outliers, and adds time-based features (hour, day of week, season, holidays, etc.).

### 02 - Weather Data
Pulls historical hourly weather from Open-Meteo for two locations on Jeju Island (Jeju-Si and Seogwipo-Si) to capture the microclimate difference caused by Mt. Hallasan. Variables: temperature, humidity, precipitation, wind speed, cloud cover. Each station is joined to its city's weather by hour. Saves raw weather to interim and the joined EV+weather dataset to processed.

### 03 - EDA
Exploratory analysis on the cleaned hourly dataset. Covers temporal patterns (hourly, daily, seasonal, year-over-year), station-level variation, spatial distribution map of stations on Jeju Island (with real map tiles via contextily), load distribution, demand response event analysis, and feature correlations. Ends with a key takeaways section to inform feature engineering and modeling decisions.

### 04 - Feature Engineering
Takes the weather-joined dataset and produces a lean, model-ready parquet. Drops NaN rows and DR hours, caps extreme outliers, encodes time features as cyclical sin/cos pairs, builds per-station lag features (1h, 2h, 3h, 24h) and rolling statistics (6h, 12h, 24h, 7-day mean/std), label-encodes categoricals, normalizes station attributes, and drops all unused columns. Output is ready for modeling.

## Next Steps
- Model training and evaluation
