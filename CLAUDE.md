# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project Overview

**Grounds for Correlation** — an exploratory data analysis of whether average temperature, average rainfall, annual population, and crude oil price have statistically significant correlations with coffee bean production volume and export revenue, across ~60 producing countries from 1995–2024.

- **Live analysis:** https://warrenrross.github.io/coffee_bean_production_analysis/
- **Presentation:** Marimo interactive notebooks, auto-published to GitHub Pages on every push to `main` via `.github/workflows/publish.yml`
- **Primary notebook:** `marimo/coffee_analysis.py`

## Repository Structure

```
marimo/          ← Marimo notebook source (primary — edit here)
notebooks/       ← Jupyter notebooks (EDA / exploration)
scripts/         ← Jupytext-synced .py (percent format, for clean git diffs)
data/            ← Processed panel CSVs (see data/README.md for what's tracked)
figures/         ← Exported PNGs, named descriptively
docs/            ← data-sources.md, methodology.md, git-workflow.md
```

## Data Schema

The analysis panel (`data/coffee_analysis_panel.csv`) is one row per country per year, 1995–2024, coffee-producing countries only.

| Column | Type | Source | Notes |
|---|---|---|---|
| `ISO3` | string | — | ISO 3166-1 alpha-3 join key |
| `Country_Name` | string | FAO | |
| `Year` | int | — | 1995–2024 |
| `Production_tonnes` | float | FAOSTAT QCL item 656 | Response Y₁ |
| `Export_Value_1000USD` | float | BACI aggregated | Response Y₂ |
| `Export_Qty_tonnes` | float | BACI aggregated | |
| `Import_Value_1000USD` | float | BACI aggregated | Supplemental |
| `Import_Qty_tonnes` | float | BACI aggregated | Supplemental |
| `Avg_Temp_C` | float | Berkeley Earth / ERA5 | Predictor X₁ |
| `Rain_mm` | float | ERA5-Land / World Bank | Predictor X₂ |
| `Population` | float | World Bank | Predictor X₃ |
| `Oil_Price_Brent_USD` | float | Various | Predictor X₄; joined on Year only |

**Why BACI for trade data:** BACI reconciles exporter- and importer-reported figures and corrects for re-exports. Country-level totals are more accurate than FAOSTAT TCL for transit-hub economies. Coverage starts 1995.

**Rainfall limitation:** Only 44 of 231 countries have true interannual variation (ERA5-Land centroid fetch). The remaining 187 carry a fixed climatological mean. Treat rainfall as a structural cross-country characteristic in regression, not a time-varying signal.

## Environment

```bash
pip install marimo pandas numpy scipy statsmodels matplotlib seaborn plotly \
            geopandas pycountry jupytext nbdime nbstripout

# Run Marimo notebook
marimo edit marimo/coffee_analysis.py

# Sync a Jupyter notebook with Jupytext
jupytext --sync notebooks/<name>.ipynb
```

## Notebook Authoring Workflow

- **Primary path:** Edit `marimo/coffee_analysis.py` directly → push → GitHub Actions publishes HTML
- **Jupyter path:** Edit `notebooks/<name>.ipynb` → Jupytext auto-syncs to `scripts/<name>.py` and `docs/<name>.md` → nbstripout removes outputs before commit
- Never edit `scripts/` or `docs/` directly — they are Jupytext-managed derivatives

## Current Status (as of 2026-04-21)

### What's Done
- Repo scaffolded, initialized, and pushed to GitHub (`warrenrross/coffee_bean_production_analysis`)
- All 4 processed data files are in `data/`:
  - `coffee_analysis_panel_with_covariates.csv` — **primary analysis file** (~1,800 rows, all 15 columns including `FAO_Flag` and `Brent_Avg`)
  - `coffee_analysis_panel.csv` — intermediate panel
  - `baci_country_trade_aggregated.csv` — BACI country-level aggregates
  - `fao_coffee_production_clean.csv` — FAO production cleaned
- `marimo/coffee_analysis.py` — notebook is complete and launches successfully
- `marimo` installed (`python3 -m marimo`, v0.23.2) and tested locally

### Known Bug: `corr_df` NameError
The correlation results cell wraps its logic in an inner `def _(): ...` function (Marimo anti-collision pattern), which traps `corr_df` in the inner scope. The downstream conclusions cell (`def _(corr_df, mo, pd):`) raises `NameError: name 'corr_df' is not defined`.

**Fix documented in:** `docs/fix_corr_df_nameerror.md`  
**Summary:** Split the broken cell into two — one that computes and `return (corr_df,)`, one that displays. Affected lines: ~350–406. No changes needed to the downstream consumer at ~717.

### Architecture Decision
No DuckDB. The panel is already built and 1,800 rows; pandas is perfectly adequate. Stick with pandas throughout.

### What's Next
1. Apply the `corr_df` fix (see `docs/fix_corr_df_nameerror.md`)
2. Run full notebook end-to-end (`Cmd+Shift+Enter`) — watch for any other NameErrors from other inner-function-wrapped cells
3. Verify all 4 analysis sections render: EDA → Correlation → Regression → Model Adequacy
4. Enable GitHub Pages on the repo (Settings → Pages → Source: GitHub Actions)
5. Push `marimo/` to trigger auto-publish to GitHub Pages

### Running Locally
```bash
cd coffee_bean_production_analysis
python3 -m marimo edit marimo/coffee_analysis.py
# Opens at http://localhost:2718
```
Note: `marimo` may not be on PATH after `pip3 install`; use `python3 -m marimo` as the reliable invocation.

---

## Key Analytical Patterns

- **Regional aggregate filtering (FAOSTAT):** Exclude rows where country name contains 'World', 'Africa', 'Asia', 'Europe', 'America', 'Oceania', 'Low-income', 'OECD', 'developing'
- **Log transforms:** `Production_tonnes` and `Export_Value_1000USD` are right-skewed — use `np.log1p()` before regression. `Population` spans 3 orders of magnitude — also log-transform.
- **Export unit value:** `(Export_Value_1000USD * 1000) / Export_Qty_tonnes`; trim to [100, 50000] USD/tonne for outlier removal
- **Correlation test:** `scipy.stats.pearsonr(x, y)` → r, p-value. T₀ = r√[(n−2)/(1−r²)], df = n−2
- **MLR:** `statsmodels.formula.api.ols('np.log1p(Production_tonnes) ~ Avg_Temp_C + Rain_mm + np.log1p(Population) + Oil_Price_Brent_USD', data=panel).fit()`
- **Map joins:** BACI uses `ISO3`; geopandas Natural Earth uses `iso_a3`

## Publishing

Pushing any change to `marimo/` triggers `.github/workflows/publish.yml`, which exports all notebooks to `docs/site/*.html` and deploys to GitHub Pages. The `docs/site/` directory is gitignored — do not commit HTML files manually.
