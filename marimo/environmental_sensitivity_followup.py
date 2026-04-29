import marimo

__generated_with = "0.23.2"
app = marimo.App(
    width="medium",
    app_title="Environmental Sensitivity Follow-Up",
)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Environmental Sensitivity Follow-Up
    ### Which coffee-producing countries still show environmental signal after population is accounted for?

    **INEG 2314H — Statistics for Industrial Engineers | Warren Ross**

    ---

    The first workbook showed that `ln(Population)` is a major predictor of coffee production. This follow-up asks a more targeted question:

    > After removing the population/scale effect, which countries still show production variation associated with temperature or rainfall?

    This notebook is an exploratory screening tool. It identifies candidate countries for deeper environmental case-study analysis; it does not prove climate causation.
    """)
    return


@app.cell
def _():
    import pathlib
    import warnings

    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import scipy.stats as stats
    import seaborn as sns
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    warnings.filterwarnings("ignore")

    plt.rcParams.update({
        "figure.dpi": 130,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 10.5,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
    })

    ACCENT = "#6F4E37"
    ACCENT2 = "#2D6A4F"
    ACCENT3 = "#C46A32"
    GREY = "#8A8A8A"
    return (
        ACCENT,
        ACCENT2,
        ACCENT3,
        GREY,
        mo,
        np,
        pathlib,
        pd,
        plt,
        sm,
        smf,
        stats,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 0. Data Loading and Derived Variables

    This notebook uses the same analysis-ready country-year panel as the main workbook. The unit of observation is one country in one year.
    """)
    return


@app.cell
def _(np, pathlib, pd):
    _here = pathlib.Path(__file__).parent
    DATA_PATH = _here.parent / "data" / "coffee_analysis_panel_with_covariates.csv"

    panel_raw = pd.read_csv(DATA_PATH).rename(columns={"Brent_Avg": "Oil_Price_Brent_USD"})

    panel = panel_raw.dropna(subset=[
        "ISO3",
        "Country_Name",
        "Year",
        "Production_tonnes",
        "Avg_Temp_C",
        "Rain_mm",
        "Population",
        "Oil_Price_Brent_USD",
    ]).copy()

    panel = panel[(panel["Production_tonnes"] > 0) & (panel["Population"] > 0)].copy()

    panel["ln_Production"] = np.log(panel["Production_tonnes"])
    panel["ln_Population"] = np.log(panel["Population"])

    if "Export_Value_1000USD" in panel.columns:
        panel["ln_Export_Value"] = np.where(
            panel["Export_Value_1000USD"] > 0,
            np.log(panel["Export_Value_1000USD"]),
            np.nan,
        )

    panel["Rain_mm_country_mean"] = panel.groupby("ISO3")["Rain_mm"].transform("mean")
    panel["Rain_mm_within"] = panel["Rain_mm"] - panel["Rain_mm_country_mean"]

    print(
        f"Loaded {len(panel):,} complete production rows across "
        f"{panel['ISO3'].nunique()} countries from {panel['Year'].min()}-{panel['Year'].max()}."
    )
    return (panel,)


@app.cell
def _(mo, panel, pd):
    _summary = pd.DataFrame({
        "Metric": [
            "Rows used for production follow-up",
            "Countries",
            "Years",
            "Countries with >= 15 observations",
            "Countries with time-varying rainfall",
        ],
        "Value": [
            f"{len(panel):,}",
            f"{panel['ISO3'].nunique():,}",
            f"{panel['Year'].min()}-{panel['Year'].max()}",
            f"{(panel.groupby('ISO3').size() >= 15).sum():,}",
            f"{(panel.groupby('ISO3')['Rain_mm'].nunique() >= 5).sum():,}",
        ],
    })

    mo.md(f"""
    ### Dataset Snapshot

    {mo.as_html(_summary)}

    > **Rainfall caution:** Rainfall only works as a within-country annual signal when `Rain_mm` changes over time. For countries with one repeated rainfall value, rainfall is a structural climate descriptor, not an annual weather variable.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## 1. Screening Logic

    The follow-up uses a two-step idea:

    1. Fit a population-only model within each country:

       $$\ln(Production) = \beta_0 + \beta_1\ln(Population) + \varepsilon$$

    2. Correlate the residuals from that model with environmental variables.

    A residual is:

    $$e_i = y_i - \hat{y}_i$$

    In context, it means: actual log production minus the log production expected from population alone.

    > **Screening vs. formal testing.** This approach partials the *response* against ln(Population) but does not partial the environmental predictor. The reported r is therefore a screening signal (an FWL-style partial-residual correlation), not a formal partial correlation. For formal H₀/H₁ inference see the main workbook §2–§5. The standardized-β columns in the ranking table below come from a full multivariate fit per country and are the more reliable effect-size measure.
    """)
    return


