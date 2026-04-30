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

## Current Status (last updated 2026-04-29)

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

### Statistical improvements (commits `8223ed8` through `c931b25`)
1. **HC3 robust SEs** — `model_a`/`model_b` now use `.fit(cov_type="HC3")`. Raw OLS fits kept as `ols_a`/`ols_b` for influence diagnostics.
2. **Clustered SE robustness** — §4.2 table compares p-values across OLS / HC3 / Clustered-ISO3 / Year-FE+Clustered.
3. **Oil price / year fixed effects** — year-FE specification in §4.2; oil weakly identified once year dummies absorb shared time trends.
4. **Rainfall decomposition** — `Rain_mm` → `Rain_mm_country_mean` + `Rain_mm_within` in all pooled regressions.
5. **Influence diagnostics** — §4.3 Cook's D bar chart and top-10 influence table.
6. **§1.5 scatter plots** — removed misleading i.i.d. p-value annotations; shows Pearson r only.
7. **Spearman ρ cross-check** — added §2.1b rank-based Spearman table alongside Pearson.
8. **Shapiro-Wilk fix** — `stats.shapiro(residuals)` on full vector (was biased slice).
9. **§5.2 teacher phrasings** — verbatim INEG assignment language built dynamically.
10. **19 CPS educational teaching notes** added to `coffee_analysis.py` (commit `c931b25`).

### Follow-up notebook improvements (commits `9f74c65`, `fa8fe28`, `219b301`, `7443db5`)
- **True FWL partial correlation** — both response AND environmental predictors residualized on ln(Population) separately before correlating (commit `9f74c65`).
- **Benjamini-Hochberg FDR correction** — `multipletests(pvals, method='fdr_bh')` applied to all ~148 simultaneous country-level tests; tier logic uses adjusted p-values.
- **Incremental F-test** — `anova_lm(restricted, full)` replaces raw ΔR² threshold for tier classification.
- **Durbin-Watson per country** — DW < 1.5 flagged as autocorrelation warning (p-value inflation risk).
- **§4 selection-bias disclosure** — warning box added for non-random cohort selection.
- **§4 rainfall decomposition** — cohort regression now uses `Rain_mm_country_mean + Rain_mm_within`.
- **§3 local-only note** — dropdown requires live kernel; GitHub Pages viewers are warned.
- **15 CPS educational notes** added to follow-up notebook (commit `fa8fe28`).
- **FWL vs. Factorial vs. RCBD course context** — conceptual comparison cell added after §1 header (commit `219b301`).
- **Mathematical FWL/RCBD equivalence** — annihilator matrix derivation, side-by-side equations, equivalence table, orthogonality explanation appended to course context cell (commit `7443db5`). Cell converted to raw string `r"""..."""` to prevent Python escape-sequence mangling of LaTeX.

### Architecture decisions
- No DuckDB — panel is 1,800 rows; pandas is adequate throughout.
- Raw OLS fits (`ols_a`, `ols_b`) retained alongside HC3 fits because `OLSInfluence` requires a plain `OLSResults` object and does not work on robust result wrappers.
- `panel_model` (without underscore prefix) returned from the regression cell so downstream cells can reference it.
- Country names displayed via `pycountry` wherever data is surfaced to the user; ISO3 retained only as the internal join key.
- Rainfall decomposition applied in all pooled multi-country regressions. Per-country mini-models use raw `Rain_mm` — correct because within one country there is no between-country variation to decompose.
- Follow-up notebook is a screening tool only; it does not generate its own H₀/H₁ conclusions. All formal inference lives in the main notebook.
- LaTeX in `mo.md()` cells must use raw strings `r"""..."""` — regular strings mangle `\top`, `\beta`, `\tau`, `\neq` via Python escape processing.

### Known issues / remaining work
- Both notebooks should be run end-to-end locally before the next major push to confirm no runtime errors.
- Statistical critique items 6–10 are logged but not yet implemented (see `../statistical_critique.md`):
  - Missing-data bias check before complete-case filtering
  - Confidence intervals on Pearson ρ (Fisher Z); de-emphasize pooled p-values in conclusions
  - Mean-response CI and prediction intervals for selected country-year scenarios
  - Scale-location plot: replace ad hoc `residuals / residuals.std()` with model-based standardized residuals
  - Model comparison: reduced vs. expanded specifications; interaction terms (e.g. Temp × Rain)
- Open thesis review issues (see `../followup_thesis_review.md`): causal language in §6, Fisher Z CIs, MIN_OBS adequacy, no dropped-vs-retained analysis, BH applied as two 74-test arrays vs. one joint 148-test correction.
- GitHub Pages not verified since last push — confirm deployment at live site.

### Last push (2026-04-29)
Commit `7443db5` pushed to `main`. Included:
- `marimo/environmental_sensitivity_followup.py` — FWL/RCBD mathematical equivalence section; raw string fix for LaTeX in course-context cell

Previous session pushes also on 2026-04-29:
- `219b301` — FWL vs. Factorial vs. RCBD course context cell
- `fa8fe28` — 15 CPS educational notes in follow-up notebook
- `9f74c65` — 5 critical thesis-review fixes (true FWL, BH, incremental F, DW, §4 disclosure)
- `c931b25` — 19 CPS educational notes in main notebook
- `50bf0f4` — follow-up notebook first push + stats review corrections

### What's Next
1. **Run both notebooks locally** — `python3 -m marimo edit marimo/coffee_analysis.py` and `python3 -m marimo edit marimo/environmental_sensitivity_followup.py`; confirm no runtime errors.
2. **Verify live site** — https://warrenrross.github.io/coffee_bean_production_analysis/
3. **Address statistical critique items 6–10** (see `../statistical_critique.md`)
4. **Address open thesis review issues** (see `../followup_thesis_review.md`)

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
