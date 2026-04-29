import marimo

__generated_with = "0.23.2"
app = marimo.App(width="medium", app_title="Grounds for Correlation")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Grounds for Correlation
    ### Do climate, population, and oil price predict coffee bean production and export revenue?

    **INEG 2314H — Statistics for Industrial Engineers | Warren Ross**

    ---

    This notebook walks through a complete exploratory statistical analysis of country-level coffee
    production (1995–2024). Four independent variables are tested against two response variables:

    | Variable | Role | Symbol |
    |---|---|---|
    | Average temperature (°C) | Predictor | X₁ |
    | Average rainfall (mm/yr) | Predictor | X₂ |
    | Annual population | Predictor | X₃ |
    | Brent crude oil price (USD/bbl) | Predictor | X₄ |
    | Coffee production (tonnes) | **Response** | Y₁ |
    | Export revenue (1000 USD) | **Response** | Y₂ |

    **Predictors (X)** are the candidate explanatory variables — the factors we test as potential drivers of coffee output.
    **Responses (Y)** are the outcomes we are trying to explain.
    The notebook asks: does a country's temperature, rainfall, population size, or global oil price help explain how much coffee it produces and earns from exports?

    **Analysis window:** 1995–2024 · **Countries:** ~74 coffee-producing nations (complete cases)

    [View source on GitHub →](https://github.com/warrenrross/coffee_bean_production_analysis)
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 0 · Setup and Data Loading
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    > **Panel data:** This analysis uses a *panel dataset* — one row per country per year,
    > covering 1995–2024. Unlike a single cross-section (one observation per country), panel data
    > has repeated observations for the same countries over time. This matters for interpretation:
    > the regression captures patterns both *across countries* (wetter climates vs. drier ones) and
    > *within countries over time* (years when production rose or fell). It also means observations
    > are not independent — the same country appears in ~30 consecutive rows — which is why we use
    > clustered standard errors in the robustness checks (§4.2).
    """)
    return


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import numpy as np
    import scipy.stats as stats
    import statsmodels.formula.api as smf
    import statsmodels.api as sm
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    import seaborn as sns
    import warnings

    warnings.filterwarnings("ignore")

    # ── Plotting defaults ──────────────────────────────────────────────────────
    plt.rcParams.update({
        "figure.dpi": 130,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
    })
    ACCENT   = "#6F4E37"   # coffee brown
    ACCENT2  = "#2D6A4F"   # forest green
    GREY     = "#9E9E9E"
    return ACCENT, ACCENT2, mo, np, pd, plt, smf, sns, stats


@app.cell
def _(np, pd):
    # ── Load panel ────────────────────────────────────────────────────────────
    # Notebook lives at marimo/coffee_analysis.py
    # Data lives at data/coffee_analysis_panel_with_covariates.csv (relative to repo root)
    import pathlib
    _here = pathlib.Path(__file__).parent          # marimo/
    DATA_PATH = _here.parent / "data" / "coffee_analysis_panel_with_covariates.csv"

    panel_raw = pd.read_csv(DATA_PATH)

    # Rename Brent_Avg → Oil_Price_Brent_USD for clarity throughout the analysis
    panel_raw = panel_raw.rename(columns={"Brent_Avg": "Oil_Price_Brent_USD"})

    # Drop rows missing any of the four predictors or either response
    panel = panel_raw.dropna(subset=[
        "Production_tonnes", "Export_Value_1000USD",
        "Avg_Temp_C", "Rain_mm", "Population", "Oil_Price_Brent_USD"
    ]).copy()

    # Add log-transformed variables used in regression
    panel["ln_Production"]    = np.log(panel["Production_tonnes"])
    panel["ln_Export_Value"]  = np.log(panel["Export_Value_1000USD"])
    panel["ln_Population"]    = np.log(panel["Population"])

    # Rainfall decomposition: country mean (structural) vs within-country deviation
    panel["Rain_mm_country_mean"] = panel.groupby("ISO3")["Rain_mm"].transform("mean")
    panel["Rain_mm_within"]       = panel["Rain_mm"] - panel["Rain_mm_country_mean"]

    print(f"Panel loaded: {len(panel):,} rows · {panel.ISO3.nunique()} countries · "
          f"{panel.Year.min()}–{panel.Year.max()}")
    return (panel,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    > **Complete-case filtering:** Rows missing any of the four predictors or either response variable
    > are dropped before analysis. This complete-case approach simplifies interpretation but means the
    > panel only includes country-years where all variables were observed. Countries or years with
    > incomplete data are excluded entirely, which could affect conclusions if missingness is related
    > to production levels.

    > **Why log-transform? (the mechanism)** A logarithm compresses very large values while
    > spreading out small ones — ln(1,000,000) = 13.8, but ln(1,000) = 6.9. This is useful when
    > a variable spans several orders of magnitude, as coffee production does (from hundreds to
    > millions of tonnes). It also converts *multiplicative* relationships into *additive* ones:
    > if Brazil produces 10× Vietnam's output, ln(Brazil) − ln(Vietnam) = ln(10) ≈ 2.3, a constant
    > gap. Linear regression handles additive relationships better than multiplicative ones.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ## 1 · Exploratory Data Analysis
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### 1.1 Descriptive Statistics

    **Right-skew in plain English:** A distribution is right-skewed when a few very large values
    pull the tail to the right — most observations are smaller, but a handful are much larger.
    Right-skew matters for regression because OLS assumes roughly symmetric residuals; a strongly
    skewed response can produce biased-looking diagnostics even when the model is correctly specified.
    The Skewness column below quantifies this: values above 1 indicate notable right-skew.
    """)
    return


