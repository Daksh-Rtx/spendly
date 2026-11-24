# Spec: Login and Logout

## Overview

Implement user authentication so registered users can sign in and out of Spendly. This step upgrades the existing stub `GET /login` route into a fully functional form that accepts a POST, verifies credentials against the `users` table, and establishes a Flask session. It also implements the `GET /logout` stub to clear the session and redirect to the landing page. A `login_required` decorator is added to protect future authenticated routes. This is the gateway feature — all subsequent steps (profile, expenses) depend on a working session.

## Depends on

- Step 01 – Database setup (`users` table, `get_db()`, `init_db()`, `seed_db()`)
- Step 02 – Registration (`create_user()`, `verify_password()`, registration flow working)

## Routes

- `GET /login` – render login form — public (already exists as stub, upgrade it)
- `POST /login` – process login form, verify credentials, establish session, redirect to `/` — public
- `GET /logout` – clear session, redirect to `/` — logged-in (upgrade stub)

No other new routes. The landing page (`/`) remains public but will show user-specific nav once logged in.

## Database changes

No new tables or columns. The existing `users` table (`id`, `name`, `email`, `password_hash`, `created_at`) covers all requirements.

A new DB helper must be added to `database/db.py`:
- `get_user_by_id(user_id)` – returns the user row matching `id`, or `None` if not found. Used by `login_required` to load the current user from the session.

## Templates

- **Modify**: `templates/login.html`
  - Change the form `action` to `url_for('login')` with `method="post"`
  - Add `name` attributes to inputs: `email`, `password`
  - Add a block to display a flash error message (e.g. "Invalid email or password")
  - Keep all existing visual design

- **Modify**: `templates/base.html`
  - Update navigation: show "Login" / "Register" when logged out; show "Profile" / "Logout" when logged in
  - Add `user` to template context (available globally via `g.user` or similar pattern)

## Files to change

- `app.py` – upgrade `login()` to handle `GET` and `POST`; implement `logout()`; add `login_required` decorator; add `before_request` to load `g.user` from session
- `database/db.py` – add `get_user_by_id(user_id)` helper
- `templates/login.html` – wire up form action/method and flash message display
- `templates/base.html` – conditional nav based on login state

## Files to create

None.

## New dependencies

No new dependencies. Uses:
- `werkzeug.security` (already installed) — for `check_password_hash` via `verify_password()`
- Flask built-ins: `session`, `g`, `flash`, `redirect`, `url_for`, `request`
- `functools.wraps` (standard library) — for the `login_required` decorator

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never use f-strings in SQL
- Passwords verified with `werkzeug.security.check_password_hash` via the existing `verify_password()` helper — never compare plaintext
- Flask session cookie: `app.secret_key` is already set in `app.py` (dev string); sessions are signed cookies, not server-side
- Server-side validation on login POST:
  1. Both email and password are non-empty
  2. Email exists in `users` table
  3. Password matches the stored hash (via `verify_password()`)
- On any validation failure, re-render the form with a flashed error message — do not redirect
- On success: set `session['user_id'] = user['id']`, `flash` a welcome message, `redirect` to `url_for('landing')`
- `logout()` clears `session` and redirects to `url_for('landing')`
- `login_required` decorator: if `g.user` is not set, `flash` "Please log in first." and `redirect` to `url_for('login')`
- `before_request` loads `g.user` by calling `get_user_by_id(session['user_id'])` if `user_id` is in session; handles missing/invalid user gracefully
- Use `abort(405)` if an unsupported HTTP method reaches the route
- All templates extend `base.html`
- Use CSS variables — never hardcode hex values
- Use `url_for()` for every internal link — never hardcode URLs

## Definition of done

- [ ] `GET /login` renders the login form without errors
- [ ] Submitting the form with valid credentials sets `session['user_id']`, flashes "Welcome back, {name}!", and redirects to `/`
- [ ] Submitting with an unknown email re-renders the form with "Invalid email or password" error
- [ ] Submitting with a known email but wrong password re-renders the form with "Invalid email or password" error
- [ ] Submitting with any empty field re-renders the form with a validation error
- [ ] `GET /logout` clears the session, flashes "You have been logged out.", and redirects to `/`
- [ ] After logging out, visiting `/profile` (stub) redirects to `/login` with a flash message
- [ ] `base.html` nav shows "Profile" and "Logout" when logged in; "Login" and "Register" when logged out
- [ ] `g.user` is available in all templates after login (e.g., can display `{{ g.user.name }}` in base nav)
- [ ] No plaintext passwords anywhere — verified by inspecting `spendly.db`
- [ ] App starts without errors on port 5001