# European River Water-Level Anomalies, Summer 2026

A presentation-first Tableau project showing a daily-granularity snapshot of the Summer 2026 drought across five monitoring stations and four major European river basins. The Tableau workbook is included as `river_summer_2026.twbx`; the CSV pipeline remains available for reproducibility and Tableau Public import.

**Author:** Pavel Krasavin  
**Portfolio:** [github.com/savlino](https://github.com/savlino)  
**LinkedIn:** [linkedin.com/in/pavel-krasavin](https://www.linkedin.com/in/pavel-krasavin)

## Published Tableau Package

- [Tableau workbook](river_summer_2026.twbx)
- [Published Tableau Public workbook](https://public.tableau.com/app/profile/pavel.krasavin1517/viz/european_river_discharge_summer_2026/Overall)
- [Station map dashboard](assets/dashboard_station_map.png)
- [Correlation dashboard](assets/dashboard_correlation.png)
- [Visual evidence dashboard](assets/dashboard_visual_evidence.png)

The visual evidence dashboard combines the quantitative station views with manually sourced Copernicus/Sentinel-2 comparisons:

- [Kaub, 2019-08-23](assets/copernicus_shots/Kaub_2019-08-23_crop.png) vs. [2026-08-13](assets/copernicus_shots/Kaub_2026-08-13_crop.png)
- [Garonne, 2019-08-22](assets/copernicus_shots/Garrone_2019-08-22_crop.png) vs. [2026-08-19](assets/copernicus_shots/Garrone_2026-08-19_crop.png)
- [Loire, 2019-08-22](assets/copernicus_shots/Loire_2019-08-22_crop.png) vs. [2026-08-12](assets/copernicus_shots/Loire_2026-08-12_crop.png)

These satellite images are illustrative evidence only. They are not part of the CSV pipeline and should not be interpreted as calibrated water-level measurements.

The dashboard PNGs remain in the repository as stable previews for readers who cannot open the Tableau workbook or access Tableau Public. The interactive Tableau Public link above is the primary presentation; the screenshots provide a fixed visual reference for the published state of the work.

## Key Findings

- **Kaub / Rhine:** the summer minimum was 7 cm, below the previous 25 cm record, with 14 days below that historical minimum and 68 days classified `Extrem niedrig` under NIWIS thresholds.
- **Dresden / Elbe:** the summer minimum was 43 cm, below the configured 46 cm historical minimum, with 2 days below the record and a less severe profile than Kaub.
- **Tonneins / Garonne:** the average historical-relative position was 36.2%; 6 days were `Extrem niedrig` and 39 were `Sehr niedrig`.
- **Ternay / Rhône:** the average historical-relative position was 35.9%; 4 days were `Extrem niedrig` and 28 were `Sehr niedrig`.
- **Blois / Loire:** this is the most extreme French result. The 2026 series falls below the 10-summer historical minimum on 58 of 88 available days, with 88 days in the `Extrem niedrig` band and an average relative position of 0.1%.

### Loire Interpretation and Caveat

The Blois signal should be presented as **extremely affected by drought**, not as a routine percentile fluctuation. Independent reporting published by AFP on 26 July 2026 described the Loire as exceptionally and unusually early dry, placed the river at `alerte` level with initial water-use restrictions, and reported natural flows comparable to historically dry 2003 and 2019 conditions. See the [Le Petit Journal / AFP reference](https://lepetitjournal.com/expat-mag/environnement/la-loire-en-alerte-eprouvee-par-une-secheresse-exceptionnelle-449934).

At the same time, Blois values are reported relative to a local gauge datum and are therefore negative and not directly comparable with Ternay, Tonneins, Kaub, or Dresden. The 0.1% relative position means the 2026 observations sit at or below the available historical distribution for the same seasonal window; it does not mean the river has 0.1% of a common physical water-level norm. The unusually persistent low Blois graph should also be treated as a station-specific warning signal because historic minima cluster near an apparent measurement or control-structure floor. It supports the drought narrative, but absolute cross-station claims should be avoided.

## Data Sources & Attribution

- Water level data (Germany): NIWIS/PEGELONLINE operator, Datenlizenz Deutschland – Namensnennung 2.0
- Water level data (France): Hub'Eau / Hydro-Eaufrance (Système d'Information sur l'Eau), Etalab Open Licence 2.0
- Weather data: [Open-Meteo.com](https://open-meteo.com/), CC BY 4.0
- Satellite imagery: Copernicus Sentinel-2 data, via Copernicus Browser (ESA)
- River geometry: Natural Earth, public domain
- Basemap: © Mapbox © OpenStreetMap contributors

---

## 1. Project Structure

```text
river_discharge_2026/
├── assets/                       # Tableau dashboard exports and visual evidence
│   ├── dashboard_station_map.png
│   ├── dashboard_correlation.png
│   ├── dashboard_visual_evidence.png
│   └── copernicus_shots/         # Manual Sentinel-2 comparison exports
├── data/
│   └── raw/
│       ├── niwis/                # Manual CSV exports from NIWIS (Rhine & Elbe)
│       │   ├── Kaub (Rhein).csv
│       │   └── Dresden (Elbe).csv
│       ├── pegelonline/          # Archived PEGELONLINE API snapshots (validation only)
│       ├── hydro_eaufrance/      # Manual Hauteur (H) exports (France, primary source)
│       │   ├── O900001002_H.csv
│       │   ├── K447001001_H.csv
│       │   ├── V303002002_H.csv
│       │   └── Historic/         # Merged 10-summer (2016-2025) reference baselines
│       │       ├── O900001002_H_10y_summer_hist.csv
│       │       ├── K447001001_H_10y_summer_hist.csv
│       │       └── V303002002_H_10y_summer_hist.csv
│       └── hubeau/               # Archived Hub'Eau observations_tr API snapshots (validation only)
├── output/
│   ├── european_drought_summer_2026_tidy.csv  # Primary Tidy dataset for Tableau Public
│   ├── meteo_river_correlation.csv            # Lagged weather cross-correlation matrix
│   ├── summary_metrics_2026.csv               # Station-level drought impact summary
│   ├── pegelonline_validation.csv             # NIWIS vs. PEGELONLINE cross-check
│   └── hydro_eaufrance_validation.csv         # Manual export vs. Hub'Eau observations_tr cross-check
├── scripts/
│   ├── config.py                 # Station coordinates & metadata
│   ├── ingest_niwis.py           # Parser for German NIWIS exports with official thresholds
│   ├── ingest_pegelonline.py     # PEGELONLINE REST API v2 -- validation only (Germany)
│   ├── ingest_hydro_eaufrance.py # Parser for French Hauteur (H) manual exports
│   ├── ingest_hubeau.py          # Hub'Eau observations_tr REST API -- validation only (France)
│   ├── ingest_meteo.py           # Open-Meteo API enrichment & lagged correlation analysis
│   └── build_pipeline.py         # Master pipeline builder
├── requirements.txt
└── README.md
```

---

## 2. Confirmed Data Sources & Integration Strategy

| Region / Scope | Primary Data Source | Metric & Unit | Validation Source | Role in Analysis |
| :--- | :--- | :--- | :--- | :--- |
| **Germany** (Rhine & Elbe) | **NIWIS** (*niwis-online.de*), manual CSV exports | Water Level ($W$, $\text{cm}$) | PEGELONLINE REST API v2 (rolling ~31-day window) | **Primary Hero Dataset**: Official 1991–2020 reference period with pre-computed calendar-day-specific low-water thresholds. |
| **France** (Garonne, Loire, Rhône) | **Hydro-Eaufrance** (*hydro.eaufrance.fr*), manual "Hauteur" (H) CSV exports | Water Level ($H$, $\text{mm}$) | Hub'Eau `observations_tr` REST API (rolling ~1-month window) | **Cross-Basin Comparison**: Sub-daily height readings aggregated to daily means and benchmarked against a 10-summer (2016-2025) station-specific reference distribution. |
| **Atmospheric Enrichment** | **Open-Meteo** (*open-meteo.com*) | Mean Temp ($^\circ\text{C}$), Precip ($\text{mm}$) | Historical / Forecast REST API | **Enrichment**: Daily precipitation and temperature series for lagged correlation with water level. |
| **Visual Evidence** | **Copernicus Browser / Sentinel-2** | Cloud-free optical satellite imagery | Manual PNG export to `assets/` | **Qualitative Presentation**: Visual before/after riverbed comparisons for reports and dashboard cards. |

Both countries now follow the same manual-export-as-truth + live-API-as-validation pattern: the tidy dataset is always built from the manually exported CSVs, while the corresponding live REST API is only used to archive an independent snapshot and cross-check it -- it never overrides the tidy values.

---

## 3. Data Source Exclusions & Technical Trade-offs

During data-source architectural review, several potential data sources were evaluated and deliberately excluded from automated ETL ingestion:

1. **PEGELONLINE REST API (`pegelonline.wsv.de`) / Hub'Eau `observations_tr`**
   - *Technical Limitation:* Both are open, no-auth REST APIs, but each enforces a rolling window on raw time-series data -- PEGELONLINE ~31 days, Hub'Eau `observations_tr` rejects any `date_debut_obs` older than ~1 calendar month.
   - *Architectural Decision:* Neither can supply a full-summer or multi-year baseline. Manual CSV exports (NIWIS for Germany, Hydro-Eaufrance for France) serve as the authoritative source for the tidy dataset; both live APIs are used exclusively to archive an independent snapshot and cross-validate the manual values (see `output/pegelonline_validation.csv` and `output/hydro_eaufrance_validation.csv`).

2. **Danube / Hungary (vizugy.hu / hydroinfo.hu / DanubeHIS)**
   - *Technical Limitation:* No open programmatic historical REST API is available. Web portals provide HTML-rendered tables without structured open endpoints.
   - *Architectural Decision:* Excluded from the tabular data pipeline. Documented qualitatively instead: the Danube gauge at Budapest broke its all-time record low repeatedly over the summer — from the prior record of 33 cm (set in 2018) to 31 cm in late July, roughly 23 cm in early August, and ultimately just 1 cm by September 8, following Hungary's driest summer since 1901 (Hungarian General Directorate of Water Management, via Xinhua/Telex reporting).

3. **Po River / Italy (ARPA Regional Portals)**
   - *Technical Limitation:* Hydrological monitoring is fragmented across regional agencies (ARPA Lombardia, ARPA Piemonte, ARPAE Emilia-Romagna) without a single standardized national REST API.
   - *Architectural Decision:* Excluded from the programmatic pipeline; referenced qualitatively instead: at Cremona, the Po's gauge fell to 8.59 m below its hydrometric zero on July 31, 2026 — surpassing the previous record of 8.58 m set during the 2022 drought. The Po River Basin Authority (Adbpo) raised its water-stress alert to "high," with over 100 municipalities in Piedmont and Lombardy facing drinking-water supply issues (ANSA).

4. **GRDC (Global Runoff Data Centre) & EFAS (European Flood Awareness System)**
   - *Technical Limitation:* GRDC requires formal application and data usage agreements; EFAS real-time discharge requires restricted Copernicus credentials.
   - *Architectural Decision:* Excluded in favor of open, reproducible public sources.

---

## 4. Methodology & Metrics Computation

### 1. Tidy Schema Structure (Tableau Public Ready)
Every row in `output/european_drought_summer_2026_tidy.csv` represents a single daily station observation:
- `river`: River name (`Rhine`, `Elbe`, `Garonne`, `Loire`, `Rhône`)
- `station_id`: Unique station identifier
- `station_name`: Official monitoring station name (`Kaub`, `Dresden`, `Tonneins`, `Blois`, `Ternay`)
- `country`: `Germany` or `France`
- `latitude` / `longitude`: Decimal coordinates for spatial mapping
- `date`: Daily timestamp (`YYYY-MM-DD`, June 1 – August 31, 2026)
- `metric`: `Water Level` for all stations (unified across both countries)
- `unit`: `cm` (Germany, NIWIS convention) or `mm` (France, Hydro-Eaufrance convention) -- kept in each source's native unit; not converted, since the tidy schema is self-describing per row
- `value`: Daily mean measured value. French "Hauteur" values are relative to a local, station-specific gauge datum and can be negative (e.g. Blois) -- only meaningful as a day-over-day trend within the same station, not comparable in absolute terms across stations
- `reference_period`: `1991-2020` official period for NIWIS stations; `2016-2025 summer reference (10 summers, Hydro-Eaufrance)` for French stations
- `seasonal_norm`: For Germany, the calendar-day-specific "niedrig" (low) threshold from the NIWIS export. For France, the median of the 2016-2025 reference distribution for the same point in the season
- `relative_position_pct`: For Germany, a ratio vs. the day-specific threshold ($\frac{\text{value}}{\text{seasonal\_norm}} \times 100$). For France, the value's **percentile rank (0-100) against the 2016-2025 historical distribution** for the same point in the season. This field is deliberately **not** named `pct_of_seasonal_norm`: French gauge readings sit on arbitrary local datums and are frequently negative, which makes a percentage-of-norm ratio mathematically meaningless for those stations. A percentile rank is datum-independent and comparable across stations
- `severity_class`: For Germany, NIWIS's official calendar-day-specific bands (`Normal` / `Niedrig` / `Sehr niedrig` / `Extrem niedrig`). For France, percentile bands against the 10-summer reference: $\le\!10$ = `Extrem niedrig`, $\le\!25$ = `Sehr niedrig`, $\le\!50$ = `Niedrig`, else `Normal`
- `historical_min_record`: Known pre-2026 record low. For Germany, the official record (e.g. 25 cm for Kaub). For France, the lowest daily mean observed across the 10 reference summers
- `is_below_historical_min`: `True` if the day's value fell below `historical_min_record`
- `data_source`: Provenance of the river measurement (`NIWIS_manual_export` or `HydroEaufrance_manual_export`) -- the tidy dataset never contains fabricated/synthetic rows
- `meteo_data_source`: Provenance of the weather enrichment (`OpenMeteo_API`, or `Synthetic_fallback` only if explicitly opted into via `ALLOW_SYNTHETIC_FALLBACK` in `build_pipeline.py`)
- `temp_mean_c`: Daily mean temperature ($^\circ\text{C}$) from Open-Meteo
- `precip_sum_mm`: Daily precipitation sum ($\text{mm}$) from Open-Meteo

**Known data gap:** the Blois (Loire) manual export only covers June 1 – August 27, 2026 (88 of 92 days) -- the source export did not include the final days of August. This shows up as a shorter series for Blois in Tableau; it is a genuine gap in the provided source data, not a pipeline defect.

**In summary:** the project combines five river monitoring stations across four major European river basins. German observations use NIWIS daily water levels and official reference thresholds. French observations use Hydro-Eaufrance daily means derived from sub-daily height measurements, benchmarked against a 10-summer (2016-2025) reference distribution assembled from the same source. Because French stations use local gauge datums and publish no official reference-period classification, cross-station comparisons rely on within-station percentile ranks (`relative_position_pct`) rather than absolute water levels.

#### French reference baseline construction
For each French station, the ten merged summers in `data/raw/hydro_eaufrance/Historic/` are aggregated to daily means. For a given calendar day, the reference sample pools all historical daily means falling within **±7 calendar days across all 10 summers** (~150 observations), which keeps percentiles stable -- a single calendar day on its own would only offer 10 values. Each 2026 daily value is then scored as its percentile rank within that pooled sample. Because the reference follows the seasonal curve, this correctly distinguishes "low for early June" from "low for late August" instead of comparing against a single flat summer average.

### 2. Lagged Weather-Hydrology Cross-Correlation
The module `scripts/ingest_meteo.py` computes Pearson cross-correlations between river water level and meteorological drivers across time lags of $0$ to $14$ days, exported to `output/meteo_river_correlation.csv` with columns `corr_temp_vs_level` and `corr_7d_precip_vs_level` (both metrics are water levels, not discharge -- the column names were corrected to reflect this):
$$\rho(\tau) = \text{corr}\big(\text{river\_value}(t + \tau), \text{weather}(t)\big)$$

`lag_days` = $\tau$ means **weather leads, river lags**: the river value observed $\tau$ days later is correlated against the weather recorded on day $t$. In plain terms: a `lag_days = 5` row means precipitation accumulated during the preceding 7-day window (ending on day $t$) is compared with the river level observed **five days later** ($t+5$). This directionality matters for the interpretation -- it tests whether weather *predicts* a future change in river level, not the reverse.

---

## 5. Quickstart & Execution

This pipeline relies strictly on plain Python (`pandas`, `numpy`) without heavyweight workflow orchestrators.

### Requirements & Setup
```bash
pip install -r requirements.txt
```

### Run Pipeline
```bash
python scripts/build_pipeline.py
```

### Output Files Generated
1. `output/european_drought_summer_2026_tidy.csv`: Master tidy dataset formatted for direct drag-and-drop import into Tableau Public.
2. `output/meteo_river_correlation.csv`: Lagged cross-correlation results table.
3. `output/summary_metrics_2026.csv`: Station-level summary table (minimum levels, record-low days, severity distribution).
4. `output/pegelonline_validation.csv`: NIWIS manual export vs. live PEGELONLINE cross-check (Germany).
5. `output/hydro_eaufrance_validation.csv`: Hydro-Eaufrance manual export vs. live Hub'Eau `observations_tr` cross-check (France).
