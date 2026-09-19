"""
Master Data Pipeline for Summer 2026 European River Low-Flow / Drought Analysis.
Executes ingestion for Germany (NIWIS) and France (Hub'Eau), merges Open-Meteo data,
and produces the final tidy CSVs for Tableau Public and analytical reports.
"""

import pandas as pd

from config import (
    RAW_NIWIS_DIR,
    RAW_HYDRO_EAUFRANCE_DIR,
    PROCESSED_DIR,
    OUTPUT_DIR,
)
from ingest_niwis import load_all_niwis_data
from ingest_pegelonline import validate_niwis_against_pegelonline
from ingest_hydro_eaufrance import load_all_hydro_eaufrance_data
from ingest_hubeau import validate_hydro_eaufrance_against_api
from ingest_meteo import pull_meteo_for_all_stations, compute_lagged_correlations

# Synthetic data is never used unless explicitly opted into here -- keeps fabricated
# rows from silently entering the tidy output when a live API is unavailable.
ALLOW_SYNTHETIC_FALLBACK = False


def _warn_if_synthetic_present(df_tidy: pd.DataFrame) -> None:
    """Prints a loud, unmissable banner if any synthetic/fabricated rows made it into the tidy output."""
    source_cols = [c for c in ["data_source", "meteo_data_source"] if c in df_tidy.columns]
    synthetic_counts = {}
    for col in source_cols:
        mask = df_tidy[col].astype(str).str.contains("Synthetic", na=False)
        if mask.any():
            synthetic_counts[col] = df_tidy.loc[mask, "station_name"].value_counts().to_dict()

    if synthetic_counts:
        print("\n" + "#" * 70)
        print("# WARNING: USING SYNTHETIC DATA -- this tidy CSV contains FABRICATED rows!")
        for col, by_station in synthetic_counts.items():
            for station, count in by_station.items():
                print(f"#   [{col}] {station}: {count} synthetic row(s)")
        print("# Do not treat these rows as real observations. Re-run once the live API is reachable.")
        print("#" * 70)


