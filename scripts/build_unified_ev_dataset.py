# %% [markdown]
# # Unified EV Dataset Builder
#
# This notebook-style script builds a unified modeling dataset from the raw PlusDR EV files.
# It creates:
#
# 1. `data/processed/ev_unified_15min.parquet`
# 2. `data/processed/ev_unified_hourly.parquet`
# 3. `data/processed/ev_station_build_summary.csv`
#
# Design choices:
#
# - Read each station CSV separately to avoid loading all 873 files into memory.
# - Write directly to Parquet with `pyarrow` so the full dataset stays manageable.
# - Keep both raw and cleaned load values.
# - Attach participant/location metadata to every row.
# - Annotate quarter-hour and hourly records with DR event flags and hourly DR performance.

# %%
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


# %% [markdown]
# ## Configuration

# %%
PROJECT_ROOT = Path.cwd().resolve()
if not (PROJECT_ROOT / "data").exists():
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

LOAD_DIR = RAW_DIR / "PlusDR_Participant_Load_Data"
PARTICIPANT_PATH = RAW_DIR / "PlusDR_Participant_Info.xlsx"
LOCATION_PATH = RAW_DIR / "PlusDR_Location_Info.xlsx"
PERFORMANCE_PATH = RAW_DIR / "PlusDR_Performance_Info.xlsx"

LOAD_UPPER_BOUND_MULTIPLIER = 1.20

# Optional environment overrides for smoke tests:
# MAX_STATIONS=10 python scripts/build_unified_ev_dataset.py
MAX_STATIONS = int(os.getenv("MAX_STATIONS", "0")) or None
OVERWRITE_OUTPUTS = os.getenv("OVERWRITE_OUTPUTS", "1") == "1"

OUTPUT_TAG = f"_sample_{MAX_STATIONS}" if MAX_STATIONS else ""
MASTER_15MIN_PATH = PROCESSED_DIR / f"ev_unified_15min{OUTPUT_TAG}.parquet"
MASTER_HOURLY_PATH = PROCESSED_DIR / f"ev_unified_hourly{OUTPUT_TAG}.parquet"
SUMMARY_PATH = PROCESSED_DIR / f"ev_station_build_summary{OUTPUT_TAG}.csv"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

assert LOAD_DIR.exists(), f"Missing load directory: {LOAD_DIR}"
assert PARTICIPANT_PATH.exists(), f"Missing file: {PARTICIPANT_PATH}"
assert LOCATION_PATH.exists(), f"Missing file: {LOCATION_PATH}"
assert PERFORMANCE_PATH.exists(), f"Missing file: {PERFORMANCE_PATH}"

print(f"Project root: {PROJECT_ROOT}")
print(f"Raw data directory: {RAW_DIR}")
print(f"Processed data directory: {PROCESSED_DIR}")
print(f"MAX_STATIONS: {MAX_STATIONS}")


# %% [markdown]
# ## Helpers

# %%
STRING_COLUMNS = [
    "public_private",
    "business_type",
    "contract_type",
    "detailed_type",
    "participate_program",
    "province",
    "city",
    "address",
]

METADATA_COLUMNS = [
    "public_private",
    "business_type",
    "contract_type",
    "detailed_type",
    "contract_power_kw",
    "total_quantity",
    "charger_7kw",
    "charger_8kw",
    "other_slow_charger",
    "charger_50kw",
    "other_fast_charger",
    "participate_program",
    "province",
    "city",
    "address",
]


def standardize_time_label(label: object) -> str:
    """Normalize time headers like 0:00 -> 00:00."""
    text = str(label).strip().replace("`", "")
    parts = text.split(":")
    if len(parts) >= 2:
        try:
            return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
        except ValueError:
            return text
    return text


def sum_or_na(series: pd.Series) -> float:
    """Preserve missingness when all values are NaN."""
    return series.sum(min_count=1)


def remove_if_needed(path: Path) -> None:
    if OVERWRITE_OUTPUTS and path.exists():
        path.unlink()


def format_bytes(path: Path) -> str:
    if not path.exists():
        return "missing"
    size = path.stat().st_size
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


# %% [markdown]
# ## Load Metadata

