# Data Dictionary — `fao_coffee_production_clean.csv`

## File Overview

| Property | Value |
|---|---|
| **File name** | `fao_coffee_production_clean.csv` |
| **Rows** | 5,080 |
| **Columns** | 5 |
| **Unit of observation** | One row per country per year |
| **Coverage (years)** | 1961–2024 |
| **Coverage (countries)** | 81 unique ISO3 codes |
| **Join key** | `(ISO3, Year)` |
| **Produced by** | Task B of `data_collection_spec.md` |
| **Source data** | FAOSTAT QCL dataset, Item "Coffee, green" (item code CPC `01610`), Element "Production", downloaded as bulk CSV from `https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_All_Data_(Normalized).zip` (bulk snapshot dated December 2025) |

## Role in the Project

This file provides **Response Variable Y₁ — coffee bean production volume (tonnes)**. It is the primary source of the dependent variable in Model A of the regression analysis, and it also defines which countries qualify as "producing countries" for the panel filter (only rows where `Production_tonnes > 0` are retained in the final panel).

It feeds directly into **Task C** (panel assembly) as the left table in the join, meaning all rows in the final panel must have a corresponding row here.

**Why FAOSTAT QCL for production, not trade:** FAOSTAT's QCL (Crops and Livestock Products) domain contains the authoritative country-level production statistics as reported by national statistical offices and verified by FAO. It covers 1961 to the present, providing a much longer time series than the BACI trade data (which begins in 1995). Production quantities in QCL are expressed in metric tonnes at the farm/harvest level, making them the appropriate measure of physical output.

---

## Column Descriptions

### `ISO3`
- **Type:** String (3-character code)
- **Description:** ISO 3166-1 alpha-3 country code. Mapped from FAO's native M49 numeric area codes using the `pycountry` library plus a manual crosswalk for codes not recognized by `pycountry`.
- **Source:** Derived — mapped from `Area Code (M49)` in the raw FAOSTAT download.
- **Mapping method:** `pycountry.countries.get(numeric=str(m49).zfill(3))`. Manual overrides applied for:
  - M49 `230` → `ETH` (Ethiopia PDR — pre-1993 FAO name for Ethiopia)
  - M49 `159` → excluded (FAO aggregate "China" — mainland production covered by M49 `156` → `CHN`)
  - Melanesia, Polynesia, LIFDCs, NFIDCs → excluded (regional/income-group aggregates)
- **Nulls:** 0 (rows with no ISO3 mapping were dropped before saving)

---

### `Country_Name_FAO`
- **Type:** String
- **Description:** Country name as it appears in the FAOSTAT source data. Retained for human readability and provenance tracing. May differ from BACI country names for the same ISO3 code (e.g. FAO uses "Viet Nam"; BACI uses "Vietnam").
- **Source:** `Area` column from the raw FAOSTAT download.
- **Notes:** One encoding artifact was corrected: "CÃ´te d'Ivoire" → "Côte d'Ivoire". Do not use as a join key — use `ISO3`.
- **Nulls:** 0

---

### `Year`
- **Type:** Integer
- **Description:** Calendar year of the production observation.
- **Range:** 1961–2024 (64 years)
- **Source:** `Year` column from the raw FAOSTAT download.
- **Notes:** The full 1961–2024 range is retained in this intermediate file. The analysis window is constrained to 1995–2024 in the final panel, where all covariates are available.
- **Nulls:** 0

---

### `Production_tonnes`
- **Type:** Float
- **Description:** Volume of green coffee beans produced by this country in this year, in **metric tonnes**. Represents physical output at the farm/harvest level, before any processing, export, or domestic consumption.
- **Role in project:** **Response variable Y₁** in the regression and correlation analysis. Log-transformed (`ln(Production_tonnes)`) before modeling due to right skew — Brazil alone produces ~3.7 million tonnes/year while small producers may produce fewer than 100 tonnes.
- **Range:** 0.0 – 3,705,719 tonnes (Brazil, 2020)
- **Nulls:** 145 — FAO uses the flag `M` to indicate "data not available" for these rows; the value is stored as `NaN`. See `FAO_Flag` column.
- **Notes:** Rows where `Production_tonnes` is 0 or null are filtered out in Task C (the final panel retains only `Production_tonnes > 0`).

---

### `FAO_Flag`
- **Type:** String (single character)
- **Description:** Quality/methodology flag assigned by FAO to each data point. Indicates the reliability and origin of the production estimate.
- **Source:** `Flag` column from the raw FAOSTAT download.
- **Role in project:** Metadata only — not used as a predictor or response. Useful during EDA to identify observations that may warrant caution (e.g. `E` = estimated, `M` = missing).

**Flag values in this dataset:**

| Flag | FAO Definition | Count | Notes |
|---|---|---|---|
| `A` | Official figure | 3,333 | Highest quality — reported by national statistical offices |
| `E` | Estimated value | 671 | FAO estimate, usually based on trend extrapolation or regional averages |
| `X` | Figure from international organizations | 485 | Sourced from non-FAO international bodies |
| `I` | Imputed value | 446 | Calculated by FAO using imputation methods |
| `M` | Data not available | 145 | No data exists; `Production_tonnes` is `NaN` for these rows |

---

## Known Issues and Caveats

| Issue | Detail |
|---|---|
| **Analysis window mismatch** | This file covers 1961–2024, but the analysis is restricted to 1995–2024 because the BACI trade data and all climate/economic covariates begin in 1995. The pre-1995 rows are preserved here for provenance but are excluded from `coffee_analysis_panel_with_covariates.csv`. |
| **145 null production values** | All carry flag `M` (missing). These rows are dropped from the final panel by the `Production_tonnes > 0` filter. |
| **Ethiopia split** | FAO records Ethiopia as "Ethiopia PDR" (M49 `230`) for pre-1993 data and "Ethiopia" (M49 `231`) for 1993 onward. Both are mapped to `ETH`. There is no overlap in years — the two series are contiguous, not duplicated. |
| **China mainland** | FAO reports China mainland as M49 `156` ("China, mainland"). The FAO aggregate "China" (M49 `159`) was excluded to avoid double-counting. The production figures for `CHN` in this file represent mainland China only. |
| **Taiwan** | Reported as M49 `158` ("China, Taiwan Province of") → mapped to `TWN`. Production is small (< 1,000 tonnes/year) and is included for completeness. |
| **FAOSTAT QCL snapshot date** | The bulk download used reflects the FAOSTAT database as of December 2025. The most recent year (2024) may contain preliminary or estimated figures for some countries. |
