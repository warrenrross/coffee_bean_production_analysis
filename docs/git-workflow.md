# Git Workflow

This project uses a layered toolchain to keep notebooks clean in version control while supporting both interactive (Jupyter) and reactive (Marimo) development paths.

---

## Toolchain Overview

| Tool | Role |
|---|---|
| **nbstripout** | Strips cell outputs and execution counts from `.ipynb` before commit — keeps diffs readable |
| **Jupytext** | Syncs `.ipynb` ↔ `.py` (percent format) ↔ `.md` — enables line-level diffs and editor-based editing |
| **nbdime** | Notebook-aware `git diff` and `git merge` for `.ipynb` — resolves structure-level conflicts |
| **Marimo** | Reactive notebook framework; source files are plain `.py` — fully version-controllable without any stripping |
| **pre-commit** | Runs Jupytext sync and Marimo export validation on every commit |
| **GitHub Actions** | Publishes Marimo notebooks to GitHub Pages on push to `main` |

---

## One-Time Setup

```bash
pip install marimo jupytext nbdime nbstripout pre-commit

# Configure nbstripout for this repo
nbstripout --install

# Configure nbdime git integration
nbdime config-git --enable

# Install pre-commit hooks
pre-commit install
```

---

## Daily Jupyter Workflow

**Edit a notebook:**
```bash
jupyter lab notebooks/<name>.ipynb
```

Jupytext automatically keeps `scripts/<name>.py` and `docs/<name>.md` in sync as you save.

**Before committing:** nbstripout removes outputs automatically via the `.gitattributes` filter. Nothing to do manually.

**Stage and commit:**
```bash
git add notebooks/<name>.ipynb scripts/<name>.py
git commit -m "describe what changed"
```

The pre-commit hook runs `jupytext --sync` to ensure the `.py` and `.md` representations are current before the commit completes.

**View a notebook diff:**
```bash
nbdiff notebooks/<name>.ipynb
# or for staged changes:
nbdiff --staged notebooks/<name>.ipynb
```

---

## Daily Marimo Workflow

Marimo notebooks live in `marimo/` as plain `.py` files. They require no stripping or syncing — they are already clean Python.

**Edit and run:**
```bash
marimo edit marimo/coffee_analysis.py
```

**Stage and commit:**
```bash
git add marimo/coffee_analysis.py
git commit -m "describe changes"
```

The pre-commit hook validates that the notebook can export to HTML before the commit is accepted:
```
Checking marimo/coffee_analysis.py...
```

If the export check fails, fix the notebook error before committing.

**Preview the published output locally:**
```bash
marimo export html marimo/coffee_analysis.py -o /tmp/preview.html
open /tmp/preview.html
```

---

## Publishing to GitHub Pages

Pushing any change to `marimo/` on `main` triggers the GitHub Actions workflow at `.github/workflows/publish.yml`.

The workflow:
1. Checks out the repository
2. Installs Python dependencies
3. Exports each `marimo/*.py` to `docs/site/<name>.html`
4. Generates an `index.html` listing all notebooks
5. Deploys `docs/site/` to GitHub Pages via `actions/deploy-pages`

The `docs/site/` directory is gitignored — do not commit HTML files manually.

To trigger a deploy without a code change: go to Actions → Publish Marimo Notebooks to GitHub Pages → Run workflow.

---

## Directory Conventions

```
marimo/        ← primary: edit here for publication
notebooks/     ← exploratory Jupyter work; Jupytext-synced
scripts/       ← auto-generated from notebooks/ by Jupytext; do not edit directly
docs/          ← auto-generated .md from notebooks/ + hand-written docs; do not edit .md synced files directly
figures/       ← exported PNGs, named <notebook>_<description>.png
data/          ← tracked processed CSVs only (see data/README.md)
```

---

## Merge Conflicts in Notebooks

If a merge conflict occurs in a `.ipynb` file:

```bash
# Use nbdime to merge
nbdime mergetool <base.ipynb> <local.ipynb> <remote.ipynb> -o <output.ipynb>
```

For Marimo `.py` files, standard Git text merge applies.

---

## Updating Pre-Commit Hooks

To update Jupytext to a newer version, edit `.pre-commit-config.yaml` and change the `rev:` field, then run:

```bash
pre-commit autoupdate
pre-commit run --all-files   # validate everything passes
```
