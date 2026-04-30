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

    This notebook is an exploratory screening tool. It identifies candidate countries for deeper environmental case-study analysis; it does not prove climate causation. Exploratory screening is the first step of the research cycle — it focuses the investigation before committing to formal tests. All H₀/H₁ conclusions with teacher-phrasing are in the main workbook (`coffee_analysis.py` §2–§5).
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
    from statsmodels.stats.multitest import multipletests
    from statsmodels.stats.stattools import durbin_watson
    from statsmodels.stats.anova import anova_lm

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
        anova_lm,
        durbin_watson,
        mo,
        multipletests,
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

    > **Partial correlation (FWL-complete).** The reported r values are **true FWL partial correlations**: both the response *and* each environmental predictor are separately regressed on ln(Population), and their residuals are then correlated. This removes any spurious correlation between the environmental predictor and the response that runs through population. For formal H₀/H₁ inference see the main workbook §2–§5. The standardized-β columns in the ranking table below come from a full multivariate fit per country and measure a related but distinct quantity (partial regression coefficient after all other predictors are controlled). The two effect-size columns come from different models and are not directly comparable.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    #### Course context: FWL vs. General Factorial Analysis vs. RCBD (Section 4)

    The FWL theorem is an extracurricular research technique used here to accomplish something
    similar to what we did with **General Factorial Analysis** and **RCBD** in Section 4 of the course.
    Understanding the parallels and differences grounds this analysis in familiar territory.

    ---

    **What each approach does**

    *FWL (this notebook)* — A theorem about regression: regress both Y and a focal predictor X₂
    on a control variable X₁, keep both sets of residuals, then correlate them. The result equals
    the coefficient X₂ would get in a full MLR with both predictors included. Here, ln(Population)
    is the control; temperature and rainfall are the focal predictors.

    *General Factorial (Section 4)* — An experimental design that tests all combinations of k
    factors at controlled levels. ANOVA partitions variance into main effects, interaction effects,
    and error. The key capability factorial has that FWL lacks: **detecting interactions** — whether
    the effect of Factor A depends on the level of Factor B.

    *RCBD (Section 4)* — A design for one factor of interest plus one **nuisance factor** (the
    block). Each treatment appears exactly once per block. ANOVA partitions SS_Total into
    SS_Treatments + SS_Blocks + SS_Error, removing block-to-block variability from the error term
    to give a more powerful test of treatments.

    ---

    **How they overlap**

    All three are doing the same thing conceptually: **isolating the effect of one variable by
    accounting for another.** They differ only in how they achieve that control:

    | | FWL | RCBD | Factorial |
    |---|---|---|---|
    | How control is achieved | Algebraic residualization of observed data | Block structure absorbs nuisance SS before the F-test | Randomization makes factors orthogonal by design |
    | Data source | Observational panel | Designed experiment | Designed experiment |
    | Nuisance variable role | Partialed out of both Y and X | Absorbed into SS_Blocks | Balanced across factor levels by randomization |
    | Interaction estimated? | No | No (assumed absent — RCBD requires `+` not `*`) | Yes — core purpose |

    **FWL is actually most similar to RCBD**, not to factorial. In RCBD, the "block" (country, in
    this analogy) is a nuisance factor you want to remove before testing treatments. The RCBD model
    is additive — `aov(obs ~ trt + blk)` — and explicitly assumes no treatment-by-block interaction,
    just as FWL assumes population is an additive nuisance separable from the environmental signal.
    RCBD removes SS_Blocks from SS_Error mathematically; FWL removes the population effect by
    residualization — two routes to the same destination.

    ---

    **The critical differences**

    *Causal inference:* Factorial and RCBD designs use randomized assignment, so their F-tests
    support causal claims. FWL operates on observational data — the partial correlation is a cleaner
    measure than raw r, but unmeasured confounders (altitude, variety, trade policy) cannot be ruled
    out. Statistical control is not the same as experimental control.

    *Interactions:* FWL is not a design tool — it is used here to evaluate data after the fact,
    partializing out one nuisance variable (population). It does not detect interactions. If
    temperature and rainfall interact in their effect on production (e.g., heat is damaging only in
    dry conditions), FWL would miss it entirely. A factorial design with Temperature × Rainfall ×
    Population as factors would catch it; a panel regression with an interaction term
    (`Temp * Rain_mm_within`) would be the observational equivalent.
    """)
    return


@app.cell
def _(anova_lm, durbin_watson, multipletests, np, panel, pd, sm, stats):
    MIN_OBS = 15
    MIN_UNIQUE = 5

    # Heuristic screening thresholds — NOT formal hypothesis tests.
    # Used to assign candidate tiers for case-study selection only.
    TIER_STRONG_R   = 0.45   # |r| between env var and pop-adjusted residual (partial)
    TIER_STRONG_DR2 = 0.10   # env vars must add ≥10pp R² beyond population
    TIER_MOD_R      = 0.35   # |r| threshold for Moderate tier
    TIER_MOD_P      = 0.10   # p-value threshold for Moderate tier (BH-adjusted)

    def _fit_r2_on_common(y, pop_col, env_cols, data):
        """
        Compute R² for population-only, env-only, and full models on the same
        complete-case subsample (avoids comparing R² values from different n).
        Returns (r2_pop, r2_env, r2_full) or (nan, nan, nan) on failure.
        """
        _all_cols = [y] + [pop_col] + env_cols
        _d = data[_all_cols].dropna()
        _n_env = len(env_cols)
        if len(_d) < max(_n_env + 5, MIN_OBS):
            return np.nan, np.nan, np.nan
        _y = _d[y]
        # Population-only
        _x_pop = sm.add_constant(_d[[pop_col]], has_constant="add")
        # Env-only
        _x_env = sm.add_constant(_d[env_cols], has_constant="add")
        # Full
        _x_full = sm.add_constant(_d[[pop_col] + env_cols], has_constant="add")
        try:
            _r2_pop  = sm.OLS(_y, _x_pop).fit().rsquared
            _r2_env  = sm.OLS(_y, _x_env).fit().rsquared if _n_env > 0 else np.nan
            _r2_full = sm.OLS(_y, _x_full).fit().rsquared
            return _r2_pop, _r2_env, _r2_full
        except Exception:
            return np.nan, np.nan, np.nan

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

        # --- Step 1: Fit population-only model and extract production residuals ---
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

        # Fix 4 — Durbin-Watson statistic on production residuals (diagnostic for serial autocorrelation).
        # DW near 2.0 = low autocorrelation; DW < 1.5 suggests positive AR(1), inflating p-values.
        try:
            _dw_stat = float(durbin_watson(_pop_fit.resid))
        except Exception:
            _dw_stat = np.nan

        _temp_ok = _g["Avg_Temp_C"].nunique() >= MIN_UNIQUE
        _rain_ok = _g["Rain_mm"].nunique() >= MIN_UNIQUE
        _env_vars = []
        if _temp_ok:
            _env_vars.append("Avg_Temp_C")
        if _rain_ok:
            _env_vars.append("Rain_mm")

        # --- Fix 1: True FWL partial correlations ---
        # Residualize BOTH the response AND each environmental predictor on ln(Population),
        # then correlate the two sets of residuals. This is the correct FWL partial correlation.
        _r_temp, _p_temp = (np.nan, np.nan)
        _r_rain, _p_rain = (np.nan, np.nan)

        _prod_resid = _g["prod_resid_after_pop"].values  # y residuals (already computed)

        if _temp_ok:
            # Regress Avg_Temp_C on ln(Population) → extract temp residuals
            _temp_data = _g[["Avg_Temp_C", "ln_Population"]].dropna()
            if len(_temp_data) >= MIN_OBS:
                try:
                    _temp_pop_x = sm.add_constant(_temp_data[["ln_Population"]], has_constant="add")
                    _temp_resid = sm.OLS(_temp_data["Avg_Temp_C"], _temp_pop_x).fit().resid
                    # Align indices: use the intersection of the production residual index and temp residual index
                    _common_idx = _g.index.intersection(_temp_resid.index)
                    _r_temp, _p_temp = stats.pearsonr(
                        _prod_resid[_g.index.get_indexer(_common_idx)],
                        _temp_resid.loc[_common_idx].values,
                    )
                except Exception:
                    pass

        if _rain_ok:
            # Regress Rain_mm on ln(Population) → extract rain residuals
            _rain_data = _g[["Rain_mm", "ln_Population"]].dropna()
            if len(_rain_data) >= MIN_OBS:
                try:
                    _rain_pop_x = sm.add_constant(_rain_data[["ln_Population"]], has_constant="add")
                    _rain_resid = sm.OLS(_rain_data["Rain_mm"], _rain_pop_x).fit().resid
                    _common_idx = _g.index.intersection(_rain_resid.index)
                    _r_rain, _p_rain = stats.pearsonr(
                        _prod_resid[_g.index.get_indexer(_common_idx)],
                        _rain_resid.loc[_common_idx].values,
                    )
                except Exception:
                    pass

        # --- R² values computed on a common complete-case sample (Fix 6.2) ---
        _r2_pop, _r2_env, _r2_full = _fit_r2_on_common(
            "ln_Production", "ln_Population", _env_vars, _g
        ) if _env_vars else (np.nan, np.nan, np.nan)
        # If no env_vars, r2_pop from the individual fit above
        if not _env_vars:
            _r2_pop = _pop_fit.rsquared
        _delta_env = _r2_full - _r2_pop if (pd.notna(_r2_full) and pd.notna(_r2_pop)) else np.nan
        _delta_pop = _r2_full - _r2_env if (pd.notna(_r2_full) and pd.notna(_r2_env)) else np.nan

        # --- Fix 3: Incremental F-test for environmental variables beyond population ---
        _p_f_incr = np.nan
        if _env_vars and pd.notna(_r2_full) and pd.notna(_r2_pop):
            _all_cols_incr = ["ln_Production", "ln_Population"] + _env_vars
            _d_incr = _g[_all_cols_incr].dropna()
            if len(_d_incr) >= len(_env_vars) + MIN_OBS:
                try:
                    _y_incr = _d_incr["ln_Production"]
                    _x_rest = sm.add_constant(_d_incr[["ln_Population"]], has_constant="add")
                    _x_full = sm.add_constant(_d_incr[["ln_Population"] + _env_vars], has_constant="add")
                    _fit_rest = sm.OLS(_y_incr, _x_rest).fit()
                    _fit_full = sm.OLS(_y_incr, _x_full).fit()
                    _anova_tbl = anova_lm(_fit_rest, _fit_full)
                    _p_f_incr = float(_anova_tbl["Pr(>F)"].iloc[1])
                except Exception:
                    pass

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
        _max_env_beta = np.nanmax([abs(_beta_temp) if pd.notna(_beta_temp) else np.nan,
                                   abs(_beta_rain) if pd.notna(_beta_rain) else np.nan])
        _env_dominates_beta = pd.notna(_max_env_beta) and pd.notna(_beta_pop) and _max_env_beta > abs(_beta_pop)

        # Tier will be reassigned after BH correction (Fix 2); store raw values for now.
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
            "r Temp after Pop (partial)": _r_temp,
            "p Temp": _p_temp,
            "r Rain after Pop (partial)": _r_rain,
            "p Rain": _p_rain,
            "p F-incr": _p_f_incr,
            "DW stat": _dw_stat,
            "Std beta Pop": _beta_pop,
            "Std beta Temp": _beta_temp,
            "Std beta Rain": _beta_rain,
            "p beta Temp": _p_beta_temp,
            "p beta Rain": _p_beta_rain,
            "Max abs env r": _max_abs_env_r,
            "Best environmental variable": _best_env,
            "_best_env_p_raw": _best_env_p,
            "_best_env_label": _best_env,
            "Env added R2 > Pop added R2": _env_dominates_r2,
            "Env beta > Pop beta": _env_dominates_beta,
            # Temp/rain raw p stored separately so BH can be applied below
            "_p_temp_raw": _p_temp,
            "_p_rain_raw": _p_rain,
            "_delta_env": _delta_env,
            "_env_dominates_r2": _env_dominates_r2,
            "_max_abs_env_r": _max_abs_env_r,
            "_p_f_incr": _p_f_incr,
        })

    # --- Fix 2: Benjamini-Hochberg FDR correction across all country-level p-values ---
    _screen_df = pd.DataFrame(country_rows)

    # Collect raw p-values; treat NaN as 1.0 for correction purposes (no evidence)
    _p_temp_arr = _screen_df["_p_temp_raw"].fillna(1.0).values
    _p_rain_arr = _screen_df["_p_rain_raw"].fillna(1.0).values

    _, _p_temp_adj, _, _ = multipletests(_p_temp_arr, method="fdr_bh")
    _, _p_rain_adj, _, _ = multipletests(_p_rain_arr, method="fdr_bh")

    # Restore NaN where the original was NaN (country lacked enough variation)
    _p_temp_adj = np.where(_screen_df["_p_temp_raw"].isna(), np.nan, _p_temp_adj)
    _p_rain_adj = np.where(_screen_df["_p_rain_raw"].isna(), np.nan, _p_rain_adj)

    _screen_df["p Temp (BH-adj)"] = _p_temp_adj
    _screen_df["p Rain (BH-adj)"] = _p_rain_adj

    # Derive BH-adjusted best-env p for tier classification
    def _bh_best_p(row):
        _t = row["p Temp (BH-adj)"] if pd.notna(row["p Temp (BH-adj)"]) else np.nan
        _r = row["p Rain (BH-adj)"] if pd.notna(row["p Rain (BH-adj)"]) else np.nan
        if row["_best_env_label"] == "Temperature":
            return _t
        elif row["_best_env_label"] == "Rainfall":
            return _r
        return np.nan

    _screen_df["_best_env_p_adj"] = _screen_df.apply(_bh_best_p, axis=1)

    # --- Fix 2 + Fix 3: Tier assignment using BH-adjusted p-values AND incremental F-test ---
    def _assign_tier(row):
        _max_r   = row["_max_abs_env_r"]
        _p_adj   = row["_best_env_p_adj"]
        _dr2     = row["_delta_env"]
        _p_f     = row["_p_f_incr"]
        _dom_r2  = row["_env_dominates_r2"]

        # Strong: high partial r AND corrected p significant AND ΔR² ≥ threshold
        # AND incremental F-test confirms the R² gain is not just noise (Fix 3)
        if (
            pd.notna(_max_r) and _max_r >= TIER_STRONG_R
            and pd.notna(_p_adj) and _p_adj < 0.05
            and pd.notna(_dr2) and _dr2 >= TIER_STRONG_DR2
            and pd.notna(_p_f) and _p_f < 0.05
        ):
            return "Strong"
        elif (
            (pd.notna(_dr2) and _dr2 >= TIER_STRONG_DR2)
            or _dom_r2
            or (pd.notna(_max_r) and _max_r >= TIER_MOD_R
                and pd.notna(_p_adj) and _p_adj < TIER_MOD_P)
        ):
            return "Moderate"
        else:
            return "Weak / inconclusive"

    _screen_df["Candidate tier"] = _screen_df.apply(_assign_tier, axis=1)

    # Drop internal helper columns before exposing
    _internal_cols = [
        "_p_temp_raw", "_p_rain_raw", "_delta_env", "_env_dominates_r2",
        "_max_abs_env_r", "_p_f_incr", "_best_env_p_raw", "_best_env_label",
        "_best_env_p_adj",
    ]
    _screen_df = _screen_df.drop(columns=[c for c in _internal_cols if c in _screen_df.columns])

    country_screen = _screen_df.sort_values(
        ["Candidate tier", "Environment added R2", "Max abs env r"],
        ascending=[True, False, False],
    )
    residual_panel = pd.concat(residual_frames, ignore_index=True)
    candidate_screen = country_screen[
        country_screen["Candidate tier"].isin(["Strong", "Moderate"])
    ].sort_values(["Candidate tier", "Environment added R2"], ascending=[True, False])
    return (
        MIN_OBS,
        TIER_MOD_P,
        TIER_MOD_R,
        TIER_STRONG_DR2,
        TIER_STRONG_R,
        candidate_screen,
        country_screen,
        residual_panel,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    #### Reading the new screening columns

    **Benjamini-Hochberg (BH) FDR correction — Note 17**
    Running ~74 countries × 2 environmental variables ≈ 148 simultaneous Pearson tests at α = 0.05 means about 7–8 false positives are expected by chance even when no real signal exists. The Bonferroni correction fixes this by making each test harder to pass (α/148 ≈ 0.00034) but is too conservative when tests are correlated. The Benjamini-Hochberg procedure controls the *False Discovery Rate* (FDR) — the expected proportion of "significant" results that are actually false — at 5%. The `p Temp (BH-adj)` and `p Rain (BH-adj)` columns in the table are BH-corrected. Tier classification uses these adjusted values, not raw p-values.

    **Incremental F-test — Note 18**
    The Strong tier requires that adding temperature and rainfall to a population-only model produces a statistically significant improvement in fit, tested with a nested F-test:

    - Restricted model: ln(Production) ~ ln(Population)
    - Full model: ln(Production) ~ ln(Population) + Temp + Rain

    The F-statistic measures the reduction in residual sum of squares (RSS) relative to the degrees of freedom consumed by the two extra predictors. The `p F-incr` column shows this p-value. A country can have a moderate partial r but fail the F-test if the improvement is not consistent across the full time series — that country would be classified as Moderate or Weak, not Strong.

    **Durbin-Watson statistic — Note 19**
    Coffee production within a country is often serially correlated over time (drought, disease, expansion all persist across years). The `DW stat` column measures this autocorrelation: values near 2.0 indicate no autocorrelation; values below 1.5 suggest positive AR(1), meaning consecutive residuals move together. **BH correction cannot fix this problem** — BH adjusts for the number of tests, not for inflated test statistics within each test. A country showing DW < 1.5 together with a small BH-adjusted p-value should be treated as a weaker candidate than the p-value alone suggests.

    **Tier thresholds — what the numbers mean**
    The thresholds `TIER_STRONG_R = 0.45` and `TIER_STRONG_DR2 = 0.10` are heuristic cutoffs chosen for case-study selection, not derived from a statistical distribution. r ≥ 0.45 implies r² ≈ 0.20 — the environmental variable accounts for at least 20% of the population-adjusted production variance. ΔR² ≥ 0.10 means environment must add at least 10 percentage points of explained variance beyond population alone. These numbers were chosen to be "large enough to matter for a case study," not because they represent a critical value at any α level.
    """)
    return


