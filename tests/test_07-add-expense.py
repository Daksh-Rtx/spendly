"""Spec-based pytest tests for the Add Expense feature (Step 7).

Spec: .claude/specs/07-add-expense.md

The feature lets a logged-in user submit a new expense through a dedicated
form page at /expenses/add. The route handles GET (render form) and POST
(validate & insert), with auth guards, validation, and DB insertion.

Write tests use a throwaway user whose rows are removed in teardown (FK
cascade), so they never disturb the shared seeded ``demo@spendly.com`` data
that other test modules (e.g. the Step 6 date-filter suite) depend on.
"""

import sys
import uuid
from pathlib import Path

import pytest

# Ensure the project root (which contains app.py) is on sys.path so that
# ``from app import app`` works when pytest is invoked from any cwd.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app  # noqa: E402
from database.db import create_user, get_db  # noqa: E402
from database.queries import insert_expense  # noqa: E402


# ------------------------------------------------------------------ #
# Fixtures / helpers
# ------------------------------------------------------------------ #

@pytest.fixture
def isolated_user():
    """Create a throwaway user; delete it (and its expenses) on teardown.

    Returns the new user's id. Deleting the user relies on the
    ``ON DELETE CASCADE`` foreign key to remove any expenses it owns.
    """
    email = f"add-expense-test-{uuid.uuid4().hex}@example.com"
    with app.app_context():
        user_id = create_user("Add Expense Tester", email, "testpass123")
    yield user_id
    with app.app_context():
        db = get_db()
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()


@pytest.fixture
def client():
    """A Flask test client with no logged-in session."""
    return app.test_client()


@pytest.fixture
def logged_in_client(client, isolated_user):
    """A Flask test client logged in as the throwaway user."""
    with client.session_transaction() as session:
        session["user_id"] = isolated_user
    return client


def _html(response):
    """Return response body as text for HTML assertions."""
    return response.get_data(as_text=True)


def _count_expenses(user_id):
    """Count expense rows owned by ``user_id``."""
    with app.app_context():
        return get_db().execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()[0]


def _fetch_latest(user_id):
    """Return the most recently inserted expense row for ``user_id``."""
    with app.app_context():
        return get_db().execute(
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()


# ------------------------------------------------------------------ #
# Unit tests: insert_expense
# ------------------------------------------------------------------ #

def test_insert_expense_valid_insert_creates_row(isolated_user):
    """Valid insert should add a queryable row with all fields stored."""
    with app.app_context():
        new_id = insert_expense(
            isolated_user, 50.0, "Food", "2026-03-20", "Lunch"
        )
        assert new_id is not None, "insert_expense must return the new row id"

    row = _fetch_latest(isolated_user)
    assert row is not None, "inserted row must exist in the DB"
    assert row["id"] == new_id
    assert row["user_id"] == isolated_user
    assert row["amount"] == pytest.approx(50.0)
    assert row["category"] == "Food"
    assert row["date"] == "2026-03-20"
    assert row["description"] == "Lunch"


def test_insert_expense_none_description_stored_as_null(isolated_user):
    """description=None must be persisted as a SQL NULL."""
    with app.app_context():
        insert_expense(
            isolated_user, 25.0, "Transport", "2026-03-21", None
        )

    row = _fetch_latest(isolated_user)
    assert row is not None, "inserted row must exist in the DB"
    assert row["description"] is None, "None description must be NULL"


# ------------------------------------------------------------------ #
# Auth guard: GET /expenses/add
# ------------------------------------------------------------------ #

def test_add_expense_get_unauthenticated_redirects_to_login(client):
    """Unauthenticated GET /expenses/add must redirect (302) to /login."""
    response = client.get("/expenses/add")
    assert response.status_code == 302
    location = response.headers["Location"]
    assert "/login" in location, f"expected redirect to /login, got {location!r}"


def test_add_expense_get_authenticated_renders_form(logged_in_client):
    """Authenticated GET /expenses/add returns 200 with the full form."""
    response = logged_in_client.get("/expenses/add")
    assert response.status_code == 200
    html = _html(response)

    assert "<form" in html, "expected a <form> element"
    assert 'method="POST"' in html, "form must submit via POST"

    for field in ("amount", "category", "date", "description"):
        assert f'name="{field}"' in html, f"expected {field!r} field in form"


def test_add_expense_get_renders_all_seven_categories(logged_in_client):
    """The category <select> exposes exactly the 7 fixed categories."""
    html = _html(logged_in_client.get("/expenses/add"))

    categories = [
        "Food", "Transport", "Bills", "Health",
        "Entertainment", "Shopping", "Other",
    ]
    for cat in categories:
        assert f">{cat}</option>" in html, f"expected category option {cat!r}"


# ------------------------------------------------------------------ #
# Auth guard: POST /expenses/add
# ------------------------------------------------------------------ #

def test_add_expense_post_unauthenticated_redirects_to_login(client, isolated_user):
    """Unauthenticated POST /expenses/add must redirect (302) to /login."""
    response = client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Sneaky",
        },
    )
    assert response.status_code == 302
    location = response.headers["Location"]
    assert "/login" in location, f"expected redirect to /login, got {location!r}"
    assert _count_expenses(isolated_user) == 0, "no row may be inserted when logged out"


