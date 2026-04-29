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

## Current Status (last updated 2026-04-23)

### What's Done
- Repo scaffolded, initialized, and pushed to GitHub (`warrenrross/coffee_bean_production_analysis`)
- All 4 processed data files are in `data/`:
  - `coffee_analysis_panel_with_covariates.csv` — **primary analysis file** (~1,800 rows, all 15 columns including `FAO_Flag` and `Brent_Avg`)
  - `coffee_analysis_panel.csv` — intermediate panel
  - `baci_country_trade_aggregated.csv` — BACI country-level aggregates
  - `fao_coffee_production_clean.csv` — FAO production cleaned
- `marimo/coffee_analysis.py` — primary notebook, complete
- `marimo/environmental_sensitivity_followup.py` — follow-up notebook, complete
- `marimo` installed (`python3 -m marimo`, v0.23.2) and tested locally
- `corr_df` NameError resolved — cell split correctly; `corr_df` returned to DAG
- `marimo/__marimo__/` session state added to `.gitignore`
- All Big 5 changes committed and pushed to `main` (commit `8223ed8`); GitHub Pages deployment triggered

### Statistical improvements implemented 2026-04-22
All five "Big 5" items from `../statistical_critique.md` are implemented in `coffee_analysis.py`:

1. **HC3 robust SEs** — `model_a`/`model_b` now use `.fit(cov_type="HC3")`. Raw OLS fits kept as `ols_a`/`ols_b` for influence diagnostics. Column headers updated to `Robust SE`, `Robust t₀`, `Robust 95% CI`.
2. **Clustered SE robustness** — new §4.2 table compares p-values across four specifications: OLS / HC3 / Clustered-ISO3 / Year-FE+Clustered.
3. **Oil price / year fixed effects** — year-FE specification included in §4.2 robustness table with callout that oil becomes weakly identified once year dummies absorb shared time trends.
4. **Rainfall decomposition** — `Rain_mm` replaced in all model formulas with `Rain_mm_country_mean` (structural cross-country climate) and `Rain_mm_within` (within-country year-to-year deviation). Decomposition computed in the panel loading cell.
5. **Influence diagnostics** — new §4.3 adds Cook's D bar chart and top-10 influence table (externally studentized residuals, leverage, Cook's D > 0.5 flag). Uses `OLSInfluence` on raw OLS fits. Country names shown via `pycountry` instead of ISO3 codes.

### Statistical review improvements implemented 2026-04-23
Applied to both notebooks following a full multi-agent stats review:

**`coffee_analysis.py`:**
- **§1.5 scatter plots** — removed misleading i.i.d. p-value annotations (n≈2,000 pooled rows flagged everything significant); now shows Pearson r only with exploratory note. Fixed `__import__("scipy")` anti-pattern → `stats.linregress`.
- **§2.1b Spearman** — added rank-based Spearman ρ cross-check table alongside Pearson; both computed in the correlation loop and returned in `corr_df`.
- **§4.1 Shapiro-Wilk** — fixed biased `residuals[:5000]` slice (was sorted by country, skewed toward early-alphabet) → `stats.shapiro(residuals)` on the full vector.
- **§5.1** — conclusion table wrapped in `mo.md()` with "Plain-English Conclusions" heading (was orphaned `mo.as_html()`).
- **§5.2 teacher phrasings** — rewritten to include verbatim INEG assignment language: exact H₀ rejection sentences, "X% of the variation … is explained by the regression model", and per-predictor "p-value = X < α = 0.05. We reject H₀: β = 0." bullets built dynamically.