# %%
def load_station_metadata() -> pd.DataFrame:
    participant = pd.read_excel(PARTICIPANT_PATH).rename(
        columns={
            "Customer ID": "customer_id",
            "Public/Private": "public_private",
            "Business Type": "business_type",
            "Contract Type": "contract_type",
            "Detailed Type": "detailed_type",
            "Contract Power (kW)": "contract_power_kw",
            "Total Quantity": "total_quantity",
            "7kW Charger": "charger_7kw",
            "8kW Charger": "charger_8kw",
            "Other Slow Charger": "other_slow_charger",
            "50kW Charger": "charger_50kw",
            "Other Fast Charger": "other_fast_charger",
        }
    )

    location = pd.read_excel(LOCATION_PATH).rename(
        columns={
            "Customer ID": "customer_id",
            "Participate Program": "participate_program",
            "Province": "province",
            "City": "city",
            "Address": "address",
        }
    )

    location = location[["customer_id", "participate_program", "province", "city", "address"]]

    meta = participant.merge(location, on="customer_id", how="left", validate="one_to_one")

    meta["customer_id"] = pd.to_numeric(meta["customer_id"], errors="raise").astype("int64")
    meta["contract_power_kw"] = pd.to_numeric(meta["contract_power_kw"], errors="coerce").astype("float32")

    for col in [
        "total_quantity",
        "charger_7kw",
        "charger_8kw",
        "other_slow_charger",
        "charger_50kw",
        "other_fast_charger",
    ]:
        meta[col] = pd.to_numeric(meta[col], errors="coerce").astype("Int16")

    for col in STRING_COLUMNS:
        meta[col] = meta[col].astype("string")

    return meta.sort_values("customer_id").reset_index(drop=True)


def load_dr_annotations() -> pd.DataFrame:
    xls = pd.ExcelFile(PERFORMANCE_PATH)
    frames = []

    for sheet_name in xls.sheet_names:
        frame = pd.read_excel(PERFORMANCE_PATH, sheet_name=sheet_name).rename(
            columns={
                "Customer ID": "customer_id",
                "Event Date": "event_date",
                "Event Time": "event_time",
                "Performance (kWh)": "dr_performance_kwh_hourly",
            }
        )
        frame["source_sheet"] = sheet_name
        frames.append(frame)

    dr = pd.concat(frames, ignore_index=True)
    dr["customer_id"] = pd.to_numeric(dr["customer_id"], errors="coerce").astype("Int64")
    dr["event_date"] = pd.to_numeric(dr["event_date"], errors="coerce").astype("Int64")
    dr["event_time"] = pd.to_numeric(dr["event_time"], errors="coerce")
    dr["dr_performance_kwh_hourly"] = pd.to_numeric(
        dr["dr_performance_kwh_hourly"], errors="coerce"
    ).astype("float32")

    dr = dr.dropna(subset=["customer_id", "event_date", "event_time"]).copy()
    dr["event_time"] = dr["event_time"].astype("int16")
    dr["event_hour_ts"] = (
        pd.to_datetime(dr["event_date"].astype(str), format="%Y%m%d", errors="coerce")
        + pd.to_timedelta(dr["event_time"], unit="h")
    )
    dr = dr.dropna(subset=["event_hour_ts"]).copy()

    annotations = (
        dr.groupby(["customer_id", "event_hour_ts"], as_index=False)
        .agg(
            dr_performance_kwh_hourly=("dr_performance_kwh_hourly", "sum"),
            dr_record_count=("dr_performance_kwh_hourly", "size"),
        )
        .sort_values(["customer_id", "event_hour_ts"])
        .reset_index(drop=True)
    )

    annotations["customer_id"] = annotations["customer_id"].astype("int64")
    annotations["dr_performance_kwh_hourly"] = annotations["dr_performance_kwh_hourly"].astype(
        "float32"
    )
    annotations["dr_record_count"] = annotations["dr_record_count"].astype("Int16")
    annotations["is_dr_event"] = True

    return annotations


station_meta = load_station_metadata()
dr_annotations = load_dr_annotations()

meta_lookup = station_meta.set_index("customer_id")
dr_lookup = {
    customer_id: frame.drop(columns=["customer_id"]).reset_index(drop=True)
    for customer_id, frame in dr_annotations.groupby("customer_id")
}

print(f"Stations in metadata: {len(station_meta):,}")
print(f"Unique stations with DR records: {len(dr_lookup):,}")
print(f"Distinct DR station-hour annotations: {len(dr_annotations):,}")


# %% [markdown]
# ## Build Functions