@app.cell
def _(mo, panel, pd):
    _vars = {
        "Production_tonnes":      ("Production (tonnes)",        "Y₁"),
        "Export_Value_1000USD":   ("Export Revenue (1000 USD)",  "Y₂"),
        "Avg_Temp_C":             ("Avg Temperature (°C)",       "X₁"),
        "Rain_mm":                ("Avg Rainfall (mm/yr)",       "X₂"),
        "Population":             ("Population",                 "X₃"),
        "Oil_Price_Brent_USD":    ("Brent Oil Price (USD/bbl)",  "X₄"),
    }

    _rows = []
    for col, (label, role) in _vars.items():
        s = panel[col]
        _rows.append({
            "Variable": label,
            "Role": role,
            "n": len(s.dropna()),
            "Mean": s.mean(),
            "Std Dev": s.std(),
            "Min": s.min(),
            "Median": s.median(),
            "Max": s.max(),
            "Skewness": s.skew(),
        })

    desc = pd.DataFrame(_rows).set_index("Variable")

    # Format nicely
    def _fmt(val, col):
        if col in ("n",):
            return f"{int(val):,}"
        if col == "Skewness":
            return f"{val:.2f}"
        if abs(val) >= 1e6:
            return f"{val:,.0f}"
        if abs(val) >= 1000:
            return f"{val:,.1f}"
        return f"{val:.2f}"

    desc_fmt = desc.copy()
    for c in desc.columns:
        if c != "Role":
            desc_fmt[c] = desc[c].apply(lambda v: _fmt(v, c))

    mo.md(
        f"""
        {mo.as_html(desc_fmt)}

        > **Note on skewness:** Production (skew = {panel['Production_tonnes'].skew():.1f}) and Export Revenue
        > (skew = {panel['Export_Value_1000USD'].skew():.1f}) are strongly right-skewed. Log transformations
        > are applied before regression and correlation analysis. Population (skew = {panel['Population'].skew():.1f})
        > is also log-transformed due to its three-order-of-magnitude range.
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    > **Standard deviation vs. standard error:** The table above reports **Std Dev**, which describes
    > the spread of the raw data — how much individual country-year values vary around the mean.
    > Later regression tables report **Robust SE** (standard error of a coefficient), which describes
    > uncertainty in an *estimate* — how precisely the model has pinned down each β̂.
    > These are different quantities and should not be compared directly.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### 1.2 Distributions — Production and Export Revenue (Raw vs. Log)

    **What a histogram shows:** Each bar counts how many observations fall in a range of values.
    This is a *shape check*, not an inferential test. Look for: Is the distribution symmetric or
    skewed? Are there long tails? Does the log-transformed version look more bell-shaped?
    """)
    return


@app.cell
def _(ACCENT, ACCENT2, mo, panel, plt):
    def _():
        fig_dist, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig_dist.suptitle("Response Variable Distributions: Raw vs. Log-Transformed", fontsize=14, fontweight="bold")

        pairs = [
            (panel["Production_tonnes"],   "Production (tonnes)",        ACCENT,  axes[0, 0]),
            (panel["ln_Production"],       "ln(Production)",             ACCENT,  axes[0, 1]),
            (panel["Export_Value_1000USD"],"Export Revenue (1000 USD)",  ACCENT2, axes[1, 0]),
            (panel["ln_Export_Value"],     "ln(Export Revenue)",         ACCENT2, axes[1, 1]),
        ]

        for data, title, color, ax in pairs:
            ax.hist(data.dropna(), bins=40, color=color, alpha=0.8, edgecolor="white", linewidth=0.4)
            ax.set_title(title)
            ax.set_ylabel("Frequency")
            skew_val = data.skew()
            ax.annotate(f"skew = {skew_val:.2f}", xy=(0.97, 0.93), xycoords="axes fraction",
                        ha="right", fontsize=9, color="#555")

        # Annotate the before/after logic
        for col_idx, label in [(0, "Before log transform →"), (1, "← After log transform")]:
            fig_dist.text(0.27 + col_idx * 0.46, 0.02, label, ha="center", fontsize=9, color="#777", style="italic")

        plt.tight_layout(rect=[0, 0.04, 1, 1])
        return mo.mpl.interactive(fig_dist)


    _()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    > **What this comparison shows:** The raw distributions are right-skewed — a few countries produce
    > vastly more than most. The log-transformed versions are closer to symmetric. This matters because
    > OLS regression performs better when the response variable is roughly symmetric — skewed responses
    > can violate the normality-of-residuals assumption and make linear fits less stable.
    > Log-transforming before regression is a model-building choice, not just a display convenience.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### 1.3 Global Production Time Series (1995–2024)
    """)
    return


@app.cell
def _(ACCENT, mo, panel, plt):
    _global = (
        panel.groupby("Year")["Production_tonnes"]
        .sum()
        .reset_index()
    )
    _global["Production_million_t"] = _global["Production_tonnes"] / 1e6

    fig_ts, ax_ts = plt.subplots(figsize=(11, 4))
    ax_ts.fill_between(_global["Year"], _global["Production_million_t"], alpha=0.18, color=ACCENT)
    ax_ts.plot(_global["Year"], _global["Production_million_t"], color=ACCENT, linewidth=2.2, marker="o", markersize=4)
    ax_ts.set_title("Global Coffee Production (Coffee-Producing Countries in Panel)", pad=10)
    ax_ts.set_xlabel("Year")
    ax_ts.set_ylabel("Production (million tonnes)")
    ax_ts.set_xlim(1994, 2025)
    ax_ts.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.1f}M t"))

    # Annotate peak year
    _peak = _global.loc[_global["Production_million_t"].idxmax()]
    ax_ts.annotate(
        f"Peak: {_peak['Production_million_t']:.1f}M t ({int(_peak['Year'])})",
        xy=(_peak["Year"], _peak["Production_million_t"]),
        xytext=(-40, 12), textcoords="offset points",
        arrowprops=dict(arrowstyle="->", color="#555", lw=1.2),
        fontsize=9, color="#333"
    )

    plt.tight_layout()
    mo.mpl.interactive(fig_ts)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    > **Descriptive, not inferential:** The upward trend in global production is visible in the plot
    > above, but this chart alone does not test whether time causes production to grow. Establishing
    > a significant time coefficient would require including `Year` as a predictor and testing its
    > coefficient — which is done in the year-FE robustness check in §4.2.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### 1.4 Top Producers (2020)
    """)
    return


