"""Spec-based pytest tests for the profile-page date filter feature.

Spec under test: .claude/specs/06-date-filter-for-profile-page.md

The feature lets a logged-in user filter the profile page (summary stats,
transaction history and category breakdown) to an inclusive date range via the
``?start=YYYY-MM-DD&end=YYYY-MM-DD`` query parameters. Invalid / missing dates
are ignored, preset ranges (This Week / This Month / This Year / All Time) are
just pre-computed start/end pairs, and an empty result set must show the
"No transactions in this date range" message.
"""

import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

# Ensure the project root (which contains app.py) is on sys.path so that
# ``from app import app`` works when pytest is invoked from any cwd.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app  # noqa: E402
from database.db import get_db  # noqa: E402
from database.queries import (  # noqa: E402
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
)


DEMO_EMAIL = "demo@spendly.com"

# The 8 seeded demo expenses (all in November 2026) as (date, description).
SEED_TRANSACTIONS = [
    ("2026-11-01", "Lunch at cafe"),
    ("2026-11-02", "Metro pass recharge"),
    ("2026-11-03", "Electricity bill"),
    ("2026-11-04", "Dental cleaning"),
    ("2026-11-05", "Movie tickets"),
    ("2026-11-06", "Groceries"),
    ("2026-11-07", "Gift for friend"),
    ("2026-11-08", "Morning coffee"),
]

ALL_TIME_TOTAL = 5490.00  # sum of the 8 seeded demo expenses
ALL_TIME_COUNT = 8


# ------------------------------------------------------------------ #
# Fixtures / helpers
# ------------------------------------------------------------------ #

@pytest.fixture
def demo_user_id():
    """Return the id of the ``demo@spendly.com`` user (seeded on startup)."""
    with app.app_context():
        row = get_db().execute(
            "SELECT id FROM users WHERE email = ?", (DEMO_EMAIL,)
        ).fetchone()
    assert row is not None, "demo@spendly.com must be seeded"
    return row["id"]


@pytest.fixture
def client():
    """A Flask test client with no logged-in session."""
    return app.test_client()


@pytest.fixture
def logged_in_client(client, demo_user_id):
    """A Flask test client with the demo user logged in via the session."""
    with client.session_transaction() as session:
        session["user_id"] = demo_user_id
    return client


def _html(response):
    return response.get_data(as_text=True)


def _assert_in_range(html, start, end):
    """Assert that exactly the seeded transactions within [start, end] appear."""
    for tx_date, description in SEED_TRANSACTIONS:
        included = start <= date.fromisoformat(tx_date) <= end
        if included:
            assert description in html, f"{description!r} should be shown"
        else:
            assert description not in html, f"{description!r} should be hidden"


# ------------------------------------------------------------------ #
# Auth guard
# ------------------------------------------------------------------ #

def test_profile_requires_login(client):
    """Unauthenticated GET /profile must redirect (302) to /login."""
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_renders_when_logged_in(logged_in_client):
    """A logged-in user can open the profile page."""
    response = logged_in_client.get("/profile")
    assert response.status_code == 200


# ------------------------------------------------------------------ #
# Unfiltered / default behaviour
# ------------------------------------------------------------------ #

def test_unfiltered_profile_shows_all_transactions(logged_in_client):
    """No query params => all transactions, default behaviour unchanged."""
    response = logged_in_client.get("/profile")
    assert response.status_code == 200
    html = _html(response)

    for _tx_date, description in SEED_TRANSACTIONS:
        assert description in html, f"expected transaction {description!r} in page"

    assert f"₹{ALL_TIME_TOTAL:.2f}" in html  # total spent across all rows


def test_unfiltered_profile_has_eight_transaction_rows(logged_in_client):
    """The rendered history table should contain exactly the 8 seeded rows."""
    html = _html(logged_in_client.get("/profile"))
    assert html.count('class="tx-date"') == ALL_TIME_COUNT


# ------------------------------------------------------------------ #
# Custom date range filtering
# ------------------------------------------------------------------ #

def test_custom_range_shows_only_transactions_within_range(logged_in_client):
    """A custom From/To range hides transactions outside the range.

    Range Nov 5 - Nov 6, 2026: Entertainment 600 (Nov 5) + Shopping 1500 (Nov 6).
    """
    response = logged_in_client.get("/profile?start=2026-11-05&end=2026-11-06")
    assert response.status_code == 200
    html = _html(response)

    _assert_in_range(html, date(2026, 11, 5), date(2026, 11, 6))
    assert html.count('class="tx-date"') == 2