def run_pipeline():
    print("=" * 70)
    print("STARTING EUROPEAN RIVER DROUGHT 2026 DATA PIPELINE")
    print("=" * 70)

    # 1. Ensure output/processed directories exist; NIWIS raw exports must be
    # manually placed in data/raw/niwis
    RAW_NIWIS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    niwis_files = list(RAW_NIWIS_DIR.glob("*.csv"))
    if not niwis_files:
        raise FileNotFoundError(
            f"No NIWIS CSV exports found in {RAW_NIWIS_DIR}. "
            "Manually export station data from niwis-online.de and place it there."
        )

    hydro_eaufrance_files = list(RAW_HYDRO_EAUFRANCE_DIR.glob("*_H.csv"))
    if not hydro_eaufrance_files:
        raise FileNotFoundError(
            f"No Hydro-Eaufrance CSV exports found in {RAW_HYDRO_EAUFRANCE_DIR}. "
            "Manually export station 'Hauteur' data from hydro.eaufrance.fr and place it there."
        )

    # 2. Ingest German Rivers (Rhine & Elbe) from manual NIWIS exports
    print("\n[1/6] Ingesting German rivers from NIWIS CSV exports...")
    df_germany = load_all_niwis_data(RAW_NIWIS_DIR)
    print(f"-> Ingested {len(df_germany)} rows for German stations.")

    # 2b. Validate against PEGELONLINE REST API (rolling ~31-day window); archives the raw
    # API response under data/raw/pegelonline/ and reports discrepancies -- the tidy dataset
    # keeps using the NIWIS CSV values as the source of truth
    print("\n[2/6] Validating against PEGELONLINE REST API (rolling ~31-day window)...")
    df_validation_de = validate_niwis_against_pegelonline(df_germany)
    if not df_validation_de.empty:
        validation_output_path = OUTPUT_DIR / "pegelonline_validation.csv"
        df_validation_de.to_csv(validation_output_path, index=False, encoding="utf-8")
        print(f"-> Exported validation report: {validation_output_path}")

    # 3. Ingest French Rivers (Garonne, Loire, Rhône) from manual Hydro-Eaufrance exports
    print("\n[3/6] Ingesting French rivers from Hydro-Eaufrance CSV exports (Hauteur/H)...")
    df_france = load_all_hydro_eaufrance_data(RAW_HYDRO_EAUFRANCE_DIR)
    print(f"-> Ingested {len(df_france)} rows for French stations.")

    # 3b. Validate against Hub'Eau observations_tr REST API (rolling ~1-month window); archives
    # the raw API response under data/raw/hubeau/ and reports discrepancies -- the tidy
    # dataset keeps using the manual export values as the source of truth
    print("\n[4/6] Validating against Hub'Eau observations_tr API (rolling ~1-month window)...")
    df_validation_fr = validate_hydro_eaufrance_against_api(df_france)
    if not df_validation_fr.empty:
        validation_output_path = OUTPUT_DIR / "hydro_eaufrance_validation.csv"
        df_validation_fr.to_csv(validation_output_path, index=False, encoding="utf-8")
        print(f"-> Exported validation report: {validation_output_path}")

    # 4. Combine into Unified Tidy Schema
    print("\n[5/6] Unifying German and French observations into Tidy Schema...")
    df_combined = pd.concat([df_germany, df_france], ignore_index=True)

    # 5. Ingest Weather & Merge
    print("\n[6/6] Pulling Open-Meteo weather enrichment & computing lagged correlations...")
    df_meteo = pull_meteo_for_all_stations(allow_synthetic_fallback=ALLOW_SYNTHETIC_FALLBACK)

    df_tidy = pd.merge(
        df_combined,
        df_meteo[["station_id", "date", "temp_mean_c", "precip_sum_mm", "data_source"]].rename(
            columns={"data_source": "meteo_data_source"}
        ),
        on=["station_id", "date"],
        how="left"
    )

    # Sort deterministically
    df_tidy = df_tidy.sort_values(["country", "river", "station_name", "date"]).reset_index(drop=True)

    _warn_if_synthetic_present(df_tidy)

    # Export Primary Tidy Dataset for Tableau Public
    tidy_output_path = OUTPUT_DIR / "european_drought_summer_2026_tidy.csv"
    df_tidy.to_csv(tidy_output_path, index=False, encoding="utf-8")
    print(f"\n[OK] Exported Master Tidy Dataset: {tidy_output_path} ({len(df_tidy)} rows)")

    # Compute and Export Lagged Weather Correlation Analysis
    df_corr = compute_lagged_correlations(df_tidy)
    corr_output_path = OUTPUT_DIR / "meteo_river_correlation.csv"
    df_corr.to_csv(corr_output_path, index=False, encoding="utf-8")
    print(f"[OK] Exported Lagged Correlations: {corr_output_path}")

    # Compute Executive Station Summary Metrics
    summary_rows = []
    for (river, st_name, country, metric, unit), grp in df_tidy.groupby(["river", "station_name", "country", "metric", "unit"]):
        min_val = grp["value"].min()
        hist_min = grp["historical_min_record"].iloc[0]
        days_below_hist = grp["is_below_historical_min"].sum()
        days_extrem = (grp["severity_class"] == "Extrem niedrig").sum()
        days_sehr = (grp["severity_class"] == "Sehr niedrig").sum()
        avg_relative_position = grp["relative_position_pct"].mean()

        summary_rows.append({
            "river": river,
            "station_name": st_name,
            "country": country,
            "metric": metric,
            "unit": unit,
            "summer_2026_min": min_val,
            "historical_min_record": hist_min,
            "new_record_set_2026": bool(min_val < hist_min),
            "days_below_historical_record": int(days_below_hist),
            "days_extrem_niedrig": int(days_extrem),
            "days_sehr_niedrig": int(days_sehr),
            "avg_relative_position_pct": round(float(avg_relative_position), 1)
        })

    df_summary = pd.DataFrame(summary_rows)
    summary_output_path = OUTPUT_DIR / "summary_metrics_2026.csv"
    df_summary.to_csv(summary_output_path, index=False, encoding="utf-8")
    print(f"[OK] Exported Executive Summary: {summary_output_path}")

    print("\n" + "=" * 70)
    print("PIPELINE EXECUTION COMPLETE")
    print("=" * 70)
    print("\nSummary Overview (Summer 2026):")
    print(df_summary.to_string(index=False))


if __name__ == "__main__":
    run_pipeline()
