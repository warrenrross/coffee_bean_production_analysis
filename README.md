# Grounds for Correlation

### Do climate, population, and oil price predict coffee bean production and export revenue?

**[View the live analysis →](https://warrenrross.github.io/coffee_bean_production_analysis/)**

---

## Overview

Coffee is one of the world's most traded agricultural commodities, grown in a narrow equatorial belt where conditions vary dramatically by country. This project investigates whether four measurable factors — average temperature, average rainfall, annual population, and crude oil price — have statistically significant correlations with a country's coffee bean production volume and export revenue.

The analysis covers **~60 coffee-producing countries across 30 years (1995–2024)**, combining agricultural production data from the FAO with harmonized trade data from BACI/CEPII, country-level climate data, and macroeconomic indicators. It is published as an interactive [Marimo](https://marimo.io) notebook so that all charts, tables, and statistical outputs are fully reproducible and explorable in the browser.

---

## The Question

> *Do average temperature, average rainfall, annual population, and crude oil price have statistically significant linear relationships with coffee bean production and export revenue — and if so, how strongly do they predict those outcomes together?*

This is framed as an exploratory analysis, not a causal study. The goal is to document which factors co-vary with agricultural output and trade revenue across the producing world, surface the patterns that hold across decades, and be transparent about what the data can and cannot show.

---

## Data Sources

| Source | Description | Coverage |
|---|---|---|
| [FAOSTAT QCL](https://www.fao.org/faostat/en/#data/QCL) | Country-level coffee production (tonnes), item "Coffee, green" (code 656) | 1961–present |
| [BACI/CEPII](https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37) | Harmonized bilateral coffee trade flows; HS codes 090111 + 090112 | 1995–2024 |
| [Berkeley Earth](https://berkeleyearth.org) / [ERA5](https://www.ecmwf.int/en/forecasts/dataset/ecmwf-reanalysis-v5) | Country annual average temperature (°C) | 1995–2024 |
| [World Bank / ERA5-Land](https://data.worldbank.org) | Country annual average rainfall (mm/year) | 1995–2024 |
| [World Bank](https://data.worldbank.org/indicator/SP.POP.TOTL) | Annual population by country | 1995–2024 |
| Various (Brent/WTI) | Annual average crude oil price (USD/barrel) | 1995–2024 |

Full source documentation, coverage notes, and known limitations: [`docs/data-sources.md`](docs/data-sources.md)

**A note on trade data:** Export and import totals are derived from BACI rather than FAOSTAT TCL. BACI reconciles both exporter- and importer-reported figures for every bilateral flow and corrects for re-exports, producing more accurate country-level totals for transit-hub economies. See [`docs/methodology.md`](docs/methodology.md) for detail.

---

## Analysis

The Marimo notebook walks through the full analysis in order:

1. **Exploratory Data Analysis** — descriptive statistics, distributions, time series of global production, scatter plots of each predictor against each response
2. **Correlation Analysis** — Pearson *r* and hypothesis tests (H₀: ρ = 0) for all predictor–response pairs
3. **Multiple Linear Regression** — two models (production, export revenue) with four predictors; ANOVA tables, coefficient estimates, confidence intervals
4. **Model Adequacy** — residual plots, normality checks; transparent reporting of assumption violations

All statistical outputs include the test statistic, p-value, and plain-English conclusion. Charts are interactive.

**Live notebook:** [warrenrross.github.io/coffee_bean_production_analysis](https://warrenrross.github.io/coffee_bean_production_analysis/)

---

## Repository Structure

```
coffee_bean_production_analysis/
├── marimo/              ← Marimo notebook source files (primary analysis)
├── notebooks/           ← Jupyter notebooks (EDA, exploration)
├── scripts/             ← Jupytext-synced .py versions of notebooks
├── data/                ← Processed panel datasets (raw sources gitignored)
├── figures/             ← Exported PNGs from the analysis
├── docs/                ← Documentation: data sources, methodology, git workflow
│   └── site/            ← Auto-generated GitHub Pages output (gitignored)
├── .github/workflows/   ← GitHub Actions: auto-publish Marimo → GitHub Pages
├── jupytext.toml        ← Jupytext sync configuration
├── .pre-commit-config.yaml  ← Pre-commit hooks (Jupytext sync, Marimo validation)
└── README.md            ← This file
```

---

## Setup

```bash
# Clone
git clone https://github.com/warrenrross/coffee_bean_production_analysis.git
cd coffee_bean_production_analysis

# Install dependencies
pip install marimo pandas numpy scipy statsmodels matplotlib seaborn plotly \
            geopandas pycountry jupytext nbdime nbstripout

# Run the Marimo notebook interactively
marimo edit marimo/coffee_analysis.py
```

The notebook will open in your browser. All analysis runs locally against the `data/` CSVs.

---

## Publishing Pipeline

On every push to `main` that touches `marimo/`, a GitHub Actions workflow automatically:

1. Exports all Marimo notebooks to self-contained interactive HTML
2. Generates an index page
3. Deploys to GitHub Pages

No manual HTML export step required. See [`.github/workflows/publish.yml`](.github/workflows/publish.yml) and [`docs/git-workflow.md`](docs/git-workflow.md).

---

## License

Data sources are subject to their original terms (FAOSTAT: CC BY-NC-SA 3.0; BACI: CC BY-NC 4.0; World Bank: CC BY 4.0; Berkeley Earth: CC BY-NC 4.0). Analysis code and documentation in this repository: [MIT License](LICENSE).