@app.cell
def _(ACCENT, mo, panel, plt):
    _top = (
        panel[panel["Year"] == 2020]
        .nlargest(12, "Production_tonnes")
        [["Country_Name", "Production_tonnes"]]
        .copy()
    )
    _top["Production_million_t"] = _top["Production_tonnes"] / 1e6

    fig_top, ax_top = plt.subplots(figsize=(10, 4.5))
    bars = ax_top.barh(_top["Country_Name"][::-1], _top["Production_million_t"][::-1],
                       color=ACCENT, alpha=0.85)
    ax_top.set_title("Top 12 Coffee Producers — 2020", pad=10)
    ax_top.set_xlabel("Production (million tonnes)")
    ax_top.bar_label(bars, fmt="%.2f", padding=4, fontsize=9)
    ax_top.set_xlim(0, _top["Production_million_t"].max() * 1.18)
    plt.tight_layout()
    mo.mpl.interactive(fig_top)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### 1.5 Predictor vs. Response Scatter Plots

    *Pearson r is shown as an exploratory summary. Pooled p-values are omitted here — with n ≈ 2,000 panel rows, nearly every r is "significant" under i.i.d. assumptions. See §2 for formal hypothesis tests.*

    **How to read a scatter plot:** look for four things — (1) **direction**: does the cloud slope upward or downward? (2) **tightness**: is the cloud compact or spread out? (3) **curvature**: does the relationship bend rather than follow a straight line? (4) **outliers**: are there points far from the main trend?
    """)
    return


@app.cell
def _(ACCENT, ACCENT2, mo, np, panel, plt, stats):
    _predictors = [
        ("Avg_Temp_C",         "Avg Temperature (°C)",       "X₁"),
        ("Rain_mm",            "Avg Rainfall (mm/yr)",       "X₂"),
        ("ln_Population",      "ln(Population)",             "ln(X₃)"),
        ("Oil_Price_Brent_USD","Oil Price (USD/bbl)",        "X₄"),
    ]
    _responses = [
        ("ln_Production",   "ln(Production, tonnes)",    ACCENT),
        ("ln_Export_Value", "ln(Export Revenue, 1000USD)", ACCENT2),
    ]

    fig_scatter, axes_sc = plt.subplots(4, 2, figsize=(13, 18))
    fig_scatter.suptitle("Predictors vs. Response Variables (Log-Transformed Y)", fontsize=13, fontweight="bold", y=1.002)

    for row_idx, (pred_col, pred_label, pred_sym) in enumerate(_predictors):
        for col_idx, (resp_col, resp_label, color) in enumerate(_responses):
            ax = axes_sc[row_idx, col_idx]
            _d = panel[[pred_col, resp_col]].dropna()
            ax.scatter(_d[pred_col], _d[resp_col], alpha=0.25, s=14, color=color, linewidths=0)

            # OLS trend line
            _m, _b, _r, _p, _ = stats.linregress(_d[pred_col], _d[resp_col])
            _x_line = np.linspace(_d[pred_col].min(), _d[pred_col].max(), 200)
            ax.plot(_x_line, _m * _x_line + _b, color="#333", linewidth=1.5, linestyle="--")

            ax.set_xlabel(f"{pred_sym}: {pred_label}", fontsize=9)
            ax.set_ylabel(resp_label, fontsize=9)
            ax.annotate(f"r = {_r:.3f}", xy=(0.05, 0.93), xycoords="axes fraction",
                        fontsize=9, color="#333")

    plt.tight_layout()
    mo.mpl.interactive(fig_scatter)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ## 2 · Correlation Analysis

    **Pearson r in plain English:** r measures the strength and direction of the *linear* association
    between two variables. r = +1 is a perfect upward line; r = −1 is a perfect downward line;
    r = 0 means no linear pattern — but nonlinear relationships can still exist.
    r does not measure overall relatedness, only linear relatedness.

    For each predictor–response pair, we test the following hypotheses following the
    7-step hypothesis-testing procedure:

    > **H₀:** ρ = 0 (no linear relationship)
    > **H₁:** ρ ≠ 0
    > **Test statistic:** T₀ = r√[(n−2) / (1−r²)],  T₀ ~ t(n−2)
    > **α = 0.05**
    """)
    return


@app.cell
def _(np, panel, pd, stats):
    # ── Run all 8 correlation tests ───────────────────────────────────────────
    _predictors = [
        ("Avg_Temp_C",         "Temperature (X₁)",     "Avg_Temp_C"),
        ("Rain_mm",            "Rainfall (X₂)",        "Rain_mm"),
        ("ln_Population",      "ln(Population) (X₃)",  "ln_Population"),
        ("Oil_Price_Brent_USD","Oil Price (X₄)",       "Oil_Price_Brent_USD"),
    ]
    _responses = [
        ("ln_Production",   "ln(Production) (Y₁)"),
        ("ln_Export_Value", "ln(Export Value) (Y₂)"),
    ]

    _corr_rows = []
    for _pred_col, _pred_label, _ in _predictors:
        for _resp_col, _resp_label in _responses:
            _d = panel[[_pred_col, _resp_col]].dropna()
            _n = len(_d)
            _r, _p = stats.pearsonr(_d[_pred_col], _d[_resp_col])
            _t0 = _r * np.sqrt((_n - 2) / (1 - _r**2))
            _reject = _p < 0.05
            _rs, _ps = stats.spearmanr(_d[_pred_col], _d[_resp_col])
            _reject_s = _ps < 0.05
            _corr_rows.append({
                "Predictor":             _pred_label,
                "Response":              _resp_label,
                "n":                     _n,
                "r":                     _r,
                "T₀":                    _t0,
                "df":                    _n - 2,
                "p-value":               _p,
                "Reject H₀?":            "Yes ✓" if _reject else "No ✗",
                "ρ_s":                   _rs,
                "p (Spearman)":          _ps,
                "Reject H₀? (Spearman)": "Yes ✓" if _reject_s else "No ✗",
                "Conclusion":  (
                    f"Significant {'positive' if _r > 0 else 'negative'} linear relationship (α=0.05)"
                    if _reject else
                    "Insufficient evidence to reject H₀ (α=0.05)"
                ),
            })

    corr_df = pd.DataFrame(_corr_rows)
    return (corr_df,)


