# Data Dictionary — `coffee_analysis_panel.csv`

## File Overview

| Property | Value |
|---|---|
| **File name** | `coffee_analysis_panel.csv` |
| **Rows** | 4,782 |
| **Columns** | 9 |
| **Unit of observation** | One row per coffee-producing country per year |
| **Coverage (years)** | 1961–2024 |
| **Coverage (countries)** | 81 unique ISO3 codes |
| **Join key** | `(ISO3, Year)` |
| **Produced by** | Task C of `data_collection_spec.md` |
| **Source data** | Left join of `fao_coffee_production_clean.csv` (Task B) onto `baci_country_trade_aggregated.csv` (Task A), filtered to `Production_tonnes > 0` |

## Role in the Project

This is the **intermediate analysis panel** — the result of joining FAO production data with BACI trade data and filtering to coffee-producing countries only. It contains all years from 1961 to 2024 but does **not yet include the climate and economic covariates** (temperature, rainfall, population, oil price). Those are added in the final panel (`coffee_analysis_panel_with_covariates.csv`).

This file is retained for **provenance and reproducibility**: it demonstrates the join result before the 1995–2024 window restriction is applied, and it allows independent verification of the production and trade data before covariates are attached.

**Join logic:** FAO production is the left table. Every row in this file has a valid `Production_tonnes` value (> 0). BACI trade values are attached where a matching `(ISO3, Year)` exists in the trade aggregation; otherwise trade columns are `NaN`. This is expected for pre-1995 rows (BACI does not cover years before 1995) and for minor producers with no recorded BACI trade flows.

---

## Column Descriptions

### `ISO3`
- **Type:** String (3-character code)
- **Description:** ISO 3166-1 alpha-3 country code. Primary join key across all datasets. Identifies the country that produced the coffee.
- **Nulls:** 0

---

### `Country_Name`
- **Type:** String
- **Description:** Country name sourced from FAO (`Country_Name_FAO` in the production file, renamed here for consistency). Reflects FAO naming conventions as of the FAOSTAT December 2025 snapshot.
- **Notes:** Do not use as a join key. For the Ethiopia case, the pre-1993 rows carry the name "Ethiopia PDR" and post-1993 rows carry "Ethiopia", but both map to `ISO3 = ETH`.
- **Nulls:** 0

---

### `Year`
- **Type:** Integer
- **Description:** Calendar year of the observation.
- **Range:** 1961–2024
- **Nulls:** 0

---

### `Production_tonnes`
- **Type:** Float
- **Description:** Volume of green coffee beans produced by this country in this year, in **metric tonnes**. All values are strictly greater than zero (the `Production_tonnes > 0` filter was applied in Task C).
- **Role in project:** **Response variable Y₁** in Model A of the regression analysis. Log-transformed (`ln(Production_tonnes)`) before modeling.
- **Range:** 0.010 – 3,705,719 tonnes
- **Nulls:** 0 (rows with null or zero production were filtered out)

---

### `FAO_Flag`
- **Type:** String (single character)
- **Description:** FAOSTAT data quality flag for the `Production_tonnes` value. Carried through from `fao_coffee_production_clean.csv` for traceability.
- **Role in project:** Metadata only — not used in statistical models.

| Flag | Meaning |
|---|---|
| `A` | Official figure from national statistical office |
| `E` | FAO estimate |
| `X` | Figure from an international organization |
| `I` | Imputed by FAO |
| `M` | Data not available (`Production_tonnes` will be NaN — but these were filtered out) |

---

### `Export_Value_1000USD`
- **Type:** Float
- **Description:** Total value of green coffee exported by this country in this year, in **thousands of US dollars**. Sourced from BACI trade aggregation.
- **Role in project:** **Response variable Y₂** in Model B of the regression analysis. Log-transformed (`ln(Export_Value_1000USD)`) before modeling.
- **Range:** 0.001 – 11,200,594 (thousand USD) where not null
- **Nulls:** 2,777 (58.1% of rows) — the majority of nulls are pre-1995 rows where BACI data does not exist. Within the 1995–2024 window, the null rate drops to ~10%, representing minor producing countries with no BACI trade records.

---

### `Export_Qty_tonnes`
- **Type:** Float
- **Description:** Total quantity of green coffee exported by this country in this year, in **metric tonnes**. Sourced from BACI trade aggregation.
- **Role in project:** Supplemental — used to compute export unit value (`Export_Value_1000USD * 1000 / Export_Qty_tonnes`) if needed. Also a cross-check against `Production_tonnes`: export quantity should not greatly exceed production unless the country is a significant re-exporter.
- **Nulls:** 2,777 (same rows as `Export_Value_1000USD`)

---

### `Import_Value_1000USD`
- **Type:** Float
- **Description:** Total value of green coffee imported by this country in this year, in **thousands of US dollars**. Sourced from BACI trade aggregation.
- **Role in project:** Supplemental reference variable — not used as a predictor or response in the primary regression models. Useful for understanding the trade balance of producing countries (many large producers also import small quantities of specialty varieties).
- **Nulls:** 2,777 + additional rows where the country appeared as a producer but not as an importer in BACI.

---

### `Import_Qty_tonnes`
- **Type:** Float
- **Description:** Total quantity of green coffee imported by this country in this year, in **metric tonnes**.
- **Role in project:** Supplemental — same as `Import_Value_1000USD`.
- **Nulls:** Same pattern as `Import_Value_1000USD`.

---

## Known Issues and Caveats

| Issue | Detail |
|---|---|
| **Pre-1995 trade nulls are structural** | 58.1% of rows have null trade values because BACI begins in 1995. This is not a data quality problem. The final analysis panel (`coffee_analysis_panel_with_covariates.csv`) is restricted to 1995–2024 and has a much lower null rate (~10%). |
| **This file is not analysis-ready** | Climate covariates (temperature, rainfall) and economic covariates (population, oil price) are not yet joined. Use `coffee_analysis_panel_with_covariates.csv` for all statistical analysis. |
| **81 countries vs. expected 50–70** | The spec estimated 50–70 producing countries. 81 is slightly above this range, primarily because the FAO data includes some small territories (e.g. Puerto Rico, Guadeloupe, Martinique) that grow trivial quantities. These territories are missing climate/population data and are excluded from the final covariate panel. |
