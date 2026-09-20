"""
Enrichment module using Open-Meteo API.
Pulls daily precipitation (mm) and mean temperature (°C) for station coordinates.
Calculates lagged cross-correlations between weather anomalies and river water levels.
"""

import json
import urllib.request
import pandas as pd
import numpy as np
from typing import List
try:
    from .config import STATIONS, START_DATE_2026, END_DATE_2026
except ImportError:
    from config import STATIONS, START_DATE_2026, END_DATE_2026

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_open_meteo_daily(
    latitude: float,
    longitude: float,
    start_date: str = START_DATE_2026,
    end_date: str = END_DATE_2026,
    timeout: int = 15
) -> pd.DataFrame:
    """
    Fetches daily precipitation sum (mm) and mean 2m temperature (°C) from Open-Meteo.
    Uses the archive API because the project covers a completed historical period.
    """
    params = [
        f"latitude={latitude:.4f}",
        f"longitude={longitude:.4f}",
        f"start_date={start_date}",
        f"end_date={end_date}",
        "daily=temperature_2m_mean,precipitation_sum",
        "timezone=UTC"
    ]
    query_str = "&".join(params)

    url = f"{OPEN_METEO_ARCHIVE_URL}?{query_str}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "RiverDischargeResearch/1.0 (Portfolio Project)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                daily = data.get("daily", {})
                if "time" in daily and "temperature_2m_mean" in daily:
                    return pd.DataFrame({
                        "date": daily["time"],
                        "temp_mean_c": daily["temperature_2m_mean"],
                        "precip_sum_mm": daily["precipitation_sum"]
                    })
    except Exception:
        pass

    # Return empty DataFrame if API unavailable
    return pd.DataFrame()


def generate_synthetic_meteo_data(
    station_key: str,
    start_date: str = START_DATE_2026,
    end_date: str = END_DATE_2026
) -> pd.DataFrame:
    """
    Fallback generator providing realistic European Summer 2026 weather:
    persistent heatwaves (24-33°C mean) and severe rain deficit (< 15-30mm total across summer).
    """
    dates = pd.date_range(start_date, end_date, freq="D").strftime("%Y-%m-%d")
    n = len(dates)
    np.random.seed(303 + len(station_key))

    # Base heatwave temperature curve
    t = np.linspace(0, 1, n)
    temp_base = 22.0 + 8.0 * np.sin(np.pi * t) + np.random.normal(0, 2.0, n)
    # Rare sporadic showers
    rain_prob = np.random.uniform(0, 1, n)
    precip = np.where(rain_prob > 0.88, np.random.exponential(4.0, n), 0.0)

    return pd.DataFrame({
        "date": dates,
        "temp_mean_c": np.round(temp_base, 1),
        "precip_sum_mm": np.round(precip, 1)
    })


def pull_meteo_for_all_stations(allow_synthetic_fallback: bool = False) -> pd.DataFrame:
    """
    Fetches meteorological records for all stations in config from Open-Meteo.
    If the live API is unreachable or returns partial coverage and
    allow_synthetic_fallback=False (the default), missing days are left as NaN
    instead of being silently fabricated. Pass allow_synthetic_fallback=True to
    explicitly opt in to filling gaps with a calibrated demonstration series,
    which is loudly flagged via a WARNING banner and tagged
    data_source='Synthetic_fallback' on every filled row.
    """
    dfs: List[pd.DataFrame] = []

    for key, meta in STATIONS.items():
        df_live = fetch_open_meteo_daily(meta["latitude"], meta["longitude"])
        all_dates = pd.date_range(START_DATE_2026, END_DATE_2026, freq="D").strftime("%Y-%m-%d")

        if not df_live.empty:
            df_meteo = pd.merge(pd.DataFrame({"date": all_dates}), df_live, on="date", how="left")
            df_meteo["data_source"] = np.where(df_meteo["temp_mean_c"].notna(), "OpenMeteo_API", "Missing")
        else:
            df_meteo = pd.DataFrame({"date": all_dates, "temp_mean_c": np.nan, "precip_sum_mm": np.nan})
            df_meteo["data_source"] = "Missing"

        missing_mask = df_meteo["data_source"] == "Missing"
        if missing_mask.any():
            if allow_synthetic_fallback:
                df_synth = generate_synthetic_meteo_data(key)
                df_meteo.loc[missing_mask, "temp_mean_c"] = df_meteo.loc[missing_mask, "date"].map(
                    df_synth.set_index("date")["temp_mean_c"]
                )
                df_meteo.loc[missing_mask, "precip_sum_mm"] = df_meteo.loc[missing_mask, "date"].map(
                    df_synth.set_index("date")["precip_sum_mm"]
                )
                df_meteo.loc[missing_mask, "data_source"] = "Synthetic_fallback"
                print(
                    "\n" + "!" * 70 +
                    f"\nWARNING: USING SYNTHETIC DATA for {missing_mask.sum()} day(s) of weather at "
                    f"{meta['station_name']} -- Open-Meteo API gap, live data NOT used.\n" +
                    "!" * 70
                )
            else:
                print(
                    f"Notice: {missing_mask.sum()} day(s) of weather missing for {meta['station_name']} "
                    "(Open-Meteo unavailable) and allow_synthetic_fallback=False -> left as NaN."
                )

        df_meteo["station_id"] = meta["station_id"]
        df_meteo["station_name"] = meta["station_name"]
        df_meteo["river"] = meta["river"]
        dfs.append(df_meteo)

    return pd.concat(dfs, ignore_index=True)


def compute_lagged_correlations(
    df_combined: pd.DataFrame,
    max_lags: int = 14
) -> pd.DataFrame:
    """
    Calculates lagged Pearson correlation between river water level and (1) the
    7-day trailing cumulative precipitation, (2) temperature -- both as recorded
    on day t. lag_days=N means the river value observed N days later (t+N) is
    correlated against the weather at day t, i.e. weather leads, river lags:
    corr(river_value(t+N), weather(t)). Example: lag_days=5 compares precipitation
    accumulated in the 7-day window ending on day t with the river level observed
    5 days after that window closes.
    """
    results = []

    for station_name, group in df_combined.groupby("station_name"):
        g = group.sort_values("date").copy()
        river_val = g["value"].values
        temp = g["temp_mean_c"].values
        precip = g["precip_sum_mm"].values

        # 7-day cumulative precip
        rolling_precip_7d = pd.Series(precip).rolling(7, min_periods=1).sum().values

        for lag in range(0, max_lags + 1):
            if lag == 0:
                corr_temp = np.corrcoef(river_val, temp)[0, 1]
                corr_precip_7d = np.corrcoef(river_val, rolling_precip_7d)[0, 1]
            else:
                # River value lagging behind weather by `lag` days
                v_slice = river_val[lag:]
                t_slice = temp[:-lag]
                p_slice = rolling_precip_7d[:-lag]
                corr_temp = np.corrcoef(v_slice, t_slice)[0, 1] if len(v_slice) > 5 else np.nan
                corr_precip_7d = np.corrcoef(v_slice, p_slice)[0, 1] if len(v_slice) > 5 else np.nan

            results.append({
                "station_name": station_name,
                "river": g["river"].iloc[0],
                "lag_days": lag,
                "corr_temp_vs_level": round(float(corr_temp), 3),
                "corr_7d_precip_vs_level": round(float(corr_precip_7d), 3)
            })

    return pd.DataFrame(results)


if __name__ == "__main__":
    df_met = pull_meteo_for_all_stations()
    print("Meteo records shape:", df_met.shape)
