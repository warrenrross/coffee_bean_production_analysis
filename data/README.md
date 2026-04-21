# Data Directory

This directory holds processed, analysis-ready datasets that are tracked in version control. Raw source files are large, externally sourced, and gitignored — see below for how to obtain them.

## Tracked Files

| File | Rows (approx.) | Description |
|---|---|---|
| `coffee_analysis_panel.csv` | ~1,800 | Master panel: country × year with all 8 variables. Join key: `(ISO3, Year)`. |
| `baci_country_trade_aggregated.csv` | ~2,800 | BACI bilateral trade collapsed to country-level totals. One row per (ISO3, Year). |
| `fao_coffee_production_clean.csv` | ~2,100 | FAO QCL production data, regional aggregates removed, M49 codes mapped to ISO3. |

## Gitignored Files (not tracked)

Raw source files are excluded because they are large, externally maintained, and not reproducible from this repository alone.

| Pattern | Description |
|---|---|
| `data/*_raw.csv` | Any raw download before transformation |
| `data/baci_country_*.csv` | Intermediate per-country BACI aggregation files |
| `data/global_shipping_*.csv` | Shipping cost / oil price source files |

## How the Tracked Files Were Built

**`baci_country_trade_aggregated.csv`**
Source: BACI HS92 dataset (CEPII), HS codes 090111 and 090112.
Steps: filter to coffee HS codes → remove non-country ISO3 codes (S19, ZA1) → groupby `(Exporter_ISO3, Year)` → sum `Value_1000USD` and `Quantity_tonnes` → repeat for importer side → outer-join on `(ISO3, Year)`.
Columns: `ISO3`, `Year`, `Export_Value_1000USD`, `Export_Qty_tonnes`, `Import_Value_1000USD`, `Import_Qty_tonnes`

**`fao_coffee_production_clean.csv`**
Source: FAOSTAT QCL, item 656 (Coffee, green), all countries, all years, Production element only.
Steps: filter regional aggregates using keyword list (World, Africa, Asia, Europe, America, Oceania, Low-income, OECD) → map M49 numeric codes to ISO3 via pycountry with manual crosswalk for exceptions → drop rows where ISO3 is null.
Columns: `ISO3`, `Country_Name`, `Year`, `Production_tonnes`

**`coffee_analysis_panel.csv`**
Built by left-joining `fao_coffee_production_clean.csv` onto `baci_country_trade_aggregated.csv` on `(ISO3, Year)`, then filtering to rows where `Production_tonnes > 0` and `ISO3` is not null.
Additional columns merged from external sources: `Avg_Temp_C`, `Avg_Rainfall_mm`, `Population`, `Oil_Price_USD`
Columns: `ISO3`, `Country_Name`, `Year`, `Production_tonnes`, `Export_Value_1000USD`, `Export_Qty_tonnes`, `Import_Value_1000USD`, `Import_Qty_tonnes`, `Avg_Temp_C`, `Avg_Rainfall_mm`, `Population`, `Oil_Price_USD`