@app.cell
def _(np, panel, pd, sm, stats):
    MIN_OBS = 15
    MIN_UNIQUE = 5

    # Heuristic screening thresholds — NOT formal hypothesis tests.
    # Used to assign candidate tiers for case-study selection only.
    TIER_STRONG_R   = 0.45   # |r| between env var and pop-adjusted residual
    TIER_STRONG_DR2 = 0.10   # env vars must add ≥10pp R² beyond population
    TIER_MOD_R      = 0.35   # |r| threshold for Moderate tier
    TIER_MOD_P      = 0.10   # p-value threshold for Moderate tier

    def _fit_r2(y, x_df):
        _d = pd.concat([y, x_df], axis=1).dropna()
        if len(_d) < x_df.shape[1] + 5:
            return np.nan
        _y = _d.iloc[:, 0]
        _x = sm.add_constant(_d.iloc[:, 1:], has_constant="add")
        try:
            return sm.OLS(_y, _x).fit().rsquared
        except Exception:
            return np.nan

    def _standardized_fit(group_df, predictors):
        _cols = ["ln_Production"] + predictors
        _d = group_df[_cols].dropna().copy()
        if len(_d) < len(predictors) + 5:
            return None
        _std = _d.std(ddof=0)
        if (_std == 0).any():
            return None
        _z = (_d - _d.mean()) / _std
        _x = sm.add_constant(_z[predictors], has_constant="add")
        try:
            return sm.OLS(_z["ln_Production"], _x).fit()
        except Exception:
            return None

    country_rows = []
    residual_frames = []

    for _iso3, _g in panel.groupby("ISO3"):
        _g = _g.sort_values("Year").copy()

        if len(_g) < MIN_OBS or _g["ln_Population"].nunique() < MIN_UNIQUE:
            continue

        _pop_x = sm.add_constant(_g[["ln_Population"]], has_constant="add")
        try:
            _pop_fit = sm.OLS(_g["ln_Production"], _pop_x).fit()
        except Exception:
            continue

        _g["prod_resid_after_pop"] = _pop_fit.resid
        residual_frames.append(_g[[
            "ISO3",
            "Country_Name",
            "Year",
            "ln_Production",
            "Production_tonnes",
            "ln_Population",
            "Avg_Temp_C",
            "Rain_mm",
            "Oil_Price_Brent_USD",
            "prod_resid_after_pop",
        ]])

        _temp_ok = _g["Avg_Temp_C"].nunique() >= MIN_UNIQUE
        _rain_ok = _g["Rain_mm"].nunique() >= MIN_UNIQUE
        _env_vars = []
        if _temp_ok:
            _env_vars.append("Avg_Temp_C")
        if _rain_ok:
            _env_vars.append("Rain_mm")

        _r_temp, _p_temp = (np.nan, np.nan)
        _r_rain, _p_rain = (np.nan, np.nan)
        if _temp_ok:
            _r_temp, _p_temp = stats.pearsonr(_g["Avg_Temp_C"], _g["prod_resid_after_pop"])
        if _rain_ok:
            _r_rain, _p_rain = stats.pearsonr(_g["Rain_mm"], _g["prod_resid_after_pop"])

        _r2_pop = _pop_fit.rsquared
        _r2_env = _fit_r2(_g["ln_Production"], _g[_env_vars]) if _env_vars else np.nan
        _r2_full = _fit_r2(_g["ln_Production"], _g[["ln_Population"] + _env_vars]) if _env_vars else np.nan
        _delta_env = _r2_full - _r2_pop if pd.notna(_r2_full) else np.nan
        _delta_pop = _r2_full - _r2_env if pd.notna(_r2_full) and pd.notna(_r2_env) else np.nan

        _std_fit = _standardized_fit(_g, ["ln_Population"] + _env_vars)
        _beta_pop = np.nan
        _beta_temp = np.nan
        _beta_rain = np.nan
        _p_beta_temp = np.nan
        _p_beta_rain = np.nan
        if _std_fit is not None:
            _beta_pop = _std_fit.params.get("ln_Population", np.nan)
            _beta_temp = _std_fit.params.get("Avg_Temp_C", np.nan)
            _beta_rain = _std_fit.params.get("Rain_mm", np.nan)
            _p_beta_temp = _std_fit.pvalues.get("Avg_Temp_C", np.nan)
            _p_beta_rain = _std_fit.pvalues.get("Rain_mm", np.nan)

        _env_abs = [
            abs(_r_temp) if pd.notna(_r_temp) else np.nan,
            abs(_r_rain) if pd.notna(_r_rain) else np.nan,
        ]
        _max_abs_env_r = np.nanmax(_env_abs)
        if pd.isna(_r_temp) and pd.isna(_r_rain):
            _best_env = None
            _best_env_p = np.nan
        elif pd.isna(_r_rain) or (pd.notna(_r_temp) and abs(_r_temp) >= abs(_r_rain)):
            _best_env = "Temperature"
            _best_env_p = _p_temp
        else:
            _best_env = "Rainfall"
            _best_env_p = _p_rain
        _env_dominates_r2 = pd.notna(_delta_env) and pd.notna(_delta_pop) and _delta_env > _delta_pop
        _max_env_beta = np.nanmax([abs(_beta_temp), abs(_beta_rain)])
        _env_dominates_beta = pd.notna(_max_env_beta) and pd.notna(_beta_pop) and _max_env_beta > abs(_beta_pop)

        if (pd.notna(_max_abs_env_r) and _max_abs_env_r >= TIER_STRONG_R
                and pd.notna(_best_env_p) and _best_env_p < 0.05
                and pd.notna(_delta_env) and _delta_env >= TIER_STRONG_DR2):
            _tier = "Strong"
        elif (
            (pd.notna(_delta_env) and _delta_env >= TIER_STRONG_DR2)
            or _env_dominates_r2
            or (pd.notna(_max_abs_env_r) and _max_abs_env_r >= TIER_MOD_R
                and pd.notna(_best_env_p) and _best_env_p < TIER_MOD_P)
        ):
            _tier = "Moderate"
        else:
            _tier = "Weak / inconclusive"

        country_rows.append({
            "ISO3": _iso3,
            "Country": _g["Country_Name"].iloc[0],
            "n": len(_g),
            "Rain unique": int(_g["Rain_mm"].nunique()),
            "Population R2": _r2_pop,
            "Environment-only R2": _r2_env,
            "Full R2": _r2_full,
            "Environment added R2": _delta_env,
            "Population added R2": _delta_pop,
            "r Temp after Pop": _r_temp,
            "p Temp": _p_temp,
            "r Rain after Pop": _r_rain,
            "p Rain": _p_rain,
            "Std beta Pop": _beta_pop,
            "Std beta Temp": _beta_temp,
            "Std beta Rain": _beta_rain,
            "p beta Temp": _p_beta_temp,
            "p beta Rain": _p_beta_rain,
            "Max abs env r": _max_abs_env_r,
            "Best environmental variable": _best_env,
            "Env added R2 > Pop added R2": _env_dominates_r2,
            "Env beta > Pop beta": _env_dominates_beta,
            "Candidate tier": _tier,
        })

    country_screen = pd.DataFrame(country_rows).sort_values(
        ["Candidate tier", "Environment added R2", "Max abs env r"],
        ascending=[True, False, False],
    )
    residual_panel = pd.concat(residual_frames, ignore_index=True)
    candidate_screen = country_screen[
        country_screen["Candidate tier"].isin(["Strong", "Moderate"])
    ].sort_values(["Candidate tier", "Environment added R2"], ascending=[True, False])
    return MIN_OBS, TIER_STRONG_DR2, TIER_STRONG_R, TIER_MOD_R, TIER_MOD_P, candidate_screen, country_screen, residual_panel


