# Spec: Date Filter for Profile Page

## Overview

This feature adds a date filter bar above the transaction history on the profile page, allowing users to filter their expenses by a date range. The filter bar includes quick preset buttons (This Week, This Month, This Year, All Time) and a custom date range form with From and To date inputs. When a filter is applied, only transactions within the selected date range are shown, and all summary stats (total spent, transaction count, top category, category breakdown) are recalculated for that filtered range. The filter state is communicated to the server via URL query parameters (`?start=YYYY-MM-DD&end=YYYY-MM-DD`), so filtered views are shareable and the browser back/forward buttons work correctly.

## Depends on

- Step 01: Database setup — the `users` and `expenses` tables must exist with `date` column.
- Step 02: Registration — user accounts must be creatable.
- Step 03: Login + Logout — session state must support authenticated flows.
- Step 04: Profile page static UI — the template layout with all sections must exist.
- Step 05: Backend connection — `database/queries.py` query helpers and the `/profile` route must be wired to real data.

## Routes

- `GET /profile` — render the profile page with optional date filter — **logged-in only** (redirect to `/login` if no `session["user_id"]`)

No new routes. The existing `GET /profile` route is extended to accept `start` and `end` query parameters.

## Database changes

No database changes. The existing `expenses` table already has a `date` column (TEXT, ISO format `YYYY-MM-DD`) with an index `idx_expenses_user_date` on `(user_id, date)`. All filtering can be done with parameterized SQL using `WHERE date >= ? AND date <= ?`.

## Templates

- **Modify**: `templates/profile.html`
  - Add a filter bar section above the transaction history table, containing:
    - Preset buttons: "This Week", "This Month", "This Year", "All Time"
    - A custom date range form with two `<input type="date">` fields (From, To) and an "Apply" button
    - The active filter state is visually indicated (active preset button highlighted)
  - All four existing sections (user info card, summary stats, transaction history, category breakdown) must reflect the filtered data when a date filter is active
  - When no transactions match the filter, show an empty-state message ("No transactions in this date range") inside the table body area instead of rendering rows
  - Preset buttons and the form must use `url_for()` or Jinja `request.args` to build filter URLs — never hardcode query strings

## Files to change

- `app.py` — modify the `profile()` view function to:
  - Read `start` and `end` from `request.args.get("start")` and `request.args.get("end")`
  - Validate date strings (must be valid `YYYY-MM-DD` or empty/None — invalid values are ignored)
  - Pass `start` and `end` (or None) to the query helpers in `database/queries.py`
  - Pass filter context (`start`, `end`, active preset name) to the template for rendering

- `database/queries.py` — modify existing query helpers to accept optional `start_date` and `end_date` parameters:
  - `get_summary_stats(user_id, start_date=None, end_date=None)` — add `WHERE` clause filtering on `date` when dates are provided
  - `get_recent_transactions(user_id, limit=10, start_date=None, end_date=None)` — add `WHERE` clause filtering on `date`
  - `get_category_breakdown(user_id, start_date=None, end_date=None)` — add `WHERE` clause filtering on `date`

- `templates/profile.html` — add filter bar markup and empty-state handling (as described above)

- `static/js/main.js` — add vanilla JS to:
  - Compute and set the date values for preset buttons (This Week = Monday to today, This Month = 1st to today, This Year = Jan 1 to today) on page load
  - Optionally highlight the active preset based on URL query params

## Files to create

No new files.

## New dependencies

No new dependencies. The feature uses only Flask, Jinja2, sqlite3 (standard library), and vanilla JavaScript — no new pip packages.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — never string-format values into SQL; always use `?` placeholders
- Passwords hashed with `werkzeug.security.generate_password_hash` (no changes to auth in this step)
- Use CSS variables — never hardcode hex values in templates or CSS
- All templates extend `base.html`
- No inline `<style>` tags — page-specific styles go in `static/css/profile.css`
- No inline `style=""` attributes in templates — use CSS classes instead
- Currency must always display as ₹ — never £ or $
- The filter bar preset buttons must use `url_for()` or Jinja `request.args` to build URLs — never hardcode query strings like `?start=2026-01-01`
- Date inputs use `type="date"` with ISO format `YYYY-MM-DD` — the browser date picker handles formatting
- All filter values passed to SQL must be validated as `YYYY-MM-DD` format before use; invalid or missing values are treated as "no filter" (show all)
- The `idx_expenses_user_date` index already exists — filtering should use it for performance
- Empty results (no transactions in range) must show a user-friendly message, not a blank table
- The profile page must still render correctly with no query parameters (default = show all transactions)
- Use `url_for()` for every internal link — never hardcode URLs

## Definition of done

- [ ] Visiting `/profile` without query params shows all transactions (default behavior unchanged)
- [ ] Clicking "This Week" preset filters transactions to the current week (Monday through today)
- [ ] Clicking "This Month" preset filters transactions to the current month (1st through today)
- [ ] Clicking "This Year" preset filters transactions to the current year (Jan 1 through today)
- [ ] Clicking "All Time" preset clears the filter and shows all transactions
- [ ] Entering custom From and To dates in the form and clicking "Apply" filters transactions to that range
- [ ] Summary stats (total spent, transaction count, top category) update to reflect the filtered date range
- [ ] Category breakdown percentages recalculate for the filtered data and still sum to 100%
- [ ] When no transactions match the filter, an empty-state message is displayed instead of a blank table
- [ ] The active preset button is visually highlighted (different style from inactive buttons)
- [ ] All amounts on the page display the ₹ symbol
- [ ] Invalid date inputs (e.g. `?start=garbage`) are gracefully ignored and all transactions are shown
- [ ] The page renders correctly in both light and dark color themes (respecting `prefers-color-scheme`)
- [ ] No hardcoded URLs appear in the template — all links use `url_for()`
- [ ] No inline `style=""` attributes appear in the template — all styling uses CSS classes
- [ ] No hex colour values appear in `profile.html` — only CSS variables
- [ ] Browser back/forward buttons correctly navigate between filtered views