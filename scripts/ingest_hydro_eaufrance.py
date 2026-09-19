"""
Parser for manually-exported Hydro-Eaufrance / Hub'Eau "Hauteur" (H) CSV files
for French rivers (Garonne, Loire, Rhône). This is the primary historical
source for French stations, mirroring the German NIWIS manual-export approach.

Raw export format (data/raw/hydro_eaufrance/{station_id}_H.csv):
  "Date (TU)","Valeur (en mm)","Statut","Qualification","Méthode","Continuité"
  2026-06-01T00:05:00.000Z,"227","12",16,10,0
  - sub-daily instantaneous water level readings, in millimeters
  - "Valeur (en mm)" is relative to a local station-specific gauge datum and
    can be negative (e.g. Blois) -- absolute values are NOT comparable across
    stations, only day-over-day trends within the same station are meaningful

Reference baseline (data/raw/hydro_eaufrance/Historic/{station_id}_H_10y_summer_hist.csv):
  10 merged summers (2016-2025) of the same sub-daily H measurements. Because
  Hydro-Eaufrance publishes no official low-water bands (unlike NIWIS), the
  reference distribution is derived from these 10 summers.

  Severity and relative position are expressed as a **percentile rank against
  the historical distribution for the same point in the season**, NOT as a
  ratio value/norm: gauge values sit on arbitrary local datums and are often
  negative, which makes a percentage-of-norm ratio meaningless for these
  stations. The percentile rank is datum-independent and directly comparable
  across stations.
"""

from pathlib import Path
import pandas as pd
import numpy as np
from typing import Optional, List, Dict
try:
    from .config import (
        RAW_HYDRO_EAUFRANCE_DIR,
        RAW_HYDRO_EAUFRANCE_HISTORIC_DIR,
        STATIONS,
        START_DATE_2026,
        END_DATE_2026,
    )
except ImportError:
    from config import (
        RAW_HYDRO_EAUFRANCE_DIR,
        RAW_HYDRO_EAUFRANCE_HISTORIC_DIR,
        STATIONS,
        START_DATE_2026,
        END_DATE_2026,
    )

FRENCH_STATION_KEYS = ["TONNEINS", "BLOIS", "TERNAY"]

# Calendar days either side of the target date pooled into its reference sample.
# +/-7 days x 10 summers gives ~150 daily observations per calendar day, which is
# enough for stable percentiles; a single calendar day alone would only have 10.
REFERENCE_WINDOW_DAYS = 7


def _classify_from_percentile(pct_rank: float) -> str:
    """Percentile-band classification (no official French low-water thresholds available)."""
    if pd.isna(pct_rank):
        return "Unbekannt"
    if pct_rank <= 10:
        return "Extrem niedrig"
    elif pct_rank <= 25:
        return "Sehr niedrig"
    elif pct_rank <= 50:
        return "Niedrig"
    return "Normal"


def _read_h_export(file_path: Path) -> pd.DataFrame:
    """Reads a Hydro-Eaufrance H export (raw per-season or merged historic) into daily means."""
    df_raw = pd.read_csv(file_path, encoding="utf-8-sig", dtype=str)
    df_raw.columns = [c.strip() for c in df_raw.columns]

    # Merged historic files are already normalised; per-season exports use the original headers
    date_col = "timestamp_utc" if "timestamp_utc" in df_raw.columns else "Date (TU)"
    value_col = "value_mm" if "value_mm" in df_raw.columns else "Valeur (en mm)"

    parsed = pd.DataFrame({
        "date": pd.to_datetime(df_raw[date_col], errors="coerce", utc=True).dt.strftime("%Y-%m-%d"),
        "value_mm": pd.to_numeric(df_raw[value_col].str.strip('"'), errors="coerce"),
    }).dropna(subset=["date", "value_mm"])

    daily = parsed.groupby("date", as_index=False)["value_mm"].mean()
    daily["value"] = np.round(daily["value_mm"], 1)
    return daily.drop(columns=["value_mm"])


