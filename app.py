import re
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for

from database.db import (
    close_db,
    create_user,
    get_db,
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
    verify_password,
)
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id as get_user_profile,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

# Register teardown so the SQLite connection is closed after each request.
app.teardown_appcontext(close_db)

# Initialise the database schema and seed sample data on startup.
with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Authentication helpers                                              #
# ------------------------------------------------------------------ #

def login_required(view_func):
    """Protect a route — redirect to /login if no user is in session."""

    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash("Please log in first.")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped_view


def guest_only(view_func):
    """Redirect logged-in users away from guest-only pages (login, register)."""

    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if g.user is not None:
            return redirect(url_for("profile"))
        return view_func(*args, **kwargs)

    return wrapped_view


@app.before_request
def load_user():
    """Load the current user from the session into ``g.user`` for every request."""
    g.user = None
    user_id = session.get("user_id")
    if user_id is not None:
        g.user = get_user_by_id(user_id)


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_date(value):
    """Return *value* if it is a valid ``YYYY-MM-DD`` string, otherwise ``None``.

    If *value* is empty/None or not a valid ISO date, returns ``None`` (means
    "show all transactions").  This prevents garbage from being passed to SQL.
    """
    if not value:
        return None
    if not _DATE_RE.match(value):
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
    return value


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
@guest_only
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validate all fields are present
        if not name or not email or not password or not confirm_password:
            flash("All fields are required.")
            return render_template("register.html")

        # Validate password confirmation
        if password != confirm_password:
            flash("Passwords do not match.")
            return render_template("register.html")

        # Validate minimum password length
        if len(password) < 8:
            flash("Password must be at least 8 characters.")
            return render_template("register.html")

        # Check for duplicate email
        existing = get_user_by_email(email)
        if existing:
            flash("Email is already registered.")
            return render_template("register.html")

        # Create the user
        create_user(name, email, password)
        flash("Account created successfully! Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
@guest_only
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        # Validate both fields are present
        if not email or not password:
            flash("Email and password are required.")
            return render_template("login.html")

        # Look up the user by email
        user = get_user_by_email(email)
        if user is None:
            flash("Invalid email or password.")
            return render_template("login.html")

        # Verify the password against the stored hash
        if not verify_password(password, user["password_hash"]):
            flash("Invalid email or password.")
            return render_template("login.html")

        # Sign the user in
        session["user_id"] = user["id"]
        flash(f"Welcome back, {user['name']}!")
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("landing"))


@app.route("/profile")
@login_required
def profile():
    user = get_user_profile(g.user["id"])
    if user is None:
        flash("User not found.")
        return redirect(url_for("login"))

    # Optional date filter — ?start=YYYY-MM-DD&end=YYYY-MM-DD (inclusive range).
    start = _parse_date(request.args.get("start"))
    end = _parse_date(request.args.get("end"))

    stats = get_summary_stats(g.user["id"], start_date=start, end_date=end)
    transactions = get_recent_transactions(
        g.user["id"], limit=10, start_date=start, end_date=end
    )
    # Map query helper's `amount` key to the template's expected `total` key.
    categories = [
        {"name": c["name"], "total": c["amount"], "percent": c["pct"]}
        for c in get_category_breakdown(g.user["id"], start_date=start, end_date=end)
    ]

    # Compute preset URLs and the active preset for the filter bar.
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday of this week
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    preset_urls = {
        "this_week": url_for(
            "profile", start=week_start.isoformat(), end=today.isoformat()
        ),
        "this_month": url_for(
            "profile", start=month_start.isoformat(), end=today.isoformat()
        ),
        "this_year": url_for(
            "profile", start=year_start.isoformat(), end=today.isoformat()
        ),
        "all_time": url_for("profile"),
    }

    active_preset = None
    if start is None and end is None:
        active_preset = "all_time"
    elif start == week_start.isoformat() and end == today.isoformat():
        active_preset = "this_week"
    elif start == month_start.isoformat() and end == today.isoformat():
        active_preset = "this_month"
    elif start == year_start.isoformat() and end == today.isoformat():
        active_preset = "this_year"

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        start=start,
        end=end,
        preset_urls=preset_urls,
        active_preset=active_preset,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