@app.cell
def _(corr_df, mo):
    _display = corr_df.copy()
    _display["r"]            = _display["r"].map(lambda x: f"{x:.4f}")
    _display["T₀"]           = _display["T₀"].map(lambda x: f"{x:.3f}")
    _display["p-value"]      = _display["p-value"].map(lambda x: f"{x:.4f}" if x >= 0.0001 else "< 0.0001")
    _display["ρ_s"]          = _display["ρ_s"].map(lambda x: f"{x:.4f}")
    _display["p (Spearman)"] = _display["p (Spearman)"].map(lambda x: f"{x:.4f}" if x >= 0.0001 else "< 0.0001")
    mo.md(
        f"""
        ### 2.1 Pearson Correlation Results (8 tests)

        {mo.as_html(_display[["Predictor","Response","n","r","T₀","df","p-value","Reject H₀?","Conclusion"]])}

        ### 2.1b Spearman Correlation — Rank-Based Cross-Check

        Spearman ρ is rank-based and less sensitive to the fat-tailed residuals visible in the §4 Q-Q plots.
        Consistent results across both tests strengthen each conclusion.

        {mo.as_html(_display[["Predictor","Response","n","ρ_s","p (Spearman)","Reject H₀? (Spearman)"]])}
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    #### Teacher-phrasing template for correlation conclusions

    When writing conclusions about correlation tests, use this sentence pattern:

    > *"p-value = X < α = 0.05. We reject H₀: ρ = 0. There is sufficient evidence of a significant
    > [positive/negative] linear relationship between [predictor] and [response] (r = X)."*

    If the test fails to reject:

    > *"p-value = X > α = 0.05. We fail to reject H₀: ρ = 0. There is insufficient evidence to
    > conclude that a linear relationship exists between [predictor] and [response]."*

    Use "fail to reject" — never "accept H₀" or "prove no relationship exists."

    ---

    #### Correlation matrix as a map

    The heatmap below shows every pairwise Pearson r in the dataset at a glance. It is useful for
    spotting broad patterns — for example, whether predictors are strongly correlated with each other
    (multicollinearity) or with the responses.

    **What the heatmap cannot tell you:** how much each predictor contributes while the others are
    held fixed. That question requires regression (§3). Use the heatmap as orientation, not conclusion.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### 2.2 Correlation Heatmap
    """)
    return


@app.cell
def _(mo, panel, plt, sns):
    _cols = {
        "Avg_Temp_C":          "Temp (X₁)",
        "Rain_mm":             "Rainfall (X₂)",
        "ln_Population":       "ln(Pop) (X₃)",
        "Oil_Price_Brent_USD": "Oil Price (X₄)",
        "ln_Production":       "ln(Prod) (Y₁)",
        "ln_Export_Value":     "ln(Export) (Y₂)",
    }
    _data = panel[list(_cols.keys())].rename(columns=_cols).dropna()
    _corr_mat = _data.corr()

    fig_heat, ax_heat = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        _corr_mat, annot=True, fmt=".3f", cmap="RdBu_r",
        center=0, vmin=-1, vmax=1,
        linewidths=0.5, ax=ax_heat,
        annot_kws={"size": 10}
    )
    ax_heat.set_title("Pearson Correlation Matrix — Predictors and Responses", pad=12)
    plt.tight_layout()
    mo.mpl.interactive(fig_heat)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## 3 · Multiple Linear Regression

    Two models are fit with five predictor terms. Rainfall is split into two components:
    $\overline{\text{Rain}}_{\text{country}}$ = each country's long-run mean (structural climate);
    $\text{Rain}_{\text{within}}$ = each year's deviation from that mean (interannual variation).

    **Model A — Production:**
    $$\ln(\text{Production}) = \beta_0 + \beta_1\,\text{Temp} + \beta_{2a}\,\overline{\text{Rain}}_{\text{country}} + \beta_{2b}\,\text{Rain}_{\text{within}} + \beta_3\,\ln(\text{Population}) + \beta_4\,\text{Oil} + \varepsilon$$

    **Model B — Export Revenue:**
    $$\ln(\text{Export\_Value}) = \beta_0 + \beta_1\,\text{Temp} + \beta_{2a}\,\overline{\text{Rain}}_{\text{country}} + \beta_{2b}\,\text{Rain}_{\text{within}} + \beta_3\,\ln(\text{Population}) + \beta_4\,\text{Oil} + \varepsilon$$

    **Overall F-test H₀:** β₁ = β₂ₐ = β₂ᵦ = β₃ = β₄ = 0 (model has no explanatory power)
    **Individual t-tests H₀:** βⱼ = 0 for each predictor term
    **α = 0.05**
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    #### What MLR adds beyond correlation

    Correlation (§2) measures pairwise association between one predictor and one response.
    Multiple linear regression fits all four predictors simultaneously, so each coefficient is
    interpreted as *holding all other predictors constant*. For example: the temperature coefficient
    β₁ estimates the association between temperature and production **after accounting for differences
    in population, rainfall, and oil price**. This is what separates regression from a collection
    of bivariate correlations.

    ---

    #### Why rainfall is split into two terms

    Raw `Rain_mm` confounds two different questions. The decomposition separates them:

    - **Rain_mm_country_mean (β₂ₐ):** Each country's long-run average rainfall. Answers: *Do wetter
      climates structurally produce more coffee?* This is a cross-country comparison.
    - **Rain_mm_within (β₂ᵦ):** Each year's deviation from that country's mean. Answers: *Does an
      unusually wet year boost production?* This is within-country variation over time.

    The two coefficients answer different questions and should not be interpreted interchangeably.

    ---

    #### Reading the regression output

    **R² and adjusted R²** both measure variation explained. Adjusted R² penalizes adding predictors
    and is reported here because it allows fair comparison across models.
    Teacher phrasing: *"X% of the variation in [response] is explained by the regression model."*

    **Coefficient table column guide:**

    | Column | Meaning |
    |---|---|
    | β̂ (coef) | Estimated change in ln(Y) per one-unit increase in X, holding all other predictors constant |
    | Robust SE | Standard error of β̂ under HC3 correction — measures estimation uncertainty |
    | Robust t₀ | t-statistic = β̂ / Robust SE — how many SEs the estimate is from zero |
    | p-value | Probability of observing this t₀ if H₀: βⱼ = 0 were true — compare to α = 0.05 |
    | Robust 95% CI | Plausible range for the true coefficient |
    | Sig? | "Yes ✓" if p-value < 0.05 |
    """)
    return


@app.cell
def _(mo, panel, pd, smf):
    # ── Fit both models (HC3 robust standard errors) ──────────────────────────
    FORMULA_A = (
        "ln_Production  ~ Avg_Temp_C + Rain_mm_country_mean + Rain_mm_within"
        " + ln_Population + Oil_Price_Brent_USD"
    )
    FORMULA_B = (
        "ln_Export_Value ~ Avg_Temp_C + Rain_mm_country_mean + Rain_mm_within"
        " + ln_Population + Oil_Price_Brent_USD"
    )

    panel_model = panel.dropna(subset=[
        "ln_Production", "ln_Export_Value",
        "Avg_Temp_C", "Rain_mm_country_mean", "Rain_mm_within",
        "ln_Population", "Oil_Price_Brent_USD"
    ])

    # Raw OLS (retained for influence diagnostics — OLSInfluence requires plain OLS)
    ols_a = smf.ols(FORMULA_A, data=panel_model).fit()
    ols_b = smf.ols(FORMULA_B, data=panel_model).fit()

    # HC3 heteroskedasticity-consistent fits — primary inference
    model_a = smf.ols(FORMULA_A, data=panel_model).fit(cov_type="HC3")
    model_b = smf.ols(FORMULA_B, data=panel_model).fit(cov_type="HC3")

    def _model_summary_table(result, model_name):
        coef_df = pd.DataFrame({
            "Term":             result.params.index,
            "β̂ (coef)":        result.params.values,
            "Robust SE":        result.bse.values,
            "Robust t₀":       result.tvalues.values,
            "p-value":          result.pvalues.values,
            "Robust 95% CI Lo": result.conf_int()[0].values,
            "Robust 95% CI Hi": result.conf_int()[1].values,
        })
        coef_df["Sig?"] = coef_df["p-value"].apply(lambda p: "Yes ✓" if p < 0.05 else "No ✗")
        for c in ["β̂ (coef)", "Robust SE", "Robust t₀", "Robust 95% CI Lo", "Robust 95% CI Hi"]:
            coef_df[c] = coef_df[c].map(lambda x: f"{x:.4f}")
        coef_df["p-value"] = coef_df["p-value"].map(lambda x: f"{x:.4f}" if x >= 0.0001 else "< 0.0001")
        return coef_df

    coef_a = _model_summary_table(model_a, "Model A")
    coef_b = _model_summary_table(model_b, "Model B")

    # F-test summary (R² and F come from base OLS; HC3 affects SE/t/p only)
    _f_rows = []
    for _name, _res in [("Model A — ln(Production)", model_a), ("Model B — ln(Export Revenue)", model_b)]:
        _f_rows.append({
            "Model":      _name,
            "n":          int(_res.nobs),
            "R²":         f"{_res.rsquared:.4f}",
            "R²_adj":     f"{_res.rsquared_adj:.4f}",
            "F₀":         f"{_res.fvalue:.3f}",
            "df (reg)":   int(_res.df_model),
            "df (error)": int(_res.df_resid),
            "p(F)":       "< 0.0001" if _res.f_pvalue < 0.0001 else f"{_res.f_pvalue:.4f}",
            "Reject H₀?": "Yes ✓" if _res.f_pvalue < 0.05 else "No ✗",
        })
    f_df = pd.DataFrame(_f_rows)

    mo.md(
        f"""
        ### 3.1 Overall Model Significance (F-test)

        {mo.as_html(f_df)}

        ---

        ### 3.2 Model A — Coefficients: ln(Production)
        *Standard errors and CIs are HC3 heteroskedasticity-consistent.*

        {mo.as_html(coef_a)}

        ---

        ### 3.3 Model B — Coefficients: ln(Export Revenue)
        *Standard errors and CIs are HC3 heteroskedasticity-consistent.*

        {mo.as_html(coef_b)}
        """
    )
    return model_a, model_b, ols_a, ols_b, panel_model


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    #### Confidence interval intuition

    Each bar in the coefficient plot shows the estimated effect of one predictor with a 95%
    confidence interval. A 95% CI gives a plausible range for the true coefficient: if we repeated
    this study many times with new samples, about 95% of those intervals would contain the true βⱼ.

    **Key link to significance:** A CI that crosses zero means zero is a plausible value for the
    coefficient — consistent with failing to reject H₀: βⱼ = 0 at α = 0.05.
    Bars shown in **gray** cross zero and are not significant; **colored** bars do not cross zero
    and are significant.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### 3.4 Coefficient Plot — Effect Sizes and 95% CIs
    """)
    return


