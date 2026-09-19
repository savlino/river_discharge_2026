"""
Parser for NIWIS (niwis-online.de) German River CSV exports (Rhine & Elbe).
Extracts daily water level (cm), relative position against the official
1991-2020 threshold, and severity class.

Real NIWIS export format:
  - 3-4 metadata/header text lines (source, license, date range, station name)
  - blank line
  - CSV header: "Datum";"Wasserstand [cm]";"extrem niedrig [cm]";"sehr niedrig [cm]";"niedrig [cm]"
  - semicolon-delimited, quoted, comma-decimal values, descending date order
  - the threshold columns are calendar-day-specific cutoffs derived from the
    1991-2020 reference period (NOT a single fixed seasonal average)
"""

from pathlib import Path
import pandas as pd
import numpy as np
from typing import Optional, List
try:
    from .config import RAW_NIWIS_DIR, STATIONS, START_DATE_2026, END_DATE_2026
except ImportError:
    from config import RAW_NIWIS_DIR, STATIONS, START_DATE_2026, END_DATE_2026


def _find_header_row(file_path: Path) -> int:
    """Locates the 0-based line index of the real CSV header row (starts with "Datum")."""
    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        for i, line in enumerate(f):
            if line.strip().lower().startswith('"datum"'):
                return i
    raise ValueError(f"Could not locate NIWIS CSV header row in {file_path.name}")


def parse_niwis_csv(
    file_path: Path,
    station_key: str,
    filter_summer_2026: bool = True
) -> pd.DataFrame:
    """
    Parses a single real NIWIS manual export CSV file into a standardized tidy DataFrame.

    Parameters:
    - file_path: Path to the NIWIS CSV export.
    - station_key: Key in STATIONS config (e.g. 'KAUB', 'DRESDEN').
    - filter_summer_2026: Whether to restrict to June 1 - August 31, 2026.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"NIWIS CSV file not found: {file_path}")

    meta = STATIONS.get(station_key.upper())
    if not meta:
        raise ValueError(f"Unknown station key: {station_key}")

    header_row = _find_header_row(file_path)
    df_raw = pd.read_csv(
        file_path,
        sep=";",
        encoding="utf-8-sig",
        skiprows=header_row,
        dtype=str,
        quotechar='"'
    )
    df_raw.columns = [c.strip().strip('"').lower() for c in df_raw.columns]

    def to_num(col: str) -> pd.Series:
        return pd.to_numeric(df_raw[col].str.replace(",", "."), errors="coerce")

    df = pd.DataFrame()
    df["date"] = pd.to_datetime(df_raw["datum"], dayfirst=True, errors="coerce").dt.strftime("%Y-%m-%d")
    df["value"] = to_num("wasserstand [cm]")
    df["threshold_extrem_niedrig"] = to_num("extrem niedrig [cm]")
    df["threshold_sehr_niedrig"] = to_num("sehr niedrig [cm]")
    df["threshold_niedrig"] = to_num("niedrig [cm]")

    # Drop rows with missing date or measurement (export includes a trailing empty day)
    df = df.dropna(subset=["date", "value"]).copy()

    # Station Metadata
    df["river"] = meta["river"]
    df["station_id"] = meta["station_id"]
    df["station_name"] = meta["station_name"]
    df["country"] = meta["country"]
    df["latitude"] = meta["latitude"]
    df["longitude"] = meta["longitude"]
    df["metric"] = meta["metric"]
    df["unit"] = meta["unit"]
    df["reference_period"] = meta["reference_period"]
    df["data_source"] = "NIWIS_manual_export"

    # Official NIWIS classification using the calendar-day-specific variable thresholds
    def classify(row):
        if row["value"] < row["threshold_extrem_niedrig"]:
            return "Extrem niedrig"
        elif row["value"] < row["threshold_sehr_niedrig"]:
            return "Sehr niedrig"
        elif row["value"] < row["threshold_niedrig"]:
            return "Niedrig"
        return "Normal"

    df["severity_class"] = df.apply(classify, axis=1)

    # "niedrig" threshold is the normal/low boundary for the 1991-2020 reference
    # period on that calendar day -> use it as the day-specific seasonal norm
    df["seasonal_norm"] = df["threshold_niedrig"]
    df["relative_position_pct"] = np.round((df["value"] / df["seasonal_norm"]) * 100, 2)

    # Days below historical record
    hist_min = meta.get("official_historical_min", 0.0)
    df["historical_min_record"] = hist_min
    df["is_below_historical_min"] = df["value"] < hist_min

    if filter_summer_2026:
        df = df[(df["date"] >= START_DATE_2026) & (df["date"] <= END_DATE_2026)].copy()

    df = df.drop(columns=["threshold_extrem_niedrig", "threshold_sehr_niedrig", "threshold_niedrig"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def load_all_niwis_data(directory: Optional[Path] = None) -> pd.DataFrame:
    """
    Scans the NIWIS raw directory and parses all matching German station CSV files.
    """
    raw_dir = directory or RAW_NIWIS_DIR
    records: List[pd.DataFrame] = []

    for station_key in ["KAUB", "DRESDEN"]:
        matching_files = list(raw_dir.glob(f"*{station_key.lower()}*.csv"))
        if matching_files:
            target_file = matching_files[0]
            df = parse_niwis_csv(target_file, station_key=station_key)
            records.append(df)
            print(f"Loaded NIWIS data for {station_key} from {target_file.name} ({len(df)} rows)")
        else:
            print(f"Warning: No NIWIS CSV file found for {station_key} in {raw_dir}")

    if records:
        return pd.concat(records, ignore_index=True)
    return pd.DataFrame()


if __name__ == "__main__":
    df_all = load_all_niwis_data()
    print(f"Total German station rows ingested: {len(df_all)}")
    if not df_all.empty:
        print(df_all.head())
