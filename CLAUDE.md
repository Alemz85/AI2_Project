# CLAUDE.md

This file provides guidance when working on this project in any AI-assisted session.

## Project Overview

ESADE AI II Final Project: **EV Charging Load Forecasting** using the PlusDR (Demand Response) dataset from Jeju, South Korea. The goal is to predict hourly electricity consumption (kWh) at EV charging stations using supervised regression — supporting grid operators in scheduling DR events.

**Deliverables:**
- Jupyter notebook (`ev_load_forecasting.ipynb`) — code + analysis
- 3-page written report
- 5-minute in-class presentation + 5-minute Q&A

## Project Status

| Deliverable | Status |
|---|---|
| Jupyter notebook | ✅ Complete |
| requirements.txt | ✅ Complete |
| 3-page written report | ⏳ Not started |
| 5-minute presentation (.pptx) | ⏳ Not started |

## Grading Criteria

The assignment is evaluated on these six criteria — every design decision and piece of writing should be optimised against them:

1. **Clarity of problem formulation** — is the business problem, target variable, and prediction task clearly stated?
2. **Appropriateness of data and modeling choices** — are the dataset and models well-chosen and justified?
3. **Rigor of training and evaluation** — is the methodology sound (temporal split, baselines, multiple metrics)?
4. **Reasoning and justification regarding evaluation metrics and their relevance to real-world objectives** — do we explain *why* each metric matters in the DR context, not just report the numbers?
5. **Depth of critical reflection** — are limitations, risks, and gaps honestly and thoroughly discussed?
6. **Overall clarity and organization** — is the work easy to follow and well-structured?

> **Important:** The Q&A session after the presentation weighs heavily on the grade. Riwad should be prepared to explain every design decision in the notebook verbally.

## Environment Setup

The project uses a **micromamba** environment called `ai2`.

```bash
# Activate the environment
micromamba activate ai2

# Install dependencies (from project root)
pip install -r requirements.txt

# Run the notebook
jupyter notebook ev_load_forecasting.ipynb
```

## Data Pipeline

```
data/raw/                          → 873 station CSVs + Excel metadata files
  ├── PlusDR_Participant_Load_Data/   15-min load readings per station
  ├── PlusDR_Participant_Info.xlsx    station metadata (charger types, contract power)
  ├── PlusDR_Location_Info.xlsx       station coordinates/addresses
  └── PlusDR_Performance_Info.xlsx    DR event performance

data/interim/                      → merged/resampled intermediate files
  ├── ev_unified_15min.parquet        all stations merged at 15-min resolution
  ├── ev_unified_hourly.parquet       resampled to hourly
  ├── jeju_weather_hourly.parquet     Jeju weather data (temp, humidity, precip, wind, cloud)
  └── *_sample_3.parquet              3-station subsets for fast iteration

data/processed/                    → model-ready datasets
  ├── ev_cleaned_hourly.parquet       cleaned + imputed hourly load with engineered features
  └── ev_cleaned_hourly_weather.parquet  ↑ merged with weather (~10M rows, used by notebook)
```

The notebook loads `data/processed/ev_cleaned_hourly_weather.parquet` and samples stations
for the pilot study. Due to batch-reading from the first 200K rows, the actual number of
sampled stations is ~12 (not 30 — the first batch doesn't contain all 873 station IDs).

## Notebook Structure

1. **Problem Definition** — business context, 1-hour-ahead forecast framing, target variable (`load_kwh_clean`), task framing
2. **Setup & Imports** — numpy, pandas, sklearn, xgboost, matplotlib, seaborn
3. **Data Loading** — parquet read with pyarrow, station sample (seed=42)
4. **EDA** — target distribution, temporal patterns (hour/day/month), weather correlations, station types
5. **Feature Engineering** — 17 numeric + 3 categorical features (time, weather, station metadata); label encoding
6. **Train/Test Split** — temporal (chronological) 80/20 split, no random shuffling
7. **Modelling** — Naive Mean Baseline → Ridge Regression → Random Forest → XGBoost
8. **Evaluation** — MAE, RMSE, R², MAPE (≥1 kWh filter); results contextualised against baseline and benchmarks; feature importance; actual vs predicted plots
9. **Critical Reflection** — construct validity, asymmetric loss, distributional shift, fairness, pilot limitations

## Key Design Decisions

- **1-hour-ahead static forecast** — prediction horizon is the next hour, using only features available at hour *t*
- **Static features only** (no lag/autoregressive terms) — deliberate pilot scope choice, discussed in Critical Reflection
- **Naive mean baseline included** — DummyRegressor provides an R²=0 floor so ML model improvements are clearly visible
- **ARIMA/LSTM excluded** — ARIMA can't natively handle multi-station + multivariate inputs; XGBoost matches LSTM performance on tabular data with far less complexity
- **Temporal split** over random split to avoid data leakage in time-series
- **MAPE filtered to load ≥ 1 kWh** to avoid division-by-near-zero on idle hours
- **Negative predictions clamped to 0** for Ridge (physical constraint: load cannot be negative)
- **Tree models (RF, XGBoost) use unscaled features; Ridge uses StandardScaler**

## Tech Stack

- Python 3, Jupyter
- pandas, numpy, pyarrow (data handling)
- scikit-learn (Ridge, RandomForest, DummyRegressor, preprocessing, metrics)
- xgboost (XGBRegressor)
- matplotlib, seaborn (visualisation)
