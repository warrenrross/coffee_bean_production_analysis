# Data Dictionary — `baci_country_trade_aggregated.csv`

## File Overview

| Property | Value |
|---|---|
| **File name** | `baci_country_trade_aggregated.csv` |
| **Rows** | 6,260 |
| **Columns** | 7 |
| **Unit of observation** | One row per country per year |
| **Coverage (years)** | 1995–2024 |
| **Coverage (countries)** | 229 unique ISO3 codes |
| **Join key** | `(ISO3, Year)` |
| **Produced by** | Task A of `data_collection_spec.md` |
| **Source data** | BACI/CEPII bilateral coffee trade flows (`coffee_bilateral_trade_BACI.csv`) |

## Role in the Project

This file is an **intermediate product** used to supply the two response variables and supplemental trade quantities to the final analysis panel. It collapses the raw BACI bilateral flow data — which has one row per exporter–importer–year–HS code combination (136,768 rows) — into a single total export value and a single total import value for each country in each year.

It feeds directly into **Task C** (panel assembly) via a left join on `(ISO3, Year)`.

**Why BACI instead of FAOSTAT TCL for trade data:** BACI (produced by CEPII) reconciles both the exporter-reported and importer-reported figures for every bilateral trade flow and produces a single harmonized value. Critically, it corrects for re-exports — goods that arrive in a transit country (e.g. a European port) and are then shipped onward to a third country are not attributed as exports from the transit country. FAOSTAT TCL does not make this correction and can overstate exports for entrepôt hubs. BACI is therefore the more accurate source for country-level export revenue.

---

## Column Descriptions

### `ISO3`
- **Type:** String (3-character code)
- **Description:** ISO 3166-1 alpha-3 country code. Identifies the country that acted as exporter or importer in a given year. Used as the primary join key across all datasets in this project.
- **Source:** Carried directly from the `Exporter_ISO3` / `Importer_ISO3` columns of the raw BACI file.
- **Notes:** Two non-country codes present in the raw data — `S19` (Other Asia, nes) and `ZA1` (Southern African Customs Union, historical) — were removed before aggregation per Step A1 of the spec.
- **Nulls:** 0

---

### `Country_Name`
- **Type:** String
- **Description:** Human-readable country name corresponding to the ISO3 code. Taken from the exporter-side name where available; falls back to the importer-side name for countries that only appear as importers in the data.
- **Source:** `Exporter_Name` / `Importer_Name` from the raw BACI file.
- **Notes:** Names reflect BACI's labeling conventions, which may differ slightly from FAO or ISO standard names (e.g. historical names for countries that changed names during 1995–2024). Do not use this column as a join key — use `ISO3` instead.
- **Nulls:** 0

---

### `Year`
- **Type:** Integer
- **Description:** Calendar year of the trade observation.
- **Range:** 1995–2024 (30 years)
- **Source:** `Year` column of the raw BACI file.
- **Nulls:** 0

---

### `Export_Value_1000USD`
- **Type:** Float
- **Description:** Total value of green coffee exported by this country in this year, expressed in **thousands of US dollars (1000 USD)**. This is the sum of all bilateral export flows where this country is the exporter, across all HS codes and all destination countries.
- **Role in project:** **Response variable Y₂** (export revenue) in the regression models. Used in `coffee_analysis_panel_with_covariates.csv` after filtering to producing countries only.
- **Range:** 0.001 – 11,200,594 (thousand USD); i.e. approximately $1 USD to $11.2 billion USD
- **Nulls:** 1,124 — a country-year has no export record in BACI (country exported nothing, or BACI has no record for that year). Left as `NaN`; **do not replace with 0** without care, as absence of a record does not definitively confirm zero exports.
- **Transformation in analysis:** Log-transformed (`ln(Export_Value_1000USD)`) as response variable in Model B due to right skew.

---

### `Export_Qty_tonnes`
- **Type:** Float
- **Description:** Total quantity of green coffee exported by this country in this year, in **metric tonnes**. Aggregated across all bilateral flows and HS codes where this country is the exporter.
- **Role in project:** Supplemental quantity variable. Used to compute `Export_Unit_Value_USD_t` (price per tonne) in the transformation pipeline if needed. Also serves as a cross-check against FAO production volumes.
- **Range:** 0.000 – 2,790,450 tonnes
- **Nulls:** 1,124 (same rows as `Export_Value_1000USD`)

---

### `Import_Value_1000USD`
- **Type:** Float
- **Description:** Total value of green coffee imported by this country in this year, in **thousands of US dollars (1000 USD)**. Sum of all bilateral flows where this country is the importer.
- **Role in project:** Supplemental variable — not used as a primary response or predictor in the regression models, but included for reference and potential EDA. Useful for identifying net-exporting vs. net-importing countries.
- **Range:** 0.001 – 3,888,649 (thousand USD)
- **Nulls:** 212

---

### `Import_Qty_tonnes`
- **Type:** Float
- **Description:** Total quantity of green coffee imported by this country in this year, in **metric tonnes**.
- **Role in project:** Supplemental — same as `Import_Value_1000USD`. Can be used to verify that large importers (e.g. Germany, USA) appear as expected.
- **Nulls:** 212 (same rows as `Import_Value_1000USD`)

---

## Known Issues and Caveats

| Issue | Detail |
|---|---|
| **NaN ≠ zero exports** | A null `Export_Value_1000USD` means BACI has no record for that country-year, not necessarily that exports were zero. Small or sporadic exporters may have genuine gaps. |
| **Pre-BACI coverage** | BACI begins in 1995. There is no trade data before 1995 in this file. The analysis window is therefore constrained to 1995–2024. |
| **Netherlands (NLD) large exports** | NLD shows large both imports and exports. This is expected and correct: BACI has already corrected pure re-exports at the bilateral level; residual NLD trade reflects genuine Dutch consumption and re-routed flows. It is not an error. |
| **HS codes included** | All HS codes representing green (unroasted) coffee are included per the source BACI file. See `coffee_bilateral_trade_data_dictionary.pdf` for the full HS code list. |
