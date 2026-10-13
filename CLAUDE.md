# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Spendly**: a Flask + SQLite personal expense tracker (amounts are in rupees). It began as a step-by-step learning project; Steps 1–9 (DB setup, register/login/logout, profile, add/edit/delete expenses) are implemented. The GitHub remote is `VenkatRamReddyjeggari/Expeses-Tracker-`.

The parent directory is named `practise ` with a **trailing space**, so always quote paths (`cd ~/"practise /expense-tracker"`).

## Commands

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python app.py                      # dev server with debug + reloader on http://localhost:5001
pytest                             # pytest + pytest-flask are installed, but no tests exist yet
pytest path/to/test_file.py::test_name   # run a single test
```

There's no linter or build step. Demo login (seeded into an empty DB): `demo@spendly.com` / `demo123`. To reset data, delete `expense_tracker.db` and restart; it is recreated on import.

## Architecture

- `app.py` is the single Flask module: every route, no blueprints or app factory. Importing it runs `init_db()` and `seed_db()`, so the DB exists as soon as the app loads (dev server or WSGI).
- **Auth** is session-based: `session["user_id"]` and `session["user_name"]` are set on login/register, and `base.html` reads `session` directly to switch the navbar. Protect routes with the `@login_required` decorator in `app.py`. `secret_key` comes from the `SPENDLY_SECRET_KEY` env var (with an insecure dev fallback); the session cookie is `SameSite=Lax`, which is the only CSRF protection, so state-changing routes must be POST-only (delete is POST-only for this reason).
- **Password hashing must pass `method="pbkdf2:sha256"`**. The local venv runs macOS's Python 3.9, whose `hashlib` lacks `scrypt` (Werkzeug's default), and `generate_password_hash` crashes without it.
- **Ownership checks**: every expense query filters on both `id` and `user_id = session["user_id"]`, and a miss returns `abort(404)` (not 403), so other users' ids are indistinguishable from missing ones. Keep this in any new expense query.
- **Expense forms**: add and edit share `templates/expense_form.html` (the `editing` flag switches title/button text) and the `parse_expense_form()` validator, which returns `(values, error)`; on error the route re-renders with the submitted `values` and status 400. Valid categories are the `CATEGORIES` list in `app.py`; amounts are capped by `MAX_AMOUNT`.
- `database/db.py`: `get_db()` returns a new SQLite connection per call (`sqlite3.Row`, foreign keys on) that routes close themselves; there's no request-scoped `g` connection. Tables are `users` (email unique, stored lowercased) and `expenses` (`ON DELETE CASCADE` to users, `amount > 0`, `date` as `YYYY-MM-DD` text). Schema changes go in `init_db()`'s `CREATE TABLE IF NOT EXISTS`; there are no migrations, so altering an existing table needs a manual step or a fresh DB.
- **Templates** extend `base.html` (blocks: `title`, `head`, `content`, `scripts`), which also renders `flash()` messages under the navbar. Format money with the `inr` Jinja filter (Indian digit grouping: `1,23,456.50`), defined in `app.py` as `format_inr`.
- `static/css/style.css` is the whole design system, built on CSS custom properties in `:root` (`--ink*`, `--paper*`, `--accent`, `--accent-2`, `--danger`, radii, fonts DM Serif Display / DM Sans). Reuse these variables and existing classes (`btn-primary`, `btn-ghost`, `auth-*`, `form-input`, `mock-bar*`, `profile-*`) rather than adding new colors. Responsive overrides live in the media queries at the end of the file.
- `static/js/main.js` is loaded on every page. It holds one global handler: any `<form data-confirm="...">` asks for confirmation before submitting.

## Deployment

The intended host is PythonAnywhere (manual WSGI config that sets `SPENDLY_SECRET_KEY` and does `from app import app as application`); SQLite persists there. Updating the live site means `git pull` in its console and pressing Reload on the Web tab.