def test_custom_range_is_inclusive(logged_in_client):
    """Both endpoints of the range are included (date >= start, <= end)."""
    html = _html(logged_in_client.get("/profile?start=2026-11-01&end=2026-11-01"))
    _assert_in_range(html, date(2026, 11, 1), date(2026, 11, 1))


def test_custom_range_filtered_summary_stats(logged_in_client):
    """Total spent / count recalculate for the filtered range."""
    html = _html(logged_in_client.get("/profile?start=2026-11-05&end=2026-11-06"))

    # Entertainment 600 + Shopping 1500 = 2100
    assert "₹2100.00" in html

    # The unfiltered total must not leak through.
    assert f"₹{ALL_TIME_TOTAL:.2f}" not in html


# ------------------------------------------------------------------ #
# Validation — invalid dates are ignored
# ------------------------------------------------------------------ #

def test_invalid_date_strings_are_ignored(logged_in_client):
    """Invalid start or end values are treated as "no filter" -> all shown."""
    html = _html(logged_in_client.get("/profile?start=garbage&end=nonsense"))

    for _tx_date, description in SEED_TRANSACTIONS:
        assert description in html, f"expected {description!r} but not found"


def test_invalid_start_with_valid_end_keeps_end(logged_in_client):
    """A bad start is dropped while a valid end is still applied."""
    html = _html(logged_in_client.get("/profile?start=garbage&end=2026-11-04"))

    assert "Dental cleaning" in html      # 2026-11-04 — inside (<= end)
    assert "Movie tickets" not in html    # 2026-11-05 — after end


def test_invalid_end_with_valid_start_keeps_start(logged_in_client):
    """A bad end is dropped while a valid start is still applied."""
    html = _html(logged_in_client.get("/profile?start=2026-11-05&end=garbage"))

    assert "Movie tickets" in html        # 2026-11-05 — inside (>= start)
    assert "Dental cleaning" not in html  # 2026-11-04 — before start


def test_sql_injection_in_date_param_is_harmless(logged_in_client, demo_user_id):
    """A malformed date value is rejected before reaching SQL."""
    response = logged_in_client.get(
        "/profile", query_string={"start": "2026-11-01'; DROP TABLE expenses;--"}
    )
    assert response.status_code == 200

    with app.app_context():
        remaining = get_db().execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (demo_user_id,)
        ).fetchone()[0]
    assert remaining == ALL_TIME_COUNT


# ------------------------------------------------------------------ #
# Preset ranges
# ------------------------------------------------------------------ #

def _preset_ranges():
    """Preset ranges: This Week (Mon..today), This Month (1st..today),
    This Year (Jan 1..today).  All Time = no filter (no query params)."""
    today = date.today()
    return {
        "this_week": (today - timedelta(days=today.weekday()), today),
        "this_month": (today.replace(day=1), today),
        "this_year": (today.replace(month=1, day=1), today),
    }


def test_preset_this_week_monday_to_today(logged_in_client):
    start, end = _preset_ranges()["this_week"]
    response = logged_in_client.get(f"/profile?start={start}&end={end}")
    assert response.status_code == 200
    _assert_in_range(response.get_data(as_text=True), start, end)


def test_preset_this_month_first_to_today(logged_in_client):
    start, end = _preset_ranges()["this_month"]
    response = logged_in_client.get(f"/profile?start={start}&end={end}")
    assert response.status_code == 200
    _assert_in_range(response.get_data(as_text=True), start, end)


def test_preset_this_year_jan_first_to_today(logged_in_client):
    start, end = _preset_ranges()["this_year"]
    response = logged_in_client.get(f"/profile?start={start}&end={end}")
    assert response.status_code == 200
    _assert_in_range(response.get_data(as_text=True), start, end)


def test_preset_all_time_clears_filter(logged_in_client):
    """The All Time preset clears the filter (rendered without query params)."""
    response = logged_in_client.get("/profile")
    assert response.status_code == 200
    for _tx_date, description in SEED_TRANSACTIONS:
        assert description in response.get_data(as_text=True)


def test_preset_buttons_and_form_render(logged_in_client):
    """The filter bar exposes the four presets and the custom-range form."""
    html = _html(logged_in_client.get("/profile"))

    for label in ("This Week", "This Month", "This Year", "All Time"):
        assert label in html, f"expected preset button {label!r} in page"

    assert 'name="start"' in html
    assert 'name="end"' in html
    assert 'type="date"' in html
    assert "Apply" in html


