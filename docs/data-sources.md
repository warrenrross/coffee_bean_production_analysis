# Data Sources

This analysis draws on six publicly available datasets. All transformations applied to each source are documented below.

---

## 1. BACI — Bilateral Agri-Food Trade (CEPII)

**What it is:** Harmonized bilateral trade flows from the Centre d'Études Prospectives et d'Informations Internationales (CEPII). BACI reconciles the FOB (free on board) values reported by exporters with the CIF (cost, insurance, freight) values reported by importers and corrects for re-exports, producing a single reconciled figure per trading pair.

**Coverage:** 1995–2024 · ~229 exporters × 233 importers

**HS codes used:** 090111 (Coffee, not roasted, not decaffeinated) and 090112 (Coffee, not roasted, decaffeinated)

**Key columns:** `Exporter_ISO3`, `Importer_ISO3`, `Year`, `Value_1000USD`, `Quantity_tonnes`

**Transformation applied:** Grouped to country-level totals (one export total and one import total per ISO3 per year). Non-country codes S19 and ZA1 are dropped before aggregation. Output: `data/baci_country_trade_aggregated.csv`

**Why BACI over FAOSTAT TCL:** Transit-hub economies (e.g. Germany, Belgium) appear as large exporters in raw FAOSTAT trade data because they re-export imported green coffee. BACI's reconciliation methodology assigns trade flows more accurately to origin and destination.

**License:** Creative Commons Attribution 4.0. Cite as: Gaulier, G. and Zignago, S. (2010). BACI: International Trade Database at the Product-level. CEPII Working Paper N°2010-23.

---

## 2. FAOSTAT — Crops and Livestock Products (QCL)

**What it is:** Country-level production volumes published by the Food and Agriculture Organization of the United Nations.

**Item:** 656 — Coffee, green

**Coverage:** 1961–2023 · ~60 producing countries

**Key columns:** `Area` (country name), `Area Code (M49)` (numeric country code), `Year`, `Value` (production in tonnes)

**Transformation applied:** Regional aggregate rows removed using keyword filter (World, Africa, Asia, Europe, America, Oceania, Low-income, OECD, developing). M49 numeric codes mapped to ISO3 via `pycountry` with a manual crosswalk for legacy or edge-case codes. Output: `data/fao_coffee_production_clean.csv`

**License:** FAO data is publicly available under FAO open data license. Cite as: FAO (2024). FAOSTAT Statistical Database. Rome.

---

## 3. Berkeley Earth / ERA5 — Surface Temperature

**What it is:** Country-level mean annual surface temperature derived from gridded reanalysis data. Berkeley Earth provides station-interpolated land temperature; ERA5 is the ECMWF atmospheric reanalysis product.

**Coverage:** 1950–present · global

**Variable used:** Annual mean surface air temperature (°C), averaged over all grid cells within each country boundary.

**Join key:** ISO3, Year

**Notes:** Values represent area-weighted national averages. High-elevation countries (e.g. Ethiopia, Colombia) may have lower averages than surrounding regions due to topography.

---

## 4. ERA5-Land / World Bank — Annual Rainfall

**What it is:** Annual total precipitation (mm) derived from ERA5-Land reanalysis or World Bank climate data portal. Only 44 of 231 countries have true year-over-year variation from the ERA5-Land centroid fetch; the remaining 187 carry a fixed climatological mean.

**Coverage:** 1981–present · global

**Variable used:** Annual total precipitation (mm)

**Join key:** ISO3, Year

**Limitation:** For most countries, rainfall is treated as a fixed structural characteristic (cross-country variation) rather than a time-varying signal. Regression coefficients on rainfall should be interpreted accordingly.

---

## 5. World Bank — Population

**What it is:** Annual national population estimates from the World Bank World Development Indicators.

**Indicator:** SP.POP.TOTL — Population, total

**Coverage:** 1960–2023 · global

**Variable used:** Total population (persons)

**Transformation:** Log-transformed (`ln(Population)`) before regression because population spans approximately 3 orders of magnitude across the sample countries.

**Join key:** ISO3, Year

**License:** CC-BY 4.0. World Bank Open Data.

---

## 6. Crude Oil Price (Brent)

**What it is:** Annual average Brent crude oil spot price, used as a proxy for global commodity market conditions and logistics costs.

**Coverage:** 1987–present

**Variable used:** Annual average Brent crude (USD per barrel)

**Join key:** Year only (this is a global series with no country dimension)

**Notes:** Oil price joins on Year across all country-year observations. It captures global macroeconomic cycles rather than country-specific cost structures.

**Common sources:** U.S. Energy Information Administration (EIA), Federal Reserve Economic Data (FRED).

---

## Panel Construction

The analysis panel (`data/coffee_analysis_panel.csv`) is built by:

1. Taking `fao_coffee_production_clean.csv` as the base (restricts to known coffee-producing countries)
2. Left-joining `baci_country_trade_aggregated.csv` on `(ISO3, Year)`
3. Merging temperature, rainfall, population, and oil price series on `(ISO3, Year)` or `Year`
4. Filtering to rows where `Production_tonnes > 0`

Join key: `(ISO3, Year)` · Expected rows: ~1,500–2,100 · Coverage: ~60 countries × 1995–2024
