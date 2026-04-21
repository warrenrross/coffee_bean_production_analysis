# Data Dictionary — `coffee_analysis_panel_with_covariates.csv`

## File Overview

| Property | Value |
|---|---|
| **File name** | `coffee_analysis_panel_with_covariates.csv` |
| **Rows** | 2,233 |
| **Columns** | 15 |
| **Unit of observation** | One row per coffee-producing country per year |
| **Coverage (years)** | 1995–2024 (30 years) |
| **Coverage (countries)** | 78 unique ISO3 codes |
| **Join key** | `(ISO3, Year)` for country-level variables; `Year` only for oil price |
| **Produced by** | Extended Task C — `coffee_analysis_panel.csv` restricted to 1995–2024 and joined to all four covariates |
| **Primary use** | **All statistical analysis in the project** — correlation tests, MLR models, EDA |

## Role in the Project

This is the **primary analysis-ready dataset**. It is the single file used for all statistical work: EDA, the 8 Pearson correlation tests, Model A (ln Production), Model B (ln Export Value), model adequacy checks, and all visualizations.

The panel structure is **country × year**: each row represents one country in one year and contains that country-year's production volume, export revenue, average temperature, annual rainfall, population, and Brent crude oil price. The two response variables (Y₁, Y₂) and all four predictors (X₁–X₄) are present in this file.

**Why 1995–2024:** This is the intersection of all data sources. BACI trade data begins in 1995; temperature (Berkeley Earth / ERA5), rainfall (ERA5-Land / World Bank), population (World Bank), and oil price are all available from 1995 onward. Restricting to this window ensures complete covariate coverage for every row.

---

## Column Descriptions — Identifiers

### `ISO3`
- **Type:** String (3-character code)
- **Description:** ISO 3166-1 alpha-3 country code. Primary join key for all datasets. Every row in this file is uniquely identified by `(ISO3, Year)`.
- **Nulls:** 0

---

### `Country_Name`
- **Type:** String
- **Description:** Country name from the FAO source data. For reference only — use `ISO3` for all programmatic joins and grouping operations.
- **Nulls:** 0

---

### `Year`
- **Type:** Integer
- **Description:** Calendar year of the observation.
- **Range:** 1995–2024
- **Nulls:** 0

---

## Column Descriptions — Response Variables

### `Production_tonnes`
- **Type:** Float
- **Description:** Volume of green coffee beans produced by this country in this year, in **metric tonnes**. All values are strictly greater than zero.
- **Role in project:** **Response variable Y₁ — Production.** Used as `ln(Production_tonnes)` in Model A:
  `ln(Production) = β₀ + β₁·Temp + β₂·Rain + β₃·ln(Population) + β₄·Oil + ε`
- **Source:** FAOSTAT QCL, item "Coffee, green" (CPC code `01610`)
- **Range:** 0.010 – 3,705,719 tonnes
- **Nulls:** 0

---

### `FAO_Flag`
- **Type:** String (single character)
- **Description:** FAOSTAT data quality flag for the `Production_tonnes` value.
- **Role in project:** Metadata — not used in models. Useful during EDA to assess data quality for specific country-year observations.

| Flag | Meaning |
|---|---|
| `A` | Official figure — highest quality |
| `E` | FAO estimate |
| `X` | Sourced from international organization |
| `I` | FAO-imputed value |

---

### `Export_Value_1000USD`
- **Type:** Float
- **Description:** Total value of green coffee exported by this country in this year, in **thousands of US dollars (1000 USD)**. Aggregated from BACI bilateral trade flows.
- **Role in project:** **Response variable Y₂ — Export Revenue.** Used as `ln(Export_Value_1000USD)` in Model B:
  `ln(Export_Value) = β₀ + β₁·Temp + β₂·Rain + β₃·ln(Population) + β₄·Oil + ε`
- **Source:** BACI/CEPII bilateral coffee trade data, aggregated to country level
- **Range:** 0.001 – 11,200,594 (thousand USD)
- **Nulls:** 228 (10.2%) — producing countries with no recorded BACI export flow in a given year. These rows can still be used in Model A (production analysis) but must be excluded from Model B.

---

### `Export_Qty_tonnes`
- **Type:** Float
- **Description:** Total quantity of green coffee exported by this country in this year, in **metric tonnes**. Aggregated from BACI bilateral trade flows.
- **Role in project:** Supplemental — used for computing export unit value and cross-checking. Not a primary model variable.
- **Nulls:** 228 (same rows as `Export_Value_1000USD`)