@app.cell
def _(MIN_OBS, TIER_MOD_P, TIER_MOD_R, TIER_STRONG_DR2, TIER_STRONG_R, country_screen, mo, pd):
    def _format_screen(df):
        _d = df.copy()
        _float_cols = [
            "Population R2",
            "Environment-only R2",
            "Full R2",
            "Environment added R2",
            "Population added R2",
            "r Temp after Pop",
            "p Temp",
            "r Rain after Pop",
            "p Rain",
            "Max abs env r",
        ]
        for _c in _float_cols:
            if _c in _d.columns:
                _d[_c] = _d[_c].map(lambda x: "" if pd.isna(x) else f"{x:.3f}")
        return _d

    _top_cols = [
        "Candidate tier",
        "ISO3",
        "Country",
        "n",
        "Rain unique",
        "Population R2",
        "Environment-only R2",
        "Full R2",
        "Environment added R2",
        "Population added R2",
        "r Temp after Pop",
        "p Temp",
        "r Rain after Pop",
        "p Rain",
        "Best environmental variable",
    ]

    _ranked = _format_screen(
        country_screen.sort_values("Environment added R2", ascending=False)[_top_cols].head(20)
    )

    _counts = country_screen["Candidate tier"].value_counts().reindex(
        ["Strong", "Moderate", "Weak / inconclusive"],
        fill_value=0,
    )
    _n_strong = int(_counts["Strong"])
    _n_mod    = int(_counts["Moderate"])
    _n_weak   = int(_counts["Weak / inconclusive"])
    _n_total  = _n_strong + _n_mod + _n_weak

    mo.md(f"""
    ### 1.1 Environmental Sensitivity Ranking

    **Strong: {_n_strong} · Moderate: {_n_mod} · Weak / inconclusive: {_n_weak}** countries (of {_n_total} with ≥ {MIN_OBS} obs)

    > **These tiers are a heuristic screening rule, not a formal hypothesis test.** Threshold guide: **Strong** = |r| ≥ {TIER_STRONG_R}, p < 0.05, and ΔR² ≥ {TIER_STRONG_DR2} from environmental variables; **Moderate** = ΔR² ≥ {TIER_STRONG_DR2}, or env dominates population in R², or |r| ≥ {TIER_MOD_R} with p < {TIER_MOD_P}.

    > **Multiple testing note.** ~{_n_total * 2} per-country correlation tests are performed. At α = 0.05, several "significant" results are expected by chance. Treat tier assignments as candidate-selection signals, not definitive statistical conclusions.

    The table below ranks countries by how much environmental variables add after population has already been used.

    {mo.as_html(_ranked)}
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ## 2. Population-Dominated Countries

    These are countries where the population-only model already explains a large share of production variation and environmental variables add comparatively little.
    """)
    return