def load_historic_reference(station_key: str) -> Dict[str, np.ndarray]:
    """
    Builds the per-calendar-day reference distribution from the merged 10-summer file.
    Returns {"MM-DD": array of historical daily means within +/-REFERENCE_WINDOW_DAYS}.
    """
    station_id = STATIONS[station_key.upper()]["station_id"]
    hist_path = RAW_HYDRO_EAUFRANCE_HISTORIC_DIR / f"{station_id}_H_10y_summer_hist.csv"
    if not hist_path.exists():
        raise FileNotFoundError(
            f"Historic baseline not found: {hist_path}. "
            "Expected the merged 10-summer export for this station."
        )

    hist_daily = _read_h_export(hist_path)
    hist_daily["doy"] = pd.to_datetime(hist_daily["date"]).dt.dayofyear
    hist_daily["month_day"] = pd.to_datetime(hist_daily["date"]).dt.strftime("%m-%d")

    reference: Dict[str, np.ndarray] = {}
    for month_day in sorted(hist_daily["month_day"].unique()):
        target_doy = hist_daily.loc[hist_daily["month_day"] == month_day, "doy"].iloc[0]
        window = hist_daily[(hist_daily["doy"] - target_doy).abs() <= REFERENCE_WINDOW_DAYS]
        reference[month_day] = window["value"].to_numpy()

    return reference


def parse_hydro_eaufrance_csv(
    file_path: Path,
    station_key: str,
    filter_summer_2026: bool = True
) -> pd.DataFrame:
    """
    Parses a manual Hydro-Eaufrance "H" export into daily-aggregated tidy rows.
    Daily value = mean of sub-daily readings, kept in mm (matches the raw export and API).
    relative_position_pct is the percentile rank of each day's value within the
    2016-2025 reference distribution for the same point in the season.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Hydro-Eaufrance CSV file not found: {file_path}")

    meta = STATIONS.get(station_key.upper())
    if not meta:
        raise ValueError(f"Unknown station key: {station_key}")

    daily = _read_h_export(file_path)
    reference = load_historic_reference(station_key)

    month_day = pd.to_datetime(daily["date"]).dt.strftime("%m-%d")

    def percentile_rank(value: float, key: str) -> float:
        sample = reference.get(key)
        if sample is None or sample.size == 0:
            return np.nan
        return round(float((sample < value).mean() * 100), 1)

    daily["relative_position_pct"] = [
        percentile_rank(v, md) for v, md in zip(daily["value"], month_day)
    ]
    daily["seasonal_norm"] = [
        round(float(np.median(reference[md])), 1) if md in reference else np.nan
        for md in month_day
    ]
    daily["severity_class"] = daily["relative_position_pct"].apply(_classify_from_percentile)

    daily["river"] = meta["river"]
    daily["station_id"] = meta["station_id"]
    daily["station_name"] = meta["station_name"]
    daily["country"] = meta["country"]
    daily["latitude"] = meta["latitude"]
    daily["longitude"] = meta["longitude"]
    daily["metric"] = meta["metric"]
    daily["unit"] = meta["unit"]
    daily["reference_period"] = meta["reference_period"]
    daily["data_source"] = "HydroEaufrance_manual_export"

    # Lowest daily mean observed across the 10 reference summers for this station
    hist_min = round(float(min(sample.min() for sample in reference.values())), 1)
    daily["historical_min_record"] = hist_min
    daily["is_below_historical_min"] = daily["value"] < hist_min

    if filter_summer_2026:
        daily = daily[(daily["date"] >= START_DATE_2026) & (daily["date"] <= END_DATE_2026)].copy()

    return daily.sort_values("date").reset_index(drop=True)


def load_all_hydro_eaufrance_data(directory: Optional[Path] = None) -> pd.DataFrame:
    """Scans the Hydro-Eaufrance raw directory and parses all configured French station files."""
    raw_dir = directory or RAW_HYDRO_EAUFRANCE_DIR
    records: List[pd.DataFrame] = []

    for station_key in FRENCH_STATION_KEYS:
        meta = STATIONS[station_key]
        target_file = raw_dir / f"{meta['station_id']}_H.csv"
        if target_file.exists():
            df = parse_hydro_eaufrance_csv(target_file, station_key)
            records.append(df)
            print(f"Loaded Hydro-Eaufrance data for {station_key} from {target_file.name} ({len(df)} rows)")
        else:
            print(f"Warning: No Hydro-Eaufrance CSV file found for {station_key} at {target_file}")

    if records:
        return pd.concat(records, ignore_index=True)
    return pd.DataFrame()


if __name__ == "__main__":
    df_all = load_all_hydro_eaufrance_data()
    print(f"Total French station rows ingested: {len(df_all)}")
    if not df_all.empty:
        print(df_all.head())