---

### `Import_Value_1000USD`
- **Type:** Float
- **Description:** Total value of green coffee imported by this country in this year, in **thousands of US dollars**.
- **Role in project:** Supplemental reference. Not used in primary regression models.
- **Nulls:** Higher than export nulls — many producing countries do not import coffee.

---

### `Import_Qty_tonnes`
- **Type:** Float
- **Description:** Total quantity of green coffee imported by this country in this year, in **metric tonnes**.
- **Role in project:** Supplemental reference.

---

## Column Descriptions — Predictor Variables (X₁–X₄)

### `Avg_Temp_C`
- **Type:** Float
- **Description:** Country-level annual average surface temperature in **degrees Celsius (°C)**. Represents the mean of monthly average temperatures across all 12 months of the calendar year.
- **Role in project:** **Predictor X₁ — Temperature.** Used untransformed in both regression models. Expected direction: negative correlation with production (coffee grows optimally at ~18–24°C; temperatures outside this range reduce yield).
- **Source:** Berkeley Earth land-surface temperature dataset for 1995–2016; ERA5 reanalysis (Open-Meteo API) for 2017–2024. See `Temp_Source` column for per-row attribution.
- **Range:** 4.50°C – 29.19°C across all country-years in this panel
- **Nulls:** 64 — four territories with no match in the temperature dataset (Taiwan, Guadeloupe, Martinique, Puerto Rico). See caveats below.

---

### `Temp_Source`
- **Type:** String (categorical)
- **Description:** Identifies the data source used for the `Avg_Temp_C` value for this country-year.
- **Role in project:** Metadata. Useful during model adequacy checks to verify that the Berkeley Earth / ERA5 transition at 2016/2017 does not introduce a systematic discontinuity in the residuals.

| Value | Count | Description |
|---|---|---|
| `Berkeley Earth` | 1,521 | Berkeley Earth land-surface station data, 1995–2016 |
| `ERA5 (Open-Meteo)` | 585 | ERA5 reanalysis, 2017–2024 |
| `Berkeley Earth (proxy: fiji)` | 41 | Berkeley Earth data from a proxy country (Fiji used as proxy for nearby Pacific islands) |
| `Berkeley Earth (proxy: ghana)` | 22 | Berkeley Earth data from a proxy country (Ghana used as proxy) |

---

### `Rain_mm`
- **Type:** Float
- **Description:** Annual total rainfall (precipitation) for this country in this year, in **millimeters per year (mm/yr)**.
- **Role in project:** **Predictor X₂ — Rainfall.** Used untransformed in both regression models. Expected direction: positive correlation with production (adequate rainfall is necessary for coffee cultivation; most coffee grows in regions with 1,500–2,500 mm/yr).
- **Source:** ERA5-Land reanalysis (Open-Meteo API) for 44 countries with full interannual data; World Bank / FAO climatological means (fixed value repeated across all years) for the remaining 187 countries. See `Rain_Source` for per-row attribution.
- **Range:** 59.0 – 4,063.6 mm/yr
- **Nulls:** 64 (same four territories as `Avg_Temp_C`)

---

### `Rain_Source`
- **Type:** String (categorical)
- **Description:** Identifies the data source and methodology used for the `Rain_mm` value.
- **Role in project:** Critical metadata for interpreting rainfall as a predictor. **The majority of country-years carry a fixed climatological mean**, which means rainfall does not vary year to year for those countries. This is a known limitation: rainfall can be used as a structural cross-country characteristic (wet vs. dry countries) but not as a time-varying within-country signal for 81% of the dataset. This limitation is documented in `project_plan.md` and should be disclosed in the analysis write-up.

| Value | Count | Description |
|---|---|---|
| `Climatological Mean (World Bank / FAO)` | 1,842 | Fixed long-run average; same value repeated for all years |
| `ERA5-Land (Open-Meteo)` | 240 | True interannual reanalysis data — varies year to year |
| `Climatological Mean (published reference)` | 60 | Fixed mean from a published climate reference |
| `Climatological Mean (proxy)` | 27 | Fixed mean estimated from a nearby proxy country |

---

### `Population`
- **Type:** Float
- **Description:** Total resident population of this country in this year.
- **Role in project:** **Predictor X₃ — Population.** Log-transformed (`ln(Population)`) in both regression models because population spans three orders of magnitude across countries in this panel (from ~16,000 for small island producers to ~1.45 billion for China). Expected direction: positive correlation with production (larger countries tend to have more land and labor available for coffee farming).
- **Source:** World Bank Development Indicators
- **Range:** 16,314 (small island producers) – 1,450,935,791 (China)
- **Nulls:** 64 (same four territories as `Avg_Temp_C` — World Bank does not publish population for Taiwan, Guadeloupe, Martinique, and Puerto Rico under standard ISO3 codes in this dataset)