@app.cell
def _(country_screen, mo, pd):
    _pop_dominated = country_screen[
        (country_screen["Population R2"] >= 0.50)
        & (country_screen["Environment added R2"].fillna(0) < 0.10)
    ].sort_values("Population R2", ascending=False)

    _display = _pop_dominated[[
        "ISO3",
        "Country",
        "n",
        "Population R2",
        "Environment added R2",
        "Population added R2",
        "Max abs env r",
        "Candidate tier",
    ]].head(20).copy()

    for _c in ["Population R2", "Environment added R2", "Population added R2", "Max abs env r"]:
        _display[_c] = _display[_c].map(lambda x: "" if pd.isna(x) else f"{x:.3f}")

    mo.md(f"""
    ### 2.1 Countries Mostly Explained by Population

    {mo.as_html(_display)}

    > These countries are not "bad" cases. They just answer a different question: production tracks scale/population more clearly than year-to-year environmental variation in this dataset.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ## 3. Interactive Country Explorer

    Pick a candidate country to inspect the population-adjusted residuals directly.
    """)
    return


@app.cell
def _(candidate_screen, country_screen, mo):
    _source = candidate_screen if len(candidate_screen) > 0 else country_screen
    _choices = [
        f"{row.Country} ({row.ISO3})"
        for row in _source.sort_values("Environment added R2", ascending=False).itertuples()
    ]
    country_select = mo.ui.dropdown(
        options=_choices,
        value=_choices[0],
        label="Country",
    )
    mo.md(f"""
    ### Choose a Country

    {country_select}
    """)
    return (country_select,)


