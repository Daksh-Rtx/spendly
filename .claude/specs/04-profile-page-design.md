# Spec: Profile Page

## Overview

This feature replaces the `/profile` stub with a fully designed profile page showing static, hardcoded data. The goal is to establish the complete UI layout — user info card, transaction history table, summary stats, and category breakdown — before any real database queries are wired up in a future step. Building the UI first lets the team validate the design in isolation and ensures the templates are ready for the backend-connection step.

## Depends on

- Step 01: Database setup — the `users` and `expenses` tables must exist.
- Step 02: Registration — user accounts must be creatable; session state must support authenticated vs. unauthenticated flows.
- Step 03: Login + Logout — a session must be established (`session["user_id"]`) and the `login_required` decorator must be available to protect the route.

## Routes

- `GET /profile` — render the profile page — **logged-in only** (redirect to `/login` if no `session["user_id"]`)

## Database changes

No database changes. The existing `users` and `expenses` tables are sufficient. All data passed to the template in this step will be hardcoded Python structures; no new tables or columns are needed.

## Templates

- **Create**: `templates/profile.html` — full profile page extending `base.html`; contains four sections:
  1. **User info card** — avatar initials, name, email, member-since date (all hardcoded)
  2. **Summary stats row** — total spent, number of transactions, top category (hardcoded)
  3. **Transaction history table** — list of recent expenses with date, description, category badge, amount (hardcoded rows)
  4. **Category breakdown** — per-category totals displayed as a simple list or progress-bar rows (hardcoded)

## Files to change

- `app.py` — replace the `/profile` stub view function with a real view that:
  - Checks `session.get("user_id")` and redirects to `url_for("login")` if absent (authentication guard)
  - Passes hardcoded context variables to `profile.html` (no DB queries in this step)

## Files to create

- `templates/profile.html` — new template file extending `base.html`

## New dependencies

No new dependencies. The feature uses only Flask, Jinja2, sqlite3 (standard library), and `werkzeug.security` (already installed).

## Rules for implementation

- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()` if any DB call is ever needed
- Parameterised queries only — never string-format SQL
- Passwords hashed with `werkzeug.security.generate_password_hash` (no changes to auth in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles in templates
- Authentication guard: check `session.get("user_id")`; if absent, `redirect(url_for("login"))`
- All data passed to the template must be hardcoded Python dicts/lists in `app.py` — no DB queries in this step
- Category badges must use a CSS class, not inline colour styles
- Use `url_for()` for every internal link — never hardcode URLs

## Definition of done

- [ ] Visiting `/profile` without being logged in redirects to `/login`
- [ ] Visiting `/profile` while logged in returns HTTP 200
- [ ] The page displays a user info card with a name and email
- [ ] The page displays at least three summary stat values (e.g. total spent, transaction count, top category)
- [ ] The page displays a transaction history table with at least three hardcoded rows
- [ ] The page displays a category breakdown section with at least three categories
- [ ] The navbar shows the logged-in state (username + logout link) when logged in, and "Login"/"Register" when logged out
- [ ] No hex colour values appear in `profile.html` — only CSS variables
- [ ] The page renders correctly in both light and dark color themes (respecting `prefers-color-scheme`)