@app.cell
def _(
    MIN_OBS,
    TIER_MOD_P,
    TIER_MOD_R,
    TIER_STRONG_DR2,
    TIER_STRONG_R,
    country_screen,
    mo,
    pd,
):
    def _format_screen(df):
        _d = df.copy()
        _float_cols = [
            "Population R2",
            "Environment-only R2",
            "Full R2",
            "Environment added R2",
            "Population added R2",
            "r Temp after Pop (partial)",
            "p Temp",
            "p Temp (BH-adj)",
            "r Rain after Pop (partial)",
            "p Rain",
            "p Rain (BH-adj)",
            "p F-incr",
            "DW stat",
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
        "r Temp after Pop (partial)",
        "p Temp",
        "p Temp (BH-adj)",
        "r Rain after Pop (partial)",
        "p Rain",
        "p Rain (BH-adj)",
        "p F-incr",
        "DW stat",
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

    # Flag countries with potential autocorrelation (DW < 1.5)
    _dw_flagged = country_screen[country_screen["DW stat"].notna() & (country_screen["DW stat"] < 1.5)]["Country"].tolist()
    _dw_flag_str = ", ".join(_dw_flagged[:10]) + ("…" if len(_dw_flagged) > 10 else "")

    mo.md(f"""
    ### 1.1 Environmental Sensitivity Ranking

    **Strong: {_n_strong} · Moderate: {_n_mod} · Weak / inconclusive: {_n_weak}** countries (of {_n_total} with ≥ {MIN_OBS} obs)

    > **These tiers are a heuristic screening rule, not a formal hypothesis test.** Threshold guide:
    > - **Strong** = partial |r| ≥ {TIER_STRONG_R}, corrected p (BH-adj) < 0.05, ΔR² ≥ {TIER_STRONG_DR2}, AND incremental F-test p < 0.05
    > - **Moderate** = ΔR² ≥ {TIER_STRONG_DR2}, or env R² > pop R², or partial |r| ≥ {TIER_MOD_R} with BH-adjusted p < {TIER_MOD_P}
    > - `r Temp after Pop (partial)` and `r Rain after Pop (partial)` are **true FWL partial correlations**: both the response and each environmental predictor are residualized on ln(Population) before computing Pearson r.
    > - `p Temp (BH-adj)` and `p Rain (BH-adj)` are **corrected p-values (Benjamini-Hochberg FDR)** across all ~{_n_total * 2} simultaneous tests. The Strong and Moderate tier significance tests use these corrected values. Raw p-values are also shown for comparison.
    > - `p F-incr` is the p-value from an incremental F-test (partial F-test) asking whether the environmental variables significantly improve fit beyond the population-only model. The Strong tier requires this p < 0.05.
    > - **Serial autocorrelation warning (Fix 4):** `DW stat` is the Durbin-Watson statistic on the population-model residuals. DW near 2.0 = low autocorrelation. **Countries with DW < 1.5 have positive AR(1) in their production residuals; their raw p-values are overstated and should be interpreted conservatively even after BH correction.** Countries flagged: {_dw_flag_str if _dw_flag_str else "none at DW < 1.5"}.

    The table below ranks countries by how much environmental variables add after population has already been used.

    {mo.as_html(_ranked)}
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    #### How to read the ranking table columns

    | Column | Meaning |
    |---|---|
    | `Population R²` | Variance in ln(Production) explained by ln(Population) alone — the "scale effect" |
    | `Env added R²` | Additional variance explained when temperature and rainfall are added |
    | `p F-incr` | Incremental F-test p-value — is the improvement in fit statistically significant? |
    | `r Temp after Pop (partial)` | True FWL partial correlation: temperature residuals vs. production residuals after removing population from both |
    | `r Rain after Pop (partial)` | Same for rainfall |
    | `p Temp (BH-adj)` / `p Rain (BH-adj)` | BH-corrected p-values — use these, not raw p-values, to judge significance |
    | `DW stat` | Durbin-Watson autocorrelation statistic — values < 1.5 warn of inflated p-values |
    | `Tier` | Heuristic classification: Strong / Moderate / Weak / Population-dominated |
    | `Best env variable` | Which of temperature or rainfall showed a stronger partial signal |
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ## 2. Population-Dominated Countries

    These are countries where the population-only model already explains a large share of production variation and environmental variables add comparatively little. A high Population R² is not a scientific failure — it tells you which question this country best answers in this dataset: the production-at-scale question, not the environmental-sensitivity question.
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

    > **Local only:** The dropdown and interactive plot in this section require a live Marimo
    > kernel. They will not function when viewing this notebook on GitHub Pages — you will see
    > a static snapshot of the last selected country only. To use the explorer, run the notebook
    > locally: `python3 -m marimo edit marimo/environmental_sensitivity_followup.py`
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


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    #### How to read the four-panel country explorer

    Each panel answers a different question about the selected country:

    - **Top-left — Production vs. Population over time:** Are log production and log population co-trending? If they move in parallel, population explains most of the variation.
    - **Top-right — Population-adjusted residual over time:** This is what remains after removing the population trend. A residual above zero means the country produced *more* than population alone predicts that year; below zero means less.
    - **Bottom-left — Residual vs. Temperature:** Does the partial residual correlate with temperature? An upward slope suggests warmer years are associated with higher-than-expected production for this country.
    - **Bottom-right — Residual vs. Rainfall:** Same question for rainfall. If rainfall is fixed (climatological mean), this panel will show a vertical cluster — no year-to-year signal.

    > **Correlation ≠ causation.** A pattern in any panel is a candidate signal for investigation, not a proven mechanism. Temperature could correlate with unmeasured variables (investment cycles, varietal shifts, trade policy) that actually drive production. For countries where rainfall is a fixed climatological mean, the bottom-right panel carries no dynamic signal — see rainfall limitation note in the dataset snapshot.
    """)
    return


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
    ax.set_title(f"Residual vs temperature (partial r = {_meta['r Temp after Pop (partial)']:.3f})")
    ax.set_xlabel("Average temperature (C)")
    ax.set_ylabel("Residual")

    ax = axes_country[1, 1]
    if _d["Rain_mm"].nunique() >= 5:
        ax.scatter(_d["Rain_mm"], _d["prod_resid_after_pop"], color=ACCENT2, alpha=0.85)
        _coef = np.polyfit(_d["Rain_mm"], _d["prod_resid_after_pop"], 1)
        _x = np.linspace(_d["Rain_mm"].min(), _d["Rain_mm"].max(), 100)
        ax.plot(_x, np.polyval(_coef, _x), color="#333333", linestyle="--", linewidth=1.2)
        ax.set_title(f"Residual vs rainfall (partial r = {_meta['r Rain after Pop (partial)']:.3f})")
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

    > **Selection-bias note (Fix 5):** This cohort was identified in §1 based on strong environmental signal. The regression below will tend to show larger coefficients and smaller p-values for these countries than the full panel — this is partly by construction, not independent confirmation. The cohort was selected from the same data being re-analyzed, so finding that environmental variables are more significant in the cohort is a tautological result. The full-panel comparison is included specifically to show the magnitude of this selection effect; it does not validate the §1 screening result.

    Rainfall is decomposed into a between-country structural mean and a within-country annual deviation — matching the main workbook §3 specification (see main workbook Note 16).
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

    _n_full_countries = int(_full_df["ISO3"].nunique())
    _n_cand_countries = int(_cand_df["ISO3"].nunique())
    _label_full = f"Full panel (n={_n_full_countries} countries)"
    _label_cand = f"Candidate cohort (n={_n_cand_countries} countries, selected for environmental signal)"

    _rows = []
    cohort_models = []

    for _label, _df in [(_label_full, _full_df), (_label_cand, _cand_df)]:
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

    > Rainfall is decomposed into a between-country structural mean (`Rain_mm_country_mean`) and a within-country annual deviation (`Rain_mm_within`), matching the main workbook's specification.
    > **Interpreting this table:** The candidate cohort row will typically show lower p-values and higher R² for environmental variables by construction — these countries were selected in §1 precisely because they exhibited strong environmental association. This is a descriptive comparison showing the magnitude of the selection effect, not independent confirmation of the §1 screening result. See the selection-bias note at the top of §4.
    """)
    return (cohort_models,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    #### How to read the cohort coefficient comparison

    The plot compares regression coefficients between the full panel and the candidate cohort:

    - **Dots to the right of zero:** positive association with ln(Production) — the variable is linked to higher production
    - **Whiskers crossing zero:** the coefficient is not distinguishable from zero at α ≈ 0.05 (95% CI)
    - **Two colors / groups:** full-panel estimates vs. candidate-cohort estimates — if cohort coefficients are larger, the screening step identified a subgroup where environmental effects are more pronounced

    > **Selection note:** The cohort was chosen in §1 for strong environmental signal. Larger coefficients here are partly by construction — this comparison measures the *size* of the selection effect, not independent confirmation of the environmental signal. See main workbook §3–§4 for the formal inference.
    """)
    return


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
    # Assign offsets and colors by position so dynamic label strings (which include country counts) work
    _unique_samples = list(_coef_df["Sample"].unique())
    _offset_list = [-0.17, 0.17]
    _color_list  = [ACCENT, ACCENT2]

    for _i, _sample in enumerate(_unique_samples):
        _sub = _coef_df[_coef_df["Sample"] == _sample].set_index("Term").loc[_terms].reset_index()
        _y = [v + _offset_list[_i % len(_offset_list)] for v in range(len(_terms))]
        _xerr = [
            _sub["coef"].values - _sub["lo"].values,
            _sub["hi"].values - _sub["coef"].values,
        ]
        ax_coef_compare.errorbar(
            _sub["coef"],
            _y,
            xerr=_xerr,
            fmt="o",
            color=_color_list[_i % len(_color_list)],
            capsize=4,
            label=_sample,
        )

    ax_coef_compare.axvline(0, color="#777777", linestyle="--", linewidth=1)
    ax_coef_compare.set_yticks(range(len(_terms)))
    ax_coef_compare.set_yticklabels(_terms)
    ax_coef_compare.set_xlabel("Coefficient estimate with 95% CI")
    ax_coef_compare.set_title("Full panel vs candidate cohort (selected for environmental signal)")
    ax_coef_compare.legend(fontsize=8)
    plt.tight_layout()

    mo.mpl.interactive(fig_coef_compare)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ## 5. Individual Country Mini-Models

    For the strongest countries, fit a small country-specific model. These models are useful for interpretation, but each country has only about 30 observations, so treat them as case-study evidence.

    > **Mini-model limitations:**
    > - **Small n per country (~15–30 rows):** OLS coefficients can be volatile — one unusual year can shift the estimate substantially
    > - **No year fixed effects:** global time trends (e.g., oil price rises 1995–2008) may appear as production trends within a country
    > - **Rainfall in mini-models:** Within a single country there is no between-country variation, so raw `Rain_mm` is used directly (no decomposition needed). Where rainfall has too few unique values, the mini-model uses population and temperature only.
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
    #### How to read the mini-model table

    | Column | Meaning |
    |---|---|
    | `n` | Country-year observations in the fit |
    | `Rain included?` | Whether Rain_mm had sufficient year-to-year variation to include |
    | `R²` / `Adj R²` | Explained-variance summary — see main workbook Note 17 |
    | `Temp coef` / `Rain coef` | OLS coefficient: estimated change in ln(Production) per one-unit increase in the predictor, holding others constant |
    | `Temp p` / `Rain p` | p-value for H₀: β = 0; small p + large coefficient = strongest signal |

    > A small Adj R² with a significant predictor is common at n ≈ 15–30 — it means the predictor is detectable but the model explains only part of the country's production story. Cross-reference with the §1 ranking table for that country's DW stat before concluding.
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

    > **Hand-off to the main workbook:** Tier assignments and country rankings here are candidate-selection signals, not statistical conclusions. For formal H₀/H₁ conclusions with INEG teacher-phrasing, see `coffee_analysis.py` §2–§5.
    """)
    return


if __name__ == "__main__":
    app.run()
