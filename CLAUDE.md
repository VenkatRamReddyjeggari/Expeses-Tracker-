# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Spendly**: a Flask + SQLite personal expense tracker (amounts are in rupees). It's a step-by-step learning project. Most of it is scaffolding, and features are added in numbered "Steps" that are referenced in placeholder code (Step 1 is DB setup, Step 3 logout, Step 4 profile, Steps 7–9 add/edit/delete expenses).

## Commands

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python app.py                      # dev server with debug on http://localhost:5001
pytest                             # run tests (pytest + pytest-flask; no tests exist yet)
pytest path/to/test_file.py::test_name   # run a single test
```

There's no linter or build step.

## Architecture

- `app.py`: the single Flask app module. It holds every route, with no blueprints or app factory. `landing`, `register` and `login` render templates. `logout`, `profile` and the `/expenses/...` routes return placeholder strings until their Step is implemented. All routes are currently GET only, but `login.html` and `register.html` already POST to `/login` and `/register`, so implementing auth means adding `methods=["GET", "POST"]`.
- `database/db.py`: a stub to be written in Step 1. It should expose `get_db()` (a SQLite connection with `row_factory` set and `PRAGMA foreign_keys` on), `init_db()` (`CREATE TABLE IF NOT EXISTS ...`) and `seed_db()`. The DB file is `expense_tracker.db`, which is gitignored.
- `templates/`: Jinja templates extend `base.html`, which provides the navbar/footer and these blocks: `title`, `head`, `content`, `scripts`. Auth templates render an optional `error` variable. Use `url_for(...)` for links.
- `static/css/style.css`: the whole design system, built on CSS custom properties in `:root` (`--ink*`, `--paper*`, `--accent`, `--accent-2`, `--danger`, radii, fonts DM Serif Display / DM Sans). Reuse these variables and the existing class names (`btn-primary`, `auth-*`, `hero-*`) rather than adding new colors.
- `static/js/main.js`: an empty placeholder, loaded on every page.
