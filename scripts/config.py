"""
Configuration and metadata for the Summer 2026 European River Drought Analysis.
"""

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_NIWIS_DIR = DATA_DIR / "raw" / "niwis"
RAW_PEGELONLINE_DIR = DATA_DIR / "raw" / "pegelonline"
RAW_HYDRO_EAUFRANCE_DIR = DATA_DIR / "raw" / "hydro_eaufrance"
RAW_HYDRO_EAUFRANCE_HISTORIC_DIR = RAW_HYDRO_EAUFRANCE_DIR / "Historic"
RAW_HUBEAU_DIR = DATA_DIR / "raw" / "hubeau"
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"

# Target Analysis Window (Summer 2026)
START_DATE_2026 = "2026-06-01"
END_DATE_2026 = "2026-08-31"

# Station Metadata Dictionary
STATIONS = {
    # Germany (NIWIS / Pegelonline)
    "KAUB": {
        "station_id": "KAUB",
        "station_name": "Kaub",
        "river": "Rhine",
        "country": "Germany",
        "latitude": 50.0847,
        "longitude": 7.7634,
        "metric": "Water Level",
        "unit": "cm",
        "provider": "NIWIS / WSV",
        "reference_period": "1991-2020",
        "official_historical_min": 25.0,  # Historic minimum prior to 2026 was ~25cm (Oct 2018)
        "pegelonline_uuid": "1d26e504-7f9e-480a-b52c-5932be6549ab",  # PEGELONLINE REST API v2 station UUID
    },
    "DRESDEN": {
        "station_id": "DRESDEN",
        "station_name": "Dresden",
        "river": "Elbe",
        "country": "Germany",
        "latitude": 51.0543,
        "longitude": 13.7389,
        "metric": "Water Level",
        "unit": "cm",
        "provider": "NIWIS / WSV",
        "reference_period": "1991-2020",
        "official_historical_min": 46.0,  # Historic low prior to 2026
        "pegelonline_uuid": "70272185-b2b3-4178-96b8-43bea330dcae",  # PEGELONLINE REST API v2 station UUID
    },
    # France (Hub'Eau Hydrométrie -- Hauteur/H, aligned with German water-level approach)
    "TONNEINS": {
        "station_id": "O900001002",
        "station_name": "Tonneins",
        "river": "Garonne",
        "country": "France",
        "latitude": 44.3872,
        "longitude": 0.3134,
        "metric": "Water Level",
        "unit": "mm",
        "provider": "Hub'Eau / Hydro-Eaufrance",
        "reference_period": "2016-2025 summer reference (10 summers, Hydro-Eaufrance)",
    },
    "BLOIS": {
        "station_id": "K447001001",
        "station_name": "Blois",
        "river": "Loire",
        "country": "France",
        "latitude": 47.5857,
        "longitude": 1.3328,
        "metric": "Water Level",
        "unit": "mm",
        "provider": "Hub'Eau / Hydro-Eaufrance",
        "reference_period": "2016-2025 summer reference (10 summers, Hydro-Eaufrance)",
    },
    "TERNAY": {
        "station_id": "V303002002",
        "station_name": "Ternay",
        "river": "Rhône",
        "country": "France",
        "latitude": 45.6082,
        "longitude": 4.8029,
        "metric": "Water Level",
        "unit": "mm",
        "provider": "Hub'Eau / Hydro-Eaufrance",
        "reference_period": "2016-2025 summer reference (10 summers, Hydro-Eaufrance)",
    }
}
