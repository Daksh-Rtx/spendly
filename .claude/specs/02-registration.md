# Spec: Registration

## Overview

Enable new users to create a Spendly account by submitting name, email, and
password through the existing `register.html` form. This step wires up the
`POST /register` handler that the template already targets, validates the
input, hashes the password with werkzeug, stores the user in the `users`
table, and redirects authenticated users to the dashboard once that step
exists.

## Depends on

- Step 1 (database setup) — `users` table schema and `get_db()` helper must
  be complete and correct.

## Routes

- `GET /register` — render registration form — public
- `POST /register` — validate input, create user, redirect to login — public

No new routes beyond the `POST /register` handler.

## Database changes

No database changes. The `users` table already exists with the required
columns (`id`, `name`, `email`, `password_hash`, `created_at`).

## Templates

- Modify: `templates/register.html` — the form already posts to `/register`
  with `method="POST"`; add an error block if validation fails and keep the
  existing fields.

## Files to change

- `app.py` — add `POST /register` handler
- `templates/register.html` — ensure error display is supported

## Files to create

- None

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend base.html
- `GET /register` must remain a plain render (no auth required)
- `POST /register` must reject duplicate emails with a clear error
- Minimum password length: 8 characters
- Use `abort()` for HTTP errors, not bare string returns
- Redirect on success — never render a template with a flash message

## Definition of done

- [ ] `GET /register` still renders the form
- [ ] `POST /register` with valid data creates a user and redirects
- [ ] `POST /register` with a duplicate email shows an error
- [ ] `POST /register` with a short password shows an error
- [ ] Stored password is a werkzeug hash, not plaintext
- [ ] App runs without errors on port 5001