# %%
def build_station_quarter_hour_df(
    load_path: Path,
    meta_row: pd.Series,
    station_dr: pd.DataFrame | None,
) -> pd.DataFrame:
    customer_id = int(load_path.stem)

    wide = pd.read_csv(load_path, skiprows=1)
    first_col = wide.columns[0]
    wide = wide.rename(columns={first_col: "date_yyyymmdd"})
    wide = wide.rename(columns={col: standardize_time_label(col) for col in wide.columns[1:]})

    long = wide.melt(
        id_vars="date_yyyymmdd",
        var_name="time_label",
        value_name="load_kwh_raw",
    )

    long["customer_id"] = customer_id
    long["date"] = pd.to_datetime(long["date_yyyymmdd"].astype(str), format="%Y%m%d", errors="coerce")
    long["timestamp"] = pd.to_datetime(
        long["date"].dt.strftime("%Y-%m-%d") + " " + long["time_label"],
        errors="coerce",
    )
    long["timestamp_hour"] = long["timestamp"].dt.floor("h")

    long["load_kwh_raw"] = pd.to_numeric(long["load_kwh_raw"], errors="coerce").astype("float32")
    long["load_missing_original"] = long["load_kwh_raw"].isna()

    contract_power_kw = float(meta_row["contract_power_kw"]) if pd.notna(meta_row["contract_power_kw"]) else np.nan
    load_cap = contract_power_kw * 0.25 * LOAD_UPPER_BOUND_MULTIPLIER if pd.notna(contract_power_kw) else np.nan

    long["load_flag_negative"] = long["load_kwh_raw"] < 0
    if pd.isna(load_cap):
        long["load_flag_above_contract_cap"] = False
    else:
        long["load_flag_above_contract_cap"] = long["load_kwh_raw"] > load_cap

    invalid_mask = long["load_flag_negative"] | long["load_flag_above_contract_cap"]
    long["load_kwh"] = long["load_kwh_raw"].mask(invalid_mask).astype("float32")

    if station_dr is not None and not station_dr.empty:
        long = long.merge(
            station_dr,
            how="left",
            left_on="timestamp_hour",
            right_on="event_hour_ts",
        ).drop(columns=["event_hour_ts"])
    else:
        long["dr_performance_kwh_hourly"] = np.nan
        long["dr_record_count"] = pd.Series(pd.NA, index=long.index, dtype="Int16")
        long["is_dr_event"] = False

    long["is_dr_event"] = long["is_dr_event"].eq(True)
    long["dr_performance_kwh_hourly"] = pd.to_numeric(
        long["dr_performance_kwh_hourly"], errors="coerce"
    ).astype("float32")
    long["dr_record_count"] = pd.to_numeric(long["dr_record_count"], errors="coerce").astype("Int16")

    for col in METADATA_COLUMNS:
        long[col] = meta_row[col]

    quarter_cols = [
        "customer_id",
        "timestamp",
        "timestamp_hour",
        "load_kwh_raw",
        "load_kwh",
        "load_missing_original",
        "load_flag_negative",
        "load_flag_above_contract_cap",
        "is_dr_event",
        "dr_performance_kwh_hourly",
        "dr_record_count",
    ] + METADATA_COLUMNS

    quarter_df = long[quarter_cols].copy()

    quarter_df["customer_id"] = quarter_df["customer_id"].astype("int64")
    quarter_df["load_kwh_raw"] = quarter_df["load_kwh_raw"].astype("float32")
    quarter_df["load_kwh"] = quarter_df["load_kwh"].astype("float32")
    quarter_df["dr_performance_kwh_hourly"] = quarter_df["dr_performance_kwh_hourly"].astype("float32")
    quarter_df["contract_power_kw"] = pd.to_numeric(quarter_df["contract_power_kw"], errors="coerce").astype(
        "float32"
    )

    for col in [
        "total_quantity",
        "charger_7kw",
        "charger_8kw",
        "other_slow_charger",
        "charger_50kw",
        "other_fast_charger",
    ]:
        quarter_df[col] = pd.to_numeric(quarter_df[col], errors="coerce").astype("Int16")

    for col in STRING_COLUMNS:
        quarter_df[col] = quarter_df[col].astype("string")

    return quarter_df


def build_station_hourly_df(quarter_df: pd.DataFrame) -> pd.DataFrame:
    customer_id = int(quarter_df["customer_id"].iat[0])

    hourly = (
        quarter_df.groupby(["customer_id", "timestamp_hour"], as_index=False)
        .agg(
            load_kwh_hourly=("load_kwh", sum_or_na),
            load_kwh_raw_hourly=("load_kwh_raw", sum_or_na),
            observed_quarters=("load_kwh", "count"),
            is_dr_event=("is_dr_event", "max"),
            dr_performance_kwh_hourly=("dr_performance_kwh_hourly", "first"),
        )
        .sort_values(["customer_id", "timestamp_hour"])
        .reset_index(drop=True)
    )

    hourly["missing_quarters"] = (4 - hourly["observed_quarters"]).clip(lower=0).astype("Int8")
    hourly["observed_quarters"] = hourly["observed_quarters"].astype("Int8")
    hourly["load_kwh_hourly"] = hourly["load_kwh_hourly"].astype("float32")
    hourly["load_kwh_raw_hourly"] = hourly["load_kwh_raw_hourly"].astype("float32")
    hourly["dr_performance_kwh_hourly"] = hourly["dr_performance_kwh_hourly"].astype("float32")

    meta_values = quarter_df.iloc[0][METADATA_COLUMNS]
    for col in METADATA_COLUMNS:
        hourly[col] = meta_values[col]

    hourly["customer_id"] = hourly["customer_id"].astype("int64")
    hourly["contract_power_kw"] = pd.to_numeric(hourly["contract_power_kw"], errors="coerce").astype("float32")

    for col in [
        "total_quantity",
        "charger_7kw",
        "charger_8kw",
        "other_slow_charger",
        "charger_50kw",
        "other_fast_charger",
    ]:
        hourly[col] = pd.to_numeric(hourly[col], errors="coerce").astype("Int16")

    for col in STRING_COLUMNS:
        hourly[col] = hourly[col].astype("string")

    hourly_cols = [
        "customer_id",
        "timestamp_hour",
        "load_kwh_hourly",
        "load_kwh_raw_hourly",
        "observed_quarters",
        "missing_quarters",
        "is_dr_event",
        "dr_performance_kwh_hourly",
    ] + METADATA_COLUMNS

    return hourly[hourly_cols]