@app.cell
def _(
    ACCENT,
    ACCENT2,
    ACCENT3,
    GREY,
    country_screen,
    country_select,
    mo,
    np,
    plt,
    residual_panel,
):
    _selected_iso3 = country_select.value.rsplit("(", 1)[-1].rstrip(")")
    _d = residual_panel[residual_panel["ISO3"] == _selected_iso3].sort_values("Year").copy()
    _meta = country_screen[country_screen["ISO3"] == _selected_iso3].iloc[0]

    fig_country, axes_country = plt.subplots(2, 2, figsize=(13, 8))
    fig_country.suptitle(
        f"{_meta['Country']} – Population-Adjusted Environmental Screen",
        fontsize=13,
        fontweight="bold",
    )

    ax = axes_country[0, 0]
    ax.plot(_d["Year"], _d["ln_Production"], color=ACCENT, marker="o", linewidth=1.7, label="ln(Production)")
    ax.plot(_d["Year"], _d["ln_Population"], color=GREY, marker="s", linewidth=1.4, label="ln(Population)")
    ax.set_title("Log production and log population")
    ax.set_xlabel("Year")
    ax.legend(fontsize=8)

    ax = axes_country[0, 1]
    ax.axhline(0, color="#333333", linestyle="--", linewidth=1)
    ax.plot(_d["Year"], _d["prod_resid_after_pop"], color=ACCENT2, marker="o", linewidth=1.7)
    ax.set_title("Production residual after population")
    ax.set_xlabel("Year")
    ax.set_ylabel("Residual")

    ax = axes_country[1, 0]
    ax.scatter(_d["Avg_Temp_C"], _d["prod_resid_after_pop"], color=ACCENT3, alpha=0.85)
    if _d["Avg_Temp_C"].nunique() >= 2:
        _coef = np.polyfit(_d["Avg_Temp_C"], _d["prod_resid_after_pop"], 1)
        _x = np.linspace(_d["Avg_Temp_C"].min(), _d["Avg_Temp_C"].max(), 100)
        ax.plot(_x, np.polyval(_coef, _x), color="#333333", linestyle="--", linewidth=1.2)
    ax.axhline(0, color="#777777", linestyle=":", linewidth=1)
    ax.set_title(f"Residual vs temperature (r = {_meta['r Temp after Pop']:.3f})")
    ax.set_xlabel("Average temperature (C)")
    ax.set_ylabel("Residual")

    ax = axes_country[1, 1]
    if _d["Rain_mm"].nunique() >= 5:
        ax.scatter(_d["Rain_mm"], _d["prod_resid_after_pop"], color=ACCENT2, alpha=0.85)
        _coef = np.polyfit(_d["Rain_mm"], _d["prod_resid_after_pop"], 1)
        _x = np.linspace(_d["Rain_mm"].min(), _d["Rain_mm"].max(), 100)
        ax.plot(_x, np.polyval(_coef, _x), color="#333333", linestyle="--", linewidth=1.2)
        ax.set_title(f"Residual vs rainfall (r = {_meta['r Rain after Pop']:.3f})")
        ax.set_xlabel("Rainfall (mm/yr)")
        ax.set_ylabel("Residual")
    else:
        ax.axis("off")
        ax.text(
            0.5,
            0.5,
            "Rainfall is fixed or nearly fixed\nfor this country,\nso within-country rainfall screening\nis not meaningful.",
            ha="center",
            va="center",
            fontsize=11,
            color="#444444",
        )

    plt.tight_layout()
    mo.mpl.interactive(fig_country)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ## 4. Candidate Cohort Regression

    Now compare the full panel against the countries flagged as environmental sensitivity candidates.
    """)
    return


@app.cell
def _(candidate_screen, mo, panel, pd, smf):
    candidate_iso3 = candidate_screen["ISO3"].tolist()
    # Use rainfall decomposition (between-country mean + within-country deviation) consistent
    # with the main workbook — raw Rain_mm conflates cross-country and year-to-year signals.
    _formula = (
        "ln_Production ~ Avg_Temp_C + Rain_mm_country_mean + Rain_mm_within"
        " + ln_Population + Oil_Price_Brent_USD"
    )

    _full_df = panel.dropna(subset=[
        "ln_Production",
        "Avg_Temp_C",
        "Rain_mm_country_mean",
        "Rain_mm_within",
        "ln_Population",
        "Oil_Price_Brent_USD",
    ]).copy()
    _cand_df = _full_df[_full_df["ISO3"].isin(candidate_iso3)].copy()

    _rows = []
    cohort_models = []

    for _label, _df in [("Full panel", _full_df), ("Candidate cohort", _cand_df)]:
        if len(_df) < 20 or _df["ISO3"].nunique() < 2:
            continue
        _res = smf.ols(_formula, data=_df).fit(cov_type="HC3")
        cohort_models.append((_label, _res))
        _rows.append({
            "Sample": _label,
            "n": int(_res.nobs),
            "Countries": int(_df["ISO3"].nunique()),
            "R2": _res.rsquared,
            "Adjusted R2": _res.rsquared_adj,
            "Temp p": _res.pvalues.get("Avg_Temp_C", float("nan")),
            "Rain (between) p": _res.pvalues.get("Rain_mm_country_mean", float("nan")),
            "Rain (within) p": _res.pvalues.get("Rain_mm_within", float("nan")),
            "Population p": _res.pvalues.get("ln_Population", float("nan")),
            "Oil p": _res.pvalues.get("Oil_Price_Brent_USD", float("nan")),
        })

    cohort_compare = pd.DataFrame(_rows)
    _display = cohort_compare.copy()
    for _c in ["R2", "Adjusted R2", "Temp p", "Rain (between) p", "Rain (within) p", "Population p", "Oil p"]:
        if _c in _display.columns:
            _display[_c] = _display[_c].map(lambda x: "" if pd.isna(x) else ("< 0.0001" if x < 0.0001 else f"{x:.4f}"))

    mo.md(f"""
    ### 4.1 Full Panel vs Candidate Cohort

    {mo.as_html(_display)}

    > Rainfall is decomposed into a between-country structural mean (`Rain_mm_country_mean`) and a within-country annual deviation (`Rain_mm_within`), matching the main workbook's specification. This comparison asks whether the environmental variables look more important after the notebook focuses on countries flagged by the residual screening step.
    """)
    return (cohort_models,)


@app.cell
def _(ACCENT, ACCENT2, cohort_models, mo, pd, plt):
    _coef_rows = []
    for _label, _res in cohort_models:
        for _term, _nice in [
            ("Avg_Temp_C", "Temperature"),
            ("Rain_mm_country_mean", "Rainfall-between"),
            ("Rain_mm_within", "Rainfall-within"),
            ("ln_Population", "ln(Population)"),
            ("Oil_Price_Brent_USD", "Oil price"),
        ]:
            _ci = _res.conf_int().loc[_term]
            _coef_rows.append({
                "Sample": _label,
                "Term": _nice,
                "coef": _res.params[_term],
                "lo": _ci[0],
                "hi": _ci[1],
                "p": _res.pvalues[_term],
            })
    _coef_df = pd.DataFrame(_coef_rows)

    fig_coef_compare, ax_coef_compare = plt.subplots(figsize=(10, 6))
    _terms = ["Temperature", "Rainfall-between", "Rainfall-within", "ln(Population)", "Oil price"]
    _offsets = {"Full panel": -0.17, "Candidate cohort": 0.17}
    _colors = {"Full panel": ACCENT, "Candidate cohort": ACCENT2}

    for _sample in _coef_df["Sample"].unique():
        _sub = _coef_df[_coef_df["Sample"] == _sample].set_index("Term").loc[_terms].reset_index()
        _y = list(range(len(_terms)))
        _y = [v + _offsets.get(_sample, 0) for v in _y]
        _xerr = [
            _sub["coef"].values - _sub["lo"].values,
            _sub["hi"].values - _sub["coef"].values,
        ]
        ax_coef_compare.errorbar(
            _sub["coef"],
            _y,
            xerr=_xerr,
            fmt="o",
            color=_colors.get(_sample, "#555555"),
            capsize=4,
            label=_sample,
        )

    ax_coef_compare.axvline(0, color="#777777", linestyle="--", linewidth=1)
    ax_coef_compare.set_yticks(range(len(_terms)))
    ax_coef_compare.set_yticklabels(_terms)
    ax_coef_compare.set_xlabel("Coefficient estimate with 95% CI")
    ax_coef_compare.set_title("Full panel vs candidate cohort coefficients")
    ax_coef_compare.legend()
    plt.tight_layout()

    mo.mpl.interactive(fig_coef_compare)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ## 5. Individual Country Mini-Models

    For the strongest countries, fit a small country-specific model. These models are useful for interpretation, but each country has only about 30 observations, so treat them as case-study evidence.

    > **Rainfall in mini-models:** Within a single country there is no between-country variation, so raw `Rain_mm` is used directly (no decomposition needed). Where rainfall has too few unique values, the mini-model uses population and temperature only.
    """)
    return