@app.cell
def _(ACCENT, ACCENT2, mo, model_a, model_b, np, plt):
    def _():
        _terms = ["Avg_Temp_C", "Rain_mm_country_mean", "Rain_mm_within", "ln_Population", "Oil_Price_Brent_USD"]
        _labels = ["Temp (X₁)", "Rainfall-between (X₂ₐ)", "Rainfall-within (X₂ᵦ)", "ln(Pop) (X₃)", "Oil Price (X₄)"]

        fig_coef, axes_coef = plt.subplots(1, 2, figsize=(13, 4), sharey=True)
        fig_coef.suptitle("Regression Coefficients with 95% Confidence Intervals", fontsize=13, fontweight="bold")

        for ax, result, title, color in [
            (axes_coef[0], model_a, "Model A — ln(Production)", ACCENT),
            (axes_coef[1], model_b, "Model B — ln(Export Revenue)", ACCENT2),
        ]:
            _coefs  = [result.params[t]         for t in _terms]
            _lo     = [result.conf_int().loc[t, 0] for t in _terms]
            _hi     = [result.conf_int().loc[t, 1] for t in _terms]
            _errs   = [[c - lo for c, lo in zip(_coefs, _lo)],
                       [hi - c for c, hi in zip(_coefs, _hi)]]
            _pvals  = [result.pvalues[t] for t in _terms]

            _y = np.arange(len(_terms))
            _colors = [color if p < 0.05 else "#BDBDBD" for p in _pvals]

            ax.axvline(0, color="#888", linewidth=1, linestyle="--")
            ax.barh(_y, _coefs, xerr=_errs, color=_colors, alpha=0.85,
                    height=0.5, error_kw=dict(ecolor="#333", capsize=4, linewidth=1.3))
            ax.set_yticks(_y)
            ax.set_yticklabels(_labels)
            ax.set_xlabel("Coefficient value")
            ax.set_title(title)
            ax.annotate("Grey = not significant (α=0.05)", xy=(0.98, 0.02), xycoords="axes fraction",
                        ha="right", fontsize=8, color="#888")

        plt.tight_layout()
        return mo.mpl.interactive(fig_coef)


    _()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## 4 · Model Adequacy Checks

    A **residual** is the actual observed value minus the model's predicted value: eᵢ = yᵢ − ŷᵢ. Residual plots reveal whether the model's assumptions hold in practice.

    > A visible pattern in residual plots is more concerning than a high R² — R² can look good even when regression assumptions are violated.

    For both models, we verify the four OLS regression assumptions:

    1. **Linearity** — Residuals vs. Fitted: no systematic curve
    2. **Heteroskedasticity** — mitigated by HC3 robust SEs; within-country serial correlation addressed in robustness section (§4.2)
    3. **Homoscedasticity** — Scale-location plot; residual spread vs. fitted
    4. **Normality of residuals** — Normal Q-Q plot; Shapiro-Wilk test
    """)
    return


@app.cell
def _(ACCENT, ACCENT2, mo, model_a, model_b, np, plt, stats):
    def _():
        fig_diag, axes_diag = plt.subplots(2, 4, figsize=(17, 8))
        fig_diag.suptitle("Model Adequacy Diagnostics", fontsize=13, fontweight="bold")

        for row_idx, (result, title, color) in enumerate([
            (model_a, "Model A — ln(Production)",    ACCENT),
            (model_b, "Model B — ln(Export Revenue)", ACCENT2),
        ]):
            residuals = result.resid
            fitted    = result.fittedvalues
            std_resid = residuals / residuals.std()

            # ── Plot 1: Residuals vs Fitted ──────────────────────────────────────
            ax = axes_diag[row_idx, 0]
            ax.scatter(fitted, residuals, alpha=0.25, s=10, color=color, linewidths=0)
            ax.axhline(0, color="#333", linewidth=1.2, linestyle="--")
            ax.set_xlabel("Fitted values")
            ax.set_ylabel("Residuals")
            ax.set_title(f"{title}\nResiduals vs. Fitted")

            # ── Plot 2: Normal Q-Q ───────────────────────────────────────────────
            ax = axes_diag[row_idx, 1]
            _osm, _osr = stats.probplot(residuals, dist="norm")
            ax.scatter(_osm[0], _osm[1], alpha=0.3, s=10, color=color, linewidths=0)
            _fit_line = np.polyfit(_osm[0], _osm[1], 1)
            _x_ql = np.linspace(min(_osm[0]), max(_osm[0]), 200)
            ax.plot(_x_ql, np.polyval(_fit_line, _x_ql), color="#333", linewidth=1.5, linestyle="--")
            ax.set_xlabel("Theoretical quantiles")
            ax.set_ylabel("Sample quantiles")
            ax.set_title(f"{title}\nNormal Q-Q Plot")

            # ── Plot 3: Scale-Location (√|std resid| vs fitted) ─────────────────
            ax = axes_diag[row_idx, 2]
            ax.scatter(fitted, np.sqrt(np.abs(std_resid)), alpha=0.25, s=10, color=color, linewidths=0)
            ax.axhline(1, color="#333", linewidth=1, linestyle="--")
            ax.set_xlabel("Fitted values")
            ax.set_ylabel("√|Standardized residuals|")
            ax.set_title(f"{title}\nScale-Location")

            # ── Plot 4: Residual histogram ───────────────────────────────────────
            ax = axes_diag[row_idx, 3]
            ax.hist(residuals, bins=35, color=color, alpha=0.8, edgecolor="white", linewidth=0.4)
            _sw_stat, _sw_p = stats.shapiro(residuals)
            ax.set_title(f"{title}\nResidual Distribution")
            ax.set_xlabel("Residual")
            ax.set_ylabel("Frequency")
            ax.annotate(
                f"Shapiro-Wilk\nW = {_sw_stat:.4f}\np = {'< 0.0001' if _sw_p < 0.0001 else f'{_sw_p:.4f}'}",
                xy=(0.97, 0.93), xycoords="axes fraction", ha="right", va="top", fontsize=8, color="#333",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7)
            )

        plt.tight_layout()
        return mo.mpl.interactive(fig_diag)


    _()
    return


@app.cell(hide_code=True)
def _(mo, model_a, model_b, stats):
    # ── Shapiro-Wilk formal results table ─────────────────────────────────────
    _results = []
    for _name, _res in [("Model A — ln(Production)", model_a), ("Model B — ln(Export Revenue)", model_b)]:
        _resid = _res.resid.values
        _w, _p = stats.shapiro(_resid)
        _results.append({
            "Model": _name,
            "n (residuals)": len(_resid),
            "Shapiro-Wilk W": f"{_w:.4f}",
            "p-value": "< 0.0001" if _p < 0.0001 else f"{_p:.4f}",
            "Reject normality (α=0.05)?": "Yes" if _p < 0.05 else "No",
            "Interpretation": (
                "Residuals depart significantly from normality. With n > 1,000, "
                "Shapiro-Wilk is highly sensitive to small departures. "
                "Inspect Q-Q plot for practical significance."
            ) if _p < 0.05 else (
                "No significant departure from normality detected."
            )
        })

    import pandas as _pd2
    _sw_df = _pd2.DataFrame(_results)

    mo.md(
        f"""
        ### 4.1 Shapiro-Wilk Normality Test Results

        {mo.as_html(_sw_df)}

        > **Note on sample size:** With n ≈ 2,000 observations, the Shapiro-Wilk test has very high
        > statistical power and will flag even minor, practically irrelevant deviations from normality.
        > The Q-Q plots above are the more informative diagnostic at this sample size.
        > If residuals follow approximately a straight line on the Q-Q plot, the normality assumption
        > is reasonably satisfied for inference purposes.
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ### 4.2 Robustness — Standard Error Strategies
    """)
    return


@app.cell
def _(mo, model_a, model_b, ols_a, ols_b, panel_model, pd, smf):
    # Compare OLS / HC3 / clustered-ISO3 / year-FE+clustered p-values per predictor
    _FORMULA_A_YFE = (
        "ln_Production  ~ Avg_Temp_C + Rain_mm_country_mean + Rain_mm_within"
        " + ln_Population + Oil_Price_Brent_USD + C(Year)"
    )
    _FORMULA_B_YFE = (
        "ln_Export_Value ~ Avg_Temp_C + Rain_mm_country_mean + Rain_mm_within"
        " + ln_Population + Oil_Price_Brent_USD + C(Year)"
    )
    _yfe_a_raw = smf.ols(_FORMULA_A_YFE, data=panel_model).fit()
    _yfe_b_raw = smf.ols(_FORMULA_B_YFE, data=panel_model).fit()

    _clust_a     = ols_a.get_robustcov_results(cov_type="cluster", groups=panel_model["ISO3"])
    _clust_b     = ols_b.get_robustcov_results(cov_type="cluster", groups=panel_model["ISO3"])
    _yfe_clust_a = _yfe_a_raw.get_robustcov_results(cov_type="cluster", groups=panel_model["ISO3"])
    _yfe_clust_b = _yfe_b_raw.get_robustcov_results(cov_type="cluster", groups=panel_model["ISO3"])

    _terms  = ["Avg_Temp_C", "Rain_mm_country_mean", "Rain_mm_within", "ln_Population", "Oil_Price_Brent_USD"]
    _labels = ["Temp (X₁)", "Rainfall-between (X₂ₐ)", "Rainfall-within (X₂ᵦ)", "ln(Pop) (X₃)", "Oil Price (X₄)"]

    def _rob_table(results, terms, labels):
        rows = []
        for t, lbl in zip(terms, labels):
            row = {"Term": lbl}
            for spec, res in results:
                _pvals = pd.Series(res.pvalues, index=res.model.exog_names)
                if t in _pvals.index:
                    p = _pvals[t]
                    sig = " ✓" if p < 0.05 else " ✗"
                    row[spec] = ("< 0.0001" if p < 0.0001 else f"{p:.4f}") + sig
                else:
                    row[spec] = "—"
            rows.append(row)
        return pd.DataFrame(rows)

    _rob_a = _rob_table(
        [("OLS", ols_a), ("HC3", model_a), ("Clustered", _clust_a), ("YFE+Clustered", _yfe_clust_a)],
        _terms, _labels,
    )
    _rob_b = _rob_table(
        [("OLS", ols_b), ("HC3", model_b), ("Clustered", _clust_b), ("YFE+Clustered", _yfe_clust_b)],
        _terms, _labels,
    )

    mo.md(f"""
    #### Model A — ln(Production): p-values across specifications

    {mo.as_html(_rob_a)}

    #### Model B — ln(Export Revenue): p-values across specifications

    {mo.as_html(_rob_b)}

    > **Oil price (X₄):** A single global annual series with no country-level variation. In the
    > Year FE + Clustered specification, year dummies absorb all shared time movements, making
    > the oil term weakly identified. Its coefficient in that column is a macro-time residual,
    > not a country-level logistics effect — interpret cautiously.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### 4.3 Influence Diagnostics — Leverage, Cook's Distance, Studentized Residuals
    """)
    return


@app.cell
def _(mo, ols_a, ols_b, panel_model, pd):
    import pycountry
    from statsmodels.stats.outliers_influence import OLSInfluence

    def _iso3_to_name(code):
        try:
            return pycountry.countries.get(alpha_3=code).name
        except AttributeError:
            return code

    def _build_diag(ols_result, panel_df):
        infl = OLSInfluence(ols_result)
        n = int(ols_result.nobs)
        p = int(ols_result.df_model) + 1
        df = pd.DataFrame({
            "Country":  [_iso3_to_name(c) for c in panel_df["ISO3"].values],
            "Year":     panel_df["Year"].values,
            "rstudent": infl.resid_studentized_external,
            "leverage": infl.hat_matrix_diag,
            "cooks_d":  infl.cooks_distance[0],
        })
        df["high_leverage"] = df["leverage"] > 2 * p / n
        df["outlier"]       = df["rstudent"].abs() > 3
        df["influential"]   = df["cooks_d"] > 0.5
        return df, n, p

    diag_a, _n_a, _p_a = _build_diag(ols_a, panel_model)
    diag_b, _n_b, _p_b = _build_diag(ols_b, panel_model)

    def _top10(df, label):
        _t = df.nlargest(10, "cooks_d")[
            ["Country", "Year", "rstudent", "leverage", "cooks_d", "high_leverage", "outlier", "influential"]
        ].copy()
        for c in ["rstudent", "leverage", "cooks_d"]:
            _t[c] = _t[c].map(lambda x: f"{x:.4f}")
        _t.insert(0, "Model", label)
        return _t

    _top_df = pd.concat([_top10(diag_a, "A"), _top10(diag_b, "B")], ignore_index=True)

    mo.md(f"""
    #### Top 10 influential observations by Cook's D

    {mo.as_html(_top_df)}

    > Thresholds: leverage > 2p/n ({2*_p_a/_n_a:.4f} for A, {2*_p_b/_n_b:.4f} for B);
    > outlier = |rstudent| > 3; influential = Cook's D > 0.5.
    """)
    return diag_a, diag_b


@app.cell
def _(ACCENT, ACCENT2, diag_a, diag_b, mo, ols_a, ols_b, plt):
    def _():
        fig_inf, axes_inf = plt.subplots(1, 2, figsize=(14, 4))
        fig_inf.suptitle("Cook's Distance — Influence Diagnostics", fontsize=13, fontweight="bold")

        for ax, diag, color, label, n in [
            (axes_inf[0], diag_a, ACCENT,  "Model A — ln(Production)",    int(ols_a.nobs)),
            (axes_inf[1], diag_b, ACCENT2, "Model B — ln(Export Revenue)", int(ols_b.nobs)),
        ]:
            ax.bar(range(len(diag)), diag["cooks_d"], color=color, alpha=0.5, width=1.0, linewidth=0)
            ax.axhline(0.5,   color="red",    linewidth=1.2, linestyle="--", label="D = 0.5")
            ax.axhline(4 / n, color="orange", linewidth=1.0, linestyle="--", label=f"4/n = {4/n:.4f}")
            ax.set_title(label)
            ax.set_xlabel("Observation index")
            ax.set_ylabel("Cook's D")
            ax.legend(fontsize=8)

        plt.tight_layout()
        return mo.mpl.interactive(fig_inf)

    _()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## 5 · Conclusions

    ### 5.1 Correlation Analysis Summary

    For each of the 8 Pearson correlation tests at **α = 0.05**:
    """)
    return