---

### `Brent_Avg`
- **Type:** Float
- **Description:** Annual average Brent crude oil price in **US dollars per barrel (USD/bbl)**. This is a global (non-country-specific) variable — every country-year in a given year has the same `Brent_Avg` value.
- **Role in project:** **Predictor X₄ — Oil Price.** Used untransformed in both regression models. Higher oil prices raise the cost of fertilizers (petrochemical-derived), machinery fuel, and international shipping — potentially reducing production or compressing export margins. Direction of effect is uncertain: higher oil may also increase export revenue if coffee is used as a commodity hedge or if fuel costs are passed through to buyers.
- **Source:** See `global_shipping_oil_price_data_dictionary.md` for full source methodology. The `Brent_Avg` column is the annual average of monthly Brent crude spot prices.
- **Range:** $12.79/bbl (1998) – $111.61/bbl (2012)
- **Nulls:** 0 — oil price data is available for all 30 years in the analysis window.
- **Note:** `Brent_High` and `Brent_Low` (annual high and low prices) are available in `global_shipping_oil_price.csv` but are not included in this panel. They can be joined on `Year` if needed for sensitivity analysis.

---

## Panel Coverage Summary

| Variable | Non-null rows | % Coverage |
|---|---|---|
| `Production_tonnes` | 2,233 | 100.0% |
| `Export_Value_1000USD` | 2,005 | 89.8% |
| `Avg_Temp_C` | 2,169 | 97.1% |
| `Rain_mm` | 2,169 | 97.1% |
| `Population` | 2,169 | 97.1% |
| `Brent_Avg` | 2,233 | 100.0% |

The 64-row coverage gap in temperature, rainfall, and population affects four territories: **Taiwan (TWN)**, **Guadeloupe (GLP)**, **Martinique (MTQ)**, and **Puerto Rico (PRI)**. These are sub-national or special administrative units that lack entries in the Berkeley Earth / ERA5 temperature dataset and the World Bank population dataset as used in this project. Rows for these territories should be excluded from any regression model that requires all four predictors.

---

## Derived Variables (computed during analysis, not stored in this file)

The following variables are computed from the panel during the analysis phase and are not stored in this CSV:

| Derived variable | Formula | Purpose |
|---|---|---|
| `ln_Production` | `np.log(Production_tonnes)` | Response Y₁ in Model A — addresses right skew |
| `ln_Export_Value` | `np.log(Export_Value_1000USD)` | Response Y₂ in Model B — addresses right skew |
| `ln_Population` | `np.log(Population)` | Predictor X₃ in both models — compresses 3-order-of-magnitude range |
| `Export_Unit_Value_USD_t` | `(Export_Value_1000USD * 1000) / Export_Qty_tonnes` | Optional EDA variable — coffee price per tonne; trim to [100, 50000] before use |

---

## Known Issues and Caveats

| Issue | Detail |
|---|---|
| **Rainfall is mostly structural, not time-varying** | 82.5% of rows (1,842 + 60 + 27 = 1,929 of 2,233) carry a fixed climatological mean for `Rain_mm`. The value does not change year to year for these countries. Rainfall therefore acts as a cross-sectional country characteristic in most of the panel, not a within-country time-varying regressor. This must be disclosed in the analysis. |
| **64 rows missing all climate/population covariates** | Taiwan, Guadeloupe, Martinique, and Puerto Rico have no temperature, rainfall, or population data. These rows are present in the panel but must be excluded from regression models requiring all predictors. |
| **228 rows missing Export_Value_1000USD** | These producing countries have no BACI trade record in the given year. They can be used in Model A (production) but not Model B (export revenue). |
| **Temperature source discontinuity** | Berkeley Earth data is used for 1995–2016; ERA5 for 2017–2024. Check residual plots for a structural break around 2016–2017 during model adequacy checks. |
| **Oil price is global, not country-specific** | Brent crude is the same for every country in a given year. Its coefficient in the MLR model represents the global-average effect of oil price changes on coffee production/revenue, not a country-specific sensitivity. |
| **Panel is not balanced** | Not every country has data for all 30 years. Some smaller producers appear sporadically. The panel is unbalanced by design — every available country-year with valid production data is included. |