# ------------------------------------------------------------------ #
# Empty state
# ------------------------------------------------------------------ #

def test_empty_range_shows_empty_state_message(logged_in_client):
    """A valid range with no transactions shows the empty-state message."""
    response = logged_in_client.get("/profile?start=2026-12-01&end=2026-12-31")
    assert response.status_code == 200
    html = _html(response)

    assert "No transactions in this date range" in html

    for _tx_date, description in SEED_TRANSACTIONS:
        assert description not in html


def test_empty_range_summary_stats_show_zero(logged_in_client):
    """An empty date range renders a zeroed summary."""
    html = _html(logged_in_client.get("/profile?start=2026-12-01&end=2026-12-31"))
    assert "₹0.00" in html


# ------------------------------------------------------------------ #
# Category breakdown
# ------------------------------------------------------------------ #

def _rendered_percentages(html):
    return [int(value) for value in re.findall(r"width:\s*(\d+)%", html)]


def test_category_percentages_sum_to_100_unfiltered(logged_in_client):
    percents = _rendered_percentages(_html(logged_in_client.get("/profile")))
    assert percents, "expected category breakdown bars in the page"
    assert sum(percents) == 100


def test_category_percentages_sum_to_100_when_filtered(logged_in_client):
    percents = _rendered_percentages(
        _html(logged_in_client.get("/profile?start=2026-11-05&end=2026-11-06"))
    )
    assert percents, "expected category breakdown bars in the page"
    assert sum(percents) == 100


def test_category_percentages_recalculate_for_filtered_data(demo_user_id):
    """Percentages are derived from the filtered subset, not the full history."""
    with app.app_context():
        full = get_category_breakdown(demo_user_id)
        filtered = get_category_breakdown(
            demo_user_id, start_date="2026-11-05", end_date="2026-11-06"
        )

    full_shopping = next(c["pct"] for c in full if c["name"] == "Shopping")
    filtered_shopping = next(c["pct"] for c in filtered if c["name"] == "Shopping")

    assert sum(c["pct"] for c in full) == 100
    assert sum(c["pct"] for c in filtered) == 100
    # In the full set Shopping is 28%; in the Nov 5-6 subset it is 71%.
    assert filtered_shopping > full_shopping


# ------------------------------------------------------------------ #
# Database layer
# ------------------------------------------------------------------ #

def test_summary_stats_apply_date_bounds(demo_user_id):
    with app.app_context():
        stats = get_summary_stats(
            demo_user_id, start_date="2026-11-05", end_date="2026-11-06"
        )
    assert stats["transaction_count"] == 2
    assert stats["total_spent"] == pytest.approx(2100.0)
    assert stats["top_category"] == "Shopping"


def test_recent_transactions_apply_date_bounds(demo_user_id):
    with app.app_context():
        rows = get_recent_transactions(
            demo_user_id, start_date="2026-11-05", end_date="2026-11-06"
        )
    assert len(rows) == 2
    for row in rows:
        assert "2026-11-05" <= row["date"] <= "2026-11-06"


def test_category_breakdown_apply_date_bounds(demo_user_id):
    with app.app_context():
        rows = get_category_breakdown(
            demo_user_id, start_date="2026-11-05", end_date="2026-11-06"
        )
    assert {row["name"] for row in rows} == {"Entertainment", "Shopping"}
    assert sum(row["pct"] for row in rows) == 100


def test_query_helpers_use_parameter_binding(demo_user_id):
    """An injection payload is passed as a literal value, not executed.

    If the helpers interpolated the value into SQL, ``OR '1'='1`` would match
    every row; because the query is parameterised, no row is >= the literal
    string, so the count is zero."""
    payload = "9999-99-99' OR '1'='1"
    with app.app_context():
        stats = get_summary_stats(demo_user_id, start_date=payload)
    assert stats["transaction_count"] == 0


def test_get_db_enables_foreign_keys():
    with app.app_context():
        enabled = get_db().execute("PRAGMA foreign_keys").fetchone()[0]
    assert enabled == 1


def test_seed_data_has_demo_user_with_eight_november_transactions(demo_user_id):
    with app.app_context():
        count = get_db().execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (demo_user_id,)
        ).fetchone()[0]
    assert count == ALL_TIME_COUNT