@app.cell
def _(corr_df, mo, pd):
    # Build a plain-English conclusion table
    _conclusions = []
    for _, row in corr_df.iterrows():
        r = float(row["r"])
        p = float(row["p-value"])
        reject = p < 0.05
        direction = "positive" if r > 0 else "negative"
        strength = "weak" if abs(r) < 0.2 else ("moderate" if abs(r) < 0.5 else "strong")

        if reject:
            text = (f"Reject H₀. Statistically significant {direction} linear relationship "
                    f"(r = {r:.3f}, {strength}). At α = 0.05, there is sufficient evidence "
                    f"that ρ ≠ 0.")
        else:
            text = (f"Fail to reject H₀. Insufficient evidence of a linear relationship "
                    f"(r = {r:.3f}, p = {p:.3f}). Cannot conclude ρ ≠ 0 at α = 0.05.")

        _conclusions.append({
            "Pair": f"{row['Predictor']} → {row['Response']}",
            "r": f"{r:.4f}",
            "p-value": "< 0.0001" if p < 0.0001 else f"{p:.4f}",
            "Conclusion": text,
        })

    _conc_df = pd.DataFrame(_conclusions)
    mo.md(f"""
    #### Plain-English Conclusions

    {mo.as_html(_conc_df)}
    """)
    return


