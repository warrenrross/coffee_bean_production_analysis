# Fix: `corr_df` NameError in `marimo/coffee_analysis.py`

## Root Cause

The cell that computes `corr_df` (around line 350) wraps everything in an inner `_()` function:

```python
@app.cell
def _(mo, np, panel, pd, stats):
    def _():
        ...
        corr_df = pd.DataFrame(corr_rows)
        ...
        return mo.md(...)

    _()
    return          # ← returns nothing; corr_df is trapped inside _()
```

Marimo builds a reactive DAG by inspecting what each cell **returns**. Because `corr_df` is created inside the inner `_()` and the outer cell returns nothing, Marimo never registers `corr_df` as an available variable. The downstream cell that declares `def _(corr_df, mo, pd):` then raises `NameError: name 'corr_df' is not defined`.

The inner-function pattern (`def _(): ... _()`) is a Marimo idiom for hiding intermediate variables from the DAG — it was used correctly for display-only intermediates, but was incorrectly applied to a cell that also needs to *export* `corr_df`.

---

## Fix: Split the Cell in Two

Replace the single wrapped cell with **two cells**:

### Cell A — Compute only, return `corr_df`

```python
@app.cell
def _(np, panel, pd, stats):
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
            _corr_rows.append({
                "Predictor":   _pred_label,
                "Response":    _resp_label,
                "n":           _n,
                "r":           _r,
                "T₀":          _t0,
                "df":          _n - 2,
                "p-value":     _p,
                "Reject H₀?":  "Yes ✓" if _reject else "No ✗",
                "Conclusion":  (
                    f"Significant {'positive' if _r > 0 else 'negative'} linear relationship (α=0.05)"
                    if _reject else
                    "Insufficient evidence to reject H₀ (α=0.05)"
                ),
            })

    corr_df = pd.DataFrame(_corr_rows)
    return (corr_df,)
```

**Key changes from the broken version:**
- No inner `_()` wrapper
- All intermediates prefixed with `_` so they are DAG-private
- `corr_df` (no underscore) is exported via `return (corr_df,)`

### Cell B — Display only, takes `corr_df` as input

```python
@app.cell
def _(corr_df, mo):
    _display = corr_df.copy()
    _display["r"]       = _display["r"].map(lambda x: f"{x:.4f}")
    _display["T₀"]      = _display["T₀"].map(lambda x: f"{x:.3f}")
    _display["p-value"] = _display["p-value"].map(lambda x: f"{x:.4f}" if x >= 0.0001 else "< 0.0001")
    return mo.md(
        f"""
        ### 2.1 Pearson Correlation Results (8 tests)

        {mo.as_html(_display[["Predictor","Response","n","r","T₀","df","p-value","Reject H₀?","Conclusion"]])}
        """
    )
```

---

## Location in File

| Item | Approx. line |
|---|---|
| Broken cell to replace | 350–406 |
| Downstream consumer of `corr_df` (already correct) | 717–745 |

The downstream cell (`def _(corr_df, mo, pd):`) does **not** need to change — once Cell A above returns `corr_df`, Marimo will wire it up automatically.

---

## General Rule

In Marimo, use the inner-function pattern only for cells that are **purely display** (no downstream consumers). Any cell that needs to export a variable to another cell must return that variable from the **outer** `def _(...):` function. Prefix all DAG-private intermediates with `_` to keep the namespace clean.