@app.cell
def _(candidate_screen, mo, panel, pd, smf):
    _mini_rows = []
    _top_iso3 = candidate_screen.sort_values("Environment added R2", ascending=False)["ISO3"].head(10).tolist()

    for _iso3 in _top_iso3:
        _g = panel[panel["ISO3"] == _iso3].sort_values("Year").copy()
        _rain_ok = _g["Rain_mm"].nunique() >= 5
        _formula = "ln_Production ~ ln_Population + Avg_Temp_C"
        if _rain_ok:
            _formula += " + Rain_mm"

        try:
            _res = smf.ols(_formula, data=_g).fit(cov_type="HC3")
        except Exception:
            continue

        _mini_rows.append({
            "ISO3": _iso3,
            "Country": _g["Country_Name"].iloc[0],
            "n": int(_res.nobs),
            "Rain included?": "Yes" if _rain_ok else "No",
            "R2": _res.rsquared,
            "Adj R2": _res.rsquared_adj,
            "Temp coef": _res.params.get("Avg_Temp_C", float("nan")),
            "Temp p": _res.pvalues.get("Avg_Temp_C", float("nan")),
            "Rain coef": _res.params.get("Rain_mm", float("nan")),
            "Rain p": _res.pvalues.get("Rain_mm", float("nan")),
            "Pop coef": _res.params.get("ln_Population", float("nan")),
            "Pop p": _res.pvalues.get("ln_Population", float("nan")),
        })

    mini_model_table = pd.DataFrame(_mini_rows)
    _display = mini_model_table.copy()
    for _c in ["R2", "Adj R2", "Temp coef", "Temp p", "Rain coef", "Rain p", "Pop coef", "Pop p"]:
        if _c in _display.columns:
            _display[_c] = _display[_c].map(lambda x: "" if pd.isna(x) else ("< 0.0001" if "p" in _c and x < 0.0001 else f"{x:.4f}"))

    mo.md(f"""
    ### 5.1 Top Candidate Country Models

    {mo.as_html(_display)}

    > Rainfall is only included when it has enough within-country variation. Otherwise, the model uses population and temperature only.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ## 6. Interpretation

    This follow-up changes the story from one global result to a screening workflow:

    - Population explains broad country scale.
    - Population-adjusted residuals show which countries produce more or less than expected from population alone.
    - Temperature and rainfall are then tested against what population did not explain.
    - The strongest countries become candidates for deeper case-study interpretation.

    Recommended next step: choose 3-5 strong countries from the ranking table and investigate agricultural history, climate shocks, policy changes, coffee variety, and data-quality notes for those countries.
    """)
    return


if __name__ == "__main__":
    app.run()
