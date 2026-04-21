# Methodology

## Research Question

Do average temperature, average rainfall, annual population, and crude oil price have statistically significant correlations with coffee bean production volume and export revenue across producing countries, 1995–2024?

---

## Data Structure

The analysis uses a panel dataset of ~60 coffee-producing countries observed annually from 1995–2024. Each observation is one country in one year. The panel is built by joining FAO production data to BACI country-level trade aggregates on `(ISO3, Year)`, then merging climate, population, and oil price series.

**Response variables (Y)**

| Variable | Symbol | Transform |
|---|---|---|
| Coffee production (tonnes) | Y₁ | ln(Y₁) |
| Export revenue (1000 USD) | Y₂ | ln(Y₂) |

**Predictor variables (X)**

| Variable | Symbol | Transform |
|---|---|---|
| Annual mean temperature (°C) | X₁ | none |
| Annual total rainfall (mm) | X₂ | none |
| National population | X₃ | ln(X₃) |
| Brent crude oil price (USD/bbl) | X₄ | none |

**Why log transforms?** Production and export revenue are right-skewed with high-leverage outliers (Brazil, Vietnam, Colombia dominate volumes). Log transformation compresses the range, linearizes multiplicative relationships, and produces more homogeneous residual variance.

---

## Analysis Steps

### 1. Exploratory Data Analysis

Before hypothesis testing: examine distributions, time trends, and missing data patterns.

- Histograms and QQ plots for all 6 variables before and after log transform
- Time series of global production and export revenue (1995–2024)
- Country-level choropleth maps of mean production and mean export value
- Correlation matrix heatmap across all variables
- Flag potential outliers; check for countries with sparse coverage

### 2. Pairwise Pearson Correlation Tests

Test whether each predictor is linearly correlated with each response. Eight tests total (4 predictors × 2 responses).

**H₀:** ρ = 0 (no linear association)
**H₁:** ρ ≠ 0

**Test statistic:**

T₀ = r × √[(n − 2) / (1 − r²)]

Under H₀, T₀ ~ t(n − 2). Decision: reject H₀ if |T₀| > t(α/2, n−2) or p-value < α.

**α = 0.05** (two-tailed)

All 8 correlations are computed on log-transformed responses and predictors where transforms apply. Results reported as: r, T₀, p-value, and interpretation.

### 3. Multiple Linear Regression

Two MLR models, one per response:

**Model 1 — Production:**
```
ln(Production) = β₀ + β₁(Temp) + β₂(Rain) + β₃·ln(Population) + β₄(OilPrice) + ε
```

**Model 2 — Export Revenue:**
```
ln(Export_Value) = β₀ + β₁(Temp) + β₂(Rain) + β₃·ln(Population) + β₄(OilPrice) + ε
```

For each model: estimate coefficients, standard errors, t-statistics, p-values for each βⱼ. Report overall F-statistic, R², adjusted R².

**Implementation:** `statsmodels.formula.api.ols()` with HC3 heteroskedasticity-consistent standard errors given the panel structure.

### 4. Model Adequacy

Residual diagnostics to assess whether model assumptions hold:

- **Residuals vs fitted values** — check for nonlinearity or heteroskedasticity
- **Normal Q-Q plot of residuals** — assess normality assumption
- **Shapiro-Wilk test** — formal normality test on residuals (n ≤ 5000)
- **Scale-location plot** — homoskedasticity check
- **Leverage / Cook's distance** — identify high-influence observations

If assumptions are violated: document the violation, note its direction of impact on inference, and consider whether subgroup analysis (by region or production tier) is warranted.

---

## Known Limitations

**Rainfall:** Only 44 of 231 countries in the ERA5-Land fetch have true interannual variation. For the remaining 187, rainfall is a fixed country-level mean. Consequently, the rainfall coefficient in MLR captures cross-country structural differences, not within-country time variation. This limits causal interpretation.

**Panel structure:** Standard OLS on panel data ignores within-country serial correlation. Inference is approximate. Fixed-effects or clustered standard errors are noted as a robustness extension.

**Oil price:** A global annual series with no country-specific variation. Its coefficient captures shared macroeconomic cycles, not country-level logistics costs.

**Coffee type:** FAOSTAT QCL item 656 ("Coffee, green") aggregates Arabica and Robusta. Production mix differs by country (e.g. Brazil produces both; Vietnam is predominantly Robusta). Price and demand shocks may affect them differently.

---

## Software

```python
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
import seaborn as sns
import geopandas as gpd
import marimo as mo
```

Full analysis is presented as an interactive Marimo notebook: `marimo/coffee_analysis.py`.
Published to GitHub Pages at: https://warrenrross.github.io/coffee_bean_production_analysis/
