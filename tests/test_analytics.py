"""Test the analytics route."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app


def test_analytics_requires_login():
    """Unauthenticated GET /analytics must redirect to /login."""
    with app.test_client() as client:
        response = client.get("/analytics")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


def test_analytics_renders_when_logged_in():
    """A logged-in user can access the analytics page."""
    with app.test_client() as client:
        # Simulate logged-in session
        with client.session_transaction() as session:
            session["user_id"] = 1  # demo user seeded by seed_db()
        response = client.get("/analytics")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Advanced Analytics" in html
        assert "COMING SOON" in html


def test_navbar_shows_analytics_link_when_logged_in():
    """The navbar must show Analytics link when user is logged in."""
    with app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = 1
        response = client.get("/analytics")
        html = response.get_data(as_text=True)
        # Check that the Analytics nav link is present
        assert "/analytics" in html