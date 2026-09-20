"""
PEGELONLINE REST API v2 validation module (pegelonline.wsv.de).
No authentication required. Only exposes a rolling ~31-day window, so it
cannot supply the 1991-2020 baseline. The primary tidy dataset continues to
rely on the manually-exported NIWIS CSVs; this module fetches the live API
purely to archive a raw snapshot and cross-check it against the NIWIS values.

Endpoint pattern (per-station UUID, CSV output):
  https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations/{uuid}/W/measurements.csv?start=P31D
"""

import urllib.request
import pandas as pd
import numpy as np
from io import StringIO
from typing import Optional
try:
    from .config import RAW_PEGELONLINE_DIR, STATIONS
except ImportError:
    from config import RAW_PEGELONLINE_DIR, STATIONS

PEGELONLINE_BASE_URL = "https://www.pegelonline.wsv.de/webservices/rest-api/v2"

# Station UUIDs (kept local to this module -- config.py stays keyed on the
# NIWIS manual-export workflow, which is the source of truth for the pipeline)
STATION_UUIDS = {
    "KAUB": "1d26e504-7f9e-480a-b52c-5932be6549ab",
    "DRESDEN": "70272185-b2b3-4178-96b8-43bea330dcae",
}


def fetch_pegelonline_csv(station_key: str, window: str = "P31D", timeout: int = 15) -> Optional[str]:
    """Fetches the raw CSV text of recent W (water level) measurements for a station."""
    uuid = STATION_UUIDS.get(station_key.upper())
    if not uuid:
        print(f"Notice: No PEGELONLINE UUID configured for station '{station_key}'.")
        return None

    url = f"{PEGELONLINE_BASE_URL}/stations/{uuid}/W/measurements.csv?start={window}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "RiverDischargeResearch/1.0 (Portfolio Project)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                return response.read().decode("utf-8")
    except Exception as e:
        print(f"Notice: PEGELONLINE API query for {station_key} returned: {e}")
    return None


def archive_raw_pegelonline(station_key: str, window: str = "P31D") -> Optional[pd.DataFrame]:
    """
    Fetches the raw API CSV, stores an untouched copy in data/raw/pegelonline/,
    and returns it parsed as a DataFrame with daily-aggregated mean values.
    """
    raw_text = fetch_pegelonline_csv(station_key, window)
    if not raw_text:
        return None

    RAW_PEGELONLINE_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = RAW_PEGELONLINE_DIR / f"{station_key.lower()}_pegelonline_{window.lower()}.csv"
    if archive_path.exists():
        print(f"Preserved existing PEGELONLINE API snapshot: {archive_path}")
    else:
        archive_path.write_text(raw_text, encoding="utf-8")
        print(f"Archived raw PEGELONLINE response: {archive_path}")

    df_raw = pd.read_csv(StringIO(raw_text), sep=";")
    df_raw["date"] = pd.to_datetime(df_raw["timestamp"]).dt.strftime("%Y-%m-%d")
    df_raw["value"] = pd.to_numeric(df_raw["value"], errors="coerce")

    daily = df_raw.groupby("date", as_index=False)["value"].mean()
    daily["value"] = daily["value"].round(1)
    daily = daily.rename(columns={"value": "pegelonline_daily_mean"})
    return daily


def validate_niwis_against_pegelonline(df_niwis: pd.DataFrame) -> pd.DataFrame:
    """
    For each German station, archives the live API data and compares it against
    the corresponding NIWIS CSV values on overlapping dates. Does NOT modify or
    override df_niwis -- the tidy dataset stays sourced from the manual export.
    Returns a validation report DataFrame (empty if no overlap / API unreachable).
    """
    reports = []

    for station_key in ["KAUB", "DRESDEN"]:
        meta = STATIONS[station_key.upper()]
        df_api_daily = archive_raw_pegelonline(station_key)
        if df_api_daily is None or df_api_daily.empty:
            continue

        df_station_niwis = df_niwis.loc[df_niwis["station_id"] == meta["station_id"], ["date", "value"]]
        merged = pd.merge(df_station_niwis, df_api_daily, on="date", how="inner")
        if merged.empty:
            continue

        merged["diff_cm"] = np.round(merged["value"] - merged["pegelonline_daily_mean"], 1)
        merged["relative_diff_pct"] = np.round(
            merged["diff_cm"] / merged["value"].abs().replace(0, np.nan) * 100,
            2,
        )
        merged["station_name"] = meta["station_name"]
        reports.append(merged)

        max_diff = merged["diff_cm"].abs().max()
        print(f"PEGELONLINE validation for {meta['station_name']}: {len(merged)} overlapping day(s), max |diff| = {max_diff} cm")

    if reports:
        return pd.concat(reports, ignore_index=True)
    return pd.DataFrame()


if __name__ == "__main__":
    for key in ["KAUB", "DRESDEN"]:
        df = archive_raw_pegelonline(key)
        if df is not None:
            print(f"{key}: {len(df)} daily rows from PEGELONLINE")
            print(df.tail())