@app.cell(hide_code=True)
def _(mo, model_a, model_b):
    # Regression conclusion text
    _all_terms = ["Avg_Temp_C", "Rain_mm_country_mean", "Rain_mm_within", "ln_Population", "Oil_Price_Brent_USD"]
    _a_sig = [t for t in _all_terms if model_a.pvalues[t] < 0.05]
    _b_sig = [t for t in _all_terms if model_b.pvalues[t] < 0.05]

    _name_map = {
        "Avg_Temp_C":           "Temperature",
        "Rain_mm_country_mean": "Rainfall-between",
        "Rain_mm_within":       "Rainfall-within",
        "ln_Population":        "ln(Population)",
        "Oil_Price_Brent_USD":  "Oil Price",
    }

    def _p_str(p):
        return "< 0.0001" if p < 0.0001 else f"= {p:.4f}"

    def _predictor_phrasings(sig_terms, model, response_label):
        if not sig_terms:
            return "- No individually significant predictors at α = 0.05."
        lines = []
        for t in sig_terms:
            p = model.pvalues[t]
            lines.append(
                f"- **{_name_map[t]}:** p-value {_p_str(p)} < α = 0.05. "
                f"We reject H₀: β = 0. There is sufficient evidence that "
                f"{_name_map[t]} is a significant predictor of {response_label}."
            )
        return "\n".join(lines)

    _a_fp = _p_str(model_a.f_pvalue)
    _b_fp = _p_str(model_b.f_pvalue)

    mo.md(
        f"""
        ### 5.2 Regression Summary

        **Model A — ln(Production):** R² = {model_a.rsquared:.4f}, Adj. R² = {model_a.rsquared_adj:.4f}

        Overall F-test: F₀ = {model_a.fvalue:.2f}, p-value {_a_fp} < α = 0.05.
        We reject H₀: β₁ = β₂ = β₃ = β₄ = 0. There is sufficient evidence that the model has statistically significant explanatory power.
        **{model_a.rsquared_adj * 100:.1f}% of the variation in ln(Production) is explained by the regression model** (adj. R²).

        Individually significant predictors (α = 0.05):

        {_predictor_phrasings(_a_sig, model_a, "ln(Production)")}

        ---

        **Model B — ln(Export Revenue):** R² = {model_b.rsquared:.4f}, Adj. R² = {model_b.rsquared_adj:.4f}

        Overall F-test: F₀ = {model_b.fvalue:.2f}, p-value {_b_fp} < α = 0.05.
        We reject H₀: β₁ = β₂ = β₃ = β₄ = 0. There is sufficient evidence that the model has statistically significant explanatory power.
        **{model_b.rsquared_adj * 100:.1f}% of the variation in ln(Export Revenue) is explained by the regression model** (adj. R²).

        Individually significant predictors (α = 0.05):

        {_predictor_phrasings(_b_sig, model_b, "ln(Export Revenue)")}

        ---

        ### 5.3 Limitations

        1. **Rainfall is largely structural:** 82.5% of country-year rows carry a fixed climatological
           mean for rainfall — the value does not vary year to year. Rainfall reflects cross-country
           differences in climate zone rather than year-to-year variation. Its coefficient should be
           interpreted as a structural climate effect, not a dynamic one.

        2. **Omitted variables:** Altitude, soil type, variety (Arabica vs. Robusta), political
           stability, and agricultural subsidies are all known drivers of production that are not
           included in this model.

        3. **Correlation ≠ causation:** This is a cross-sectional panel analysis. Statistically
           significant correlations document co-variation across countries and years but do not
           establish causal mechanisms.

        4. **Oil price is global:** A single annual Brent price is assigned to all countries. This
           cannot capture country-specific exposure to fuel and fertilizer costs.

        5. **Panel is unbalanced:** Not every country appears in every year. This could introduce
           selection effects if data availability is correlated with production levels.
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ## Data Sources

    | Source | Description | Coverage |
    |---|---|---|
    | [FAOSTAT QCL](https://www.fao.org/faostat/en/#data/QCL) | Coffee production (tonnes), item 656 "Coffee, green" | 1961–2024 |
    | [BACI/CEPII](https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37) | Harmonized bilateral coffee trade flows | 1995–2024 |
    | [Berkeley Earth](https://berkeleyearth.org) / [ERA5](https://www.ecmwf.int) | Country annual avg temperature (°C) | 1995–2024 |
    | [World Bank / ERA5-Land](https://data.worldbank.org) | Country annual avg rainfall (mm/yr) | 1995–2024 |
    | [World Bank](https://data.worldbank.org/indicator/SP.POP.TOTL) | Annual population | 1995–2024 |
    | Various (Brent crude) | Annual avg oil price (USD/bbl) | 1995–2024 |

    Full column-level documentation: [`data/coffee_analysis_panel_with_covariates_data_dictionary.md`](../data/coffee_analysis_panel_with_covariates_data_dictionary.md)

    ---
    *INEG 2314H — Statistics for Industrial Engineers · Warren Ross · 2026*
    """)
    return


if __name__ == "__main__":
    app.run()