**`environmental_sensitivity_followup.py`:**
- **§4 cohort regression (blocker)** — was using raw `Rain_mm` in a pooled multi-country regression, reintroducing the between/within conflation the main workbook fixed. Now uses `Rain_mm_country_mean + Rain_mm_within`. dropna subset, p-value column names, display format, and §4 coefficient plot term mapping all updated to match.
- **§1 tier thresholds** — magic numbers replaced with named constants (`TIER_STRONG_R=0.45`, `TIER_STRONG_DR2=0.10`, `TIER_MOD_R=0.35`, `TIER_MOD_P=0.10`); constants returned from cell for downstream use.
- **§1 `_best_env` NaN fix** — when both r_temp and r_rain are NaN the old code silently assigned "Temperature"; now assigns `None` / `np.nan`.
- **§1.1 display** — tier counts converted from 3-row HTML table to inline bold text; multiple-testing caveat added (n_countries × 2 tests at α=0.05 → several false discoveries expected by chance).
- **§1 markdown** — FWL / screening-not-testing note added explaining the partial-residual approach and pointing graders to the main workbook for formal H₀/H₁ inference.
- **§3 country dropdown** — `"ISO3 - Country"` → `"Country (ISO3)"`; ISO3 extractor updated to match; defensive `"GREY" in globals()` check removed; figure title ASCII hyphen → en-dash.
- **§5 mini-model note** — clarifies why raw `Rain_mm` is used in per-country models (within a single country there is no between-country variation to decompose).

### Architecture decisions
- No DuckDB — panel is 1,800 rows; pandas is adequate throughout.
- Raw OLS fits (`ols_a`, `ols_b`) retained alongside HC3 fits because `OLSInfluence` requires a plain `OLSResults` object and does not work on robust result wrappers.
- `panel_model` (without underscore prefix) returned from the regression cell so downstream influence and robustness cells can reference it.
- Country names displayed via `pycountry` wherever data is surfaced to the user; ISO3 retained only as the internal join key.
- Rainfall decomposition (`Rain_mm_country_mean + Rain_mm_within`) applied in all pooled multi-country regressions in both notebooks. Per-country mini-models intentionally use raw `Rain_mm` — correct because within one country there is no between-country variation.
- Follow-up notebook (`environmental_sensitivity_followup.py`) is a screening tool only; it does not generate its own H₀/H₁ conclusions. All formal inference lives in the main notebook.

### Known issues / remaining work
- Both notebooks have not been run end-to-end locally since 2026-04-23 edits — do this before pushing.
- Statistical critique items 6–10 are logged but not yet implemented (see `../statistical_critique.md`):
  - Missing-data bias check before complete-case filtering
  - Confidence intervals on Pearson ρ (Fisher Z); de-emphasize pooled p-values in conclusions
  - Mean-response CI and prediction intervals for selected country-year scenarios
  - Scale-location plot: replace ad hoc `residuals / residuals.std()` with model-based standardized residuals
  - Model comparison: reduced vs. expanded specifications; interaction terms (e.g. Temp × Rain)
- GitHub Pages not verified since 2026-04-23 edits — push `marimo/` to trigger rebuild.

### What's Next
1. **Run both notebooks locally** — `python3 -m marimo edit marimo/coffee_analysis.py` and `python3 -m marimo edit marimo/environmental_sensitivity_followup.py`; confirm no runtime errors before pushing.
2. **Push to trigger GitHub Pages** — any push touching `marimo/` triggers the publish workflow.
3. **Verify live site** — https://warrenrross.github.io/coffee_bean_production_analysis/
4. **Address statistical critique items 6–10** (see `../statistical_critique.md`)

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
- **MLR (primary):** `.fit(cov_type="HC3")` for inference; keep raw `.fit()` as `ols_a`/`ols_b` for `OLSInfluence`. Rainfall is decomposed: `Rain_mm_country_mean + Rain_mm_within`.
- **MLR formula:** `"ln_Production ~ Avg_Temp_C + Rain_mm_country_mean + Rain_mm_within + ln_Population + Oil_Price_Brent_USD"`
- **Country display:** Always convert ISO3 → country name via `pycountry.countries.get(alpha_3=code).name` before displaying to user.
- **Map joins:** BACI uses `ISO3`; geopandas Natural Earth uses `iso_a3`

## Publishing

Pushing any change to `marimo/` triggers `.github/workflows/publish.yml`, which exports all notebooks to `docs/site/*.html` and deploys to GitHub Pages. The `docs/site/` directory is gitignored — do not commit HTML files manually.
