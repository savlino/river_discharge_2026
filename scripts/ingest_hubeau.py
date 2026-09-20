"""
Hub'Eau recent-observations validation module for French rivers.
Fetches live "Hauteur" (H) readings -- same measurement type as the manual
Hydro-Eaufrance export -- for cross-validation, mirroring the German
NIWIS (manual) + PEGELONLINE (live validation) design.

Hub'Eau names this endpoint `observations_tr` (`tr` = French "temps réel", or
real time). It exposes only a rolling ~1-month window:
  https://hubeau.eaufrance.fr/api/v2/hydrometrie/observations_tr.json
    ?code_entite={station_code}&grandeur_hydro=H
    &date_debut_obs={start}&date_fin_obs={end}&size=5000

The primary tidy dataset continues to rely on the manual Hydro-Eaufrance CSV
exports; this module archives a raw API snapshot under data/raw/hubeau/ and
reports discrepancies without altering them.
"""

import json
import urllib.request
from datetime import date, timedelta
import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional
try:
    from .config import RAW_HUBEAU_DIR, STATIONS
    from .ingest_hydro_eaufrance import FRENCH_STATION_KEYS
except ImportError:
    from config import RAW_HUBEAU_DIR, STATIONS
    from ingest_hydro_eaufrance import FRENCH_STATION_KEYS

HUBEAU_OBSERVATIONS_URL = "https://hubeau.eaufrance.fr/api/v2/hydrometrie/observations_tr.json"


def fetch_hubeau_api(
    station_code: str,
    start_date: str,
    end_date: str,
    grandeur_hydro: str = "H",
    size: int = 20000,
    timeout: int = 20
) -> List[Dict[str, Any]]:
    """Fetches raw water-level (H) observations for a station over the given date range."""
    params = [
        f"code_entite={station_code}",
        f"grandeur_hydro={grandeur_hydro}",
        f"date_debut_obs={start_date}",
        f"date_fin_obs={end_date}",
        f"size={size}"
    ]
    url = f"{HUBEAU_OBSERVATIONS_URL}?{'&'.join(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; portfolio-project/1.0)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                return data.get("data", [])
    except Exception as e:
        print(f"Notice: Hub'Eau recent-observations query for {station_code} returned: {e}")
    return []


def archive_hubeau_api(station_key: str, window_days: int = 29) -> Optional[pd.DataFrame]:
    """
    Fetches the last `window_days` of live H readings, archives a raw CSV copy
    under data/raw/hubeau/, and returns a daily-aggregated DataFrame.
    Hub'Eau rejects date_debut_obs older than ~1 calendar month from today, so
    the default stays a couple days under that limit as a safety margin.
    """
    meta = STATIONS[station_key.upper()]
    end_date = date.today()
    start_date = end_date - timedelta(days=window_days)

    records = fetch_hubeau_api(meta["station_id"], start_date.isoformat(), end_date.isoformat())
    if not records:
        return None

    RAW_HUBEAU_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = RAW_HUBEAU_DIR / f"{meta['station_id']}_H_api_snapshot.csv"
    df_raw = pd.DataFrame(records)[["date_obs", "resultat_obs", "code_statut", "code_qualification_obs"]]
    if archive_path.exists():
        print(f"Preserved existing Hub'Eau API snapshot: {archive_path}")
    else:
        df_raw.to_csv(archive_path, index=False, encoding="utf-8")
        print(f"Archived raw Hub'Eau response: {archive_path}")

    df_raw["date"] = pd.to_datetime(df_raw["date_obs"]).dt.strftime("%Y-%m-%d")
    df_raw["resultat_obs"] = pd.to_numeric(df_raw["resultat_obs"], errors="coerce")

    daily = df_raw.groupby("date", as_index=False)["resultat_obs"].mean()
    daily["resultat_obs"] = daily["resultat_obs"].round(1)
    daily = daily.rename(columns={"resultat_obs": "api_daily_mean"})
    return daily


def validate_hydro_eaufrance_against_hubeau(df_manual: pd.DataFrame) -> pd.DataFrame:
    """
    For each French station, archives the live recent observations and compares
    it against the corresponding manual Hydro-Eaufrance CSV values on overlapping
    dates. Does NOT modify df_manual -- the tidy dataset stays sourced from the
    manual export. Returns a validation report DataFrame (empty if no overlap).
    """
    reports = []

    for station_key in FRENCH_STATION_KEYS:
        meta = STATIONS[station_key]
        df_api_daily = archive_hubeau_api(station_key)
        if df_api_daily is None or df_api_daily.empty:
            continue

        df_station_manual = df_manual.loc[df_manual["station_id"] == meta["station_id"], ["date", "value"]]
        merged = pd.merge(df_station_manual, df_api_daily, on="date", how="inner")
        if merged.empty:
            continue

        merged["diff_mm"] = np.round(merged["value"] - merged["api_daily_mean"], 1)
        merged["relative_diff_pct"] = np.round(
            merged["diff_mm"] / merged["value"].abs().replace(0, np.nan) * 100,
            2,
        )
        merged["station_name"] = meta["station_name"]
        reports.append(merged)

        max_diff = merged["diff_mm"].abs().max()
        print(f"Hydro-Eaufrance validation for {meta['station_name']}: {len(merged)} overlapping day(s), max |diff| = {max_diff} mm")

    if reports:
        return pd.concat(reports, ignore_index=True)
    return pd.DataFrame()


if __name__ == "__main__":
    for key in FRENCH_STATION_KEYS:
        df = archive_hubeau_api(key)
        if df is not None:
            print(f"{key}: {len(df)} daily rows from Hub'Eau")
            print(df.tail())