def make_station_summary(quarter_df: pd.DataFrame) -> dict:
    return {
        "customer_id": int(quarter_df["customer_id"].iat[0]),
        "rows_total": int(len(quarter_df)),
        "raw_non_null_rows": int(quarter_df["load_kwh_raw"].notna().sum()),
        "cleaned_non_null_rows": int(quarter_df["load_kwh"].notna().sum()),
        "load_valid_ratio": float(quarter_df["load_kwh"].notna().mean()),
        "negative_flag_count": int(quarter_df["load_flag_negative"].sum()),
        "above_contract_cap_count": int(quarter_df["load_flag_above_contract_cap"].sum()),
        "dr_event_quarter_rows": int(quarter_df["is_dr_event"].sum()),
        "dr_event_hour_count": int(quarter_df.loc[quarter_df["is_dr_event"], "timestamp_hour"].nunique()),
        "start_timestamp": quarter_df["timestamp"].min(),
        "end_timestamp": quarter_df["timestamp"].max(),
    }


# %% [markdown]
# ## Build the Unified Datasets

# %%
remove_if_needed(MASTER_15MIN_PATH)
remove_if_needed(MASTER_HOURLY_PATH)
remove_if_needed(SUMMARY_PATH)

load_files = sorted(LOAD_DIR.glob("*.csv"))
if MAX_STATIONS is not None:
    load_files = load_files[:MAX_STATIONS]

writer_15min = None
writer_hourly = None
station_summaries = []

for idx, load_path in enumerate(load_files, start=1):
    customer_id = int(load_path.stem)

    if customer_id not in meta_lookup.index:
        print(f"[skip] Missing metadata for {customer_id}")
        continue

    meta_row = meta_lookup.loc[customer_id]
    station_dr = dr_lookup.get(customer_id)

    quarter_df = build_station_quarter_hour_df(load_path, meta_row, station_dr)
    hourly_df = build_station_hourly_df(quarter_df)

    table_15min = pa.Table.from_pandas(quarter_df, preserve_index=False)
    table_hourly = pa.Table.from_pandas(hourly_df, preserve_index=False)

    if writer_15min is None:
        writer_15min = pq.ParquetWriter(MASTER_15MIN_PATH, table_15min.schema, compression="snappy")
    if writer_hourly is None:
        writer_hourly = pq.ParquetWriter(MASTER_HOURLY_PATH, table_hourly.schema, compression="snappy")

    writer_15min.write_table(table_15min)
    writer_hourly.write_table(table_hourly)
    station_summaries.append(make_station_summary(quarter_df))

    if idx == 1 or idx % 50 == 0 or idx == len(load_files):
        print(f"Processed {idx:,} / {len(load_files):,} stations")

if writer_15min is not None:
    writer_15min.close()
if writer_hourly is not None:
    writer_hourly.close()

summary_df = pd.DataFrame(station_summaries).sort_values("customer_id").reset_index(drop=True)
summary_df.to_csv(SUMMARY_PATH, index=False)

print("\nBuild complete.")
print(f"15-minute dataset: {MASTER_15MIN_PATH} ({format_bytes(MASTER_15MIN_PATH)})")
print(f"Hourly dataset:    {MASTER_HOURLY_PATH} ({format_bytes(MASTER_HOURLY_PATH)})")
print(f"Station summary:   {SUMMARY_PATH} ({format_bytes(SUMMARY_PATH)})")


# %% [markdown]
# ## Quick Validation

# %%
summary_df = pd.read_csv(SUMMARY_PATH)
summary_df.head()


# %%
print(summary_df[["rows_total", "raw_non_null_rows", "cleaned_non_null_rows", "load_valid_ratio"]].describe())
print(f"\nRows in station summary: {len(summary_df):,}")


# %%
hourly_preview = pd.read_parquet(MASTER_HOURLY_PATH).head(10)
hourly_preview