# ------------------------------------------------------------------ #
# POST /expenses/add: valid data
# ------------------------------------------------------------------ #

def test_add_expense_post_valid_data_redirects_and_inserts(
    logged_in_client, isolated_user,
):
    """Valid POST redirects to /profile (302) and creates exactly one row."""
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        },
    )
    assert response.status_code == 302
    location = response.headers["Location"]
    assert "/profile" in location, f"expected redirect to /profile, got {location!r}"

    assert _count_expenses(isolated_user) == 1, "exactly one expense must be inserted"
    row = _fetch_latest(isolated_user)
    assert row["amount"] == pytest.approx(50.0)
    assert row["category"] == "Food"
    assert row["date"] == "2026-03-20"
    assert row["description"] == "Lunch"


# ------------------------------------------------------------------ #
# POST /expenses/add: validation errors
# ------------------------------------------------------------------ #

@pytest.mark.parametrize(
    "amount",
    ["", "0", "-5", "abc", "  "],
    ids=["missing", "zero", "negative", "non-numeric", "whitespace"],
)
def test_add_expense_post_invalid_amount_rerenders_with_error(
    logged_in_client, isolated_user, amount,
):
    """A missing / zero / negative / non-numeric amount re-renders with error."""
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": amount,
            "category": "Food",
            "date": "2026-03-20",
            "description": "Test",
        },
    )
    assert response.status_code == 200, "invalid amount must re-render the form"
    html = _html(response)
    assert 'class="form-error"' in html, "expected an error message to be shown"
    assert _count_expenses(isolated_user) == 0, "no row may be inserted on error"


def test_add_expense_post_invalid_category_rerenders_with_error(
    logged_in_client, isolated_user,
):
    """A category outside the fixed list re-renders with an error message."""
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "InvalidCategory",
            "date": "2026-03-20",
            "description": "Test",
        },
    )
    assert response.status_code == 200
    html = _html(response)
    assert 'class="form-error"' in html, "expected an error message to be shown"
    assert _count_expenses(isolated_user) == 0, "no row may be inserted on error"


@pytest.mark.parametrize(
    "bad_date",
    ["not-a-date", "2026-13-01", "20-03-2026", ""],
    ids=["garbage", "bad-month", "wrong-format", "missing"],
)
def test_add_expense_post_invalid_date_rerenders_with_error(
    logged_in_client, isolated_user, bad_date,
):
    """A malformed / missing date re-renders the form with an error message."""
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "Food",
            "date": bad_date,
            "description": "Test",
        },
    )
    assert response.status_code == 200
    html = _html(response)
    assert 'class="form-error"' in html, "expected an error message to be shown"
    assert _count_expenses(isolated_user) == 0, "no row may be inserted on error"


# ------------------------------------------------------------------ #
# POST /expenses/add: no description (optional field)
# ------------------------------------------------------------------ #

@pytest.mark.parametrize(
    "description",
    ["", "   "],
    ids=["empty", "whitespace-only"],
)
def test_add_expense_post_no_description_saves_null(
    logged_in_client, isolated_user, description,
):
    """Omitting the description is valid; the row stores description as NULL."""
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "25.0",
            "category": "Health",
            "date": "2026-03-21",
            "description": description,
        },
    )
    assert response.status_code == 302, "no error expected when description is blank"
    location = response.headers["Location"]
    assert "/profile" in location, f"expected redirect to /profile, got {location!r}"

    assert _count_expenses(isolated_user) == 1
    row = _fetch_latest(isolated_user)
    assert row["description"] is None, "blank description must be stored as NULL"
