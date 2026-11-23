"""Database helpers for Spendly expense tracker.

Contains SQLite connection management and schema setup:

    get_db()   — returns a SQLite connection with row_factory and foreign keys enabled
    close_db() — closes the connection registered on ``g`` for this request
    init_db()  — creates all tables using CREATE TABLE IF NOT EXISTS
    seed_db()  — inserts sample data for development
"""

import os
import sqlite3

from flask import g
from werkzeug.security import generate_password_hash

# SQLite database file lives at the project root.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE = os.path.join(PROJECT_ROOT, "spendly.db")


def get_db():
    """Return the SQLite connection for the current request context.

    The connection is stored on Flask's ``g`` object so it is reused within
    the same request. Row objects are dict-like (``sqlite3.Row``) and foreign
    keys are enforced on every connection via PRAGMA.
    """
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    """Close the SQLite connection registered on ``g`` for this request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create all tables if they do not already exist.

    Safe to call multiple times. Uses ``CREATE TABLE IF NOT EXISTS`` and
    ``INSERT OR IGNORE`` patterns so repeated calls are no-ops.
    """
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL CHECK (amount >= 0),
            date TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_expenses_user_date
            ON expenses (user_id, date);
        """
    )
    db.commit()


def seed_db():
    """Insert sample users and expenses for development.

    Uses parameterized queries throughout (``?`` placeholders). Re-running is
    safe: the seed user is inserted with ``INSERT OR IGNORE`` and expenses are
    seeded only when the user has no expenses yet.
    """
    db = get_db()

    db.execute(
        "INSERT OR IGNORE INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )

    row = db.execute(
        "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()
    if row is None:
        return

    user_id = row["id"]

    existing = db.execute(
        "SELECT COUNT(*) AS c FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()
    if existing and existing["c"] > 0:
        return

    # Fixed category list per spec: Food, Transport, Bills, Health, Entertainment, Shopping, Other
    expenses = [
        (user_id, "Food", 850.00, "2026-11-01", "Lunch at cafe"),
        (user_id, "Transport", 450.00, "2026-11-02", "Metro pass recharge"),
        (user_id, "Bills", 1200.00, "2026-11-03", "Electricity bill"),
        (user_id, "Health", 350.00, "2026-11-04", "Dental cleaning"),
        (user_id, "Entertainment", 600.00, "2026-11-05", "Movie tickets"),
        (user_id, "Shopping", 1500.00, "2026-11-06", "Groceries"),
        (user_id, "Other", 220.00, "2026-11-07", "Gift for friend"),
        (user_id, "Food", 320.00, "2026-11-08", "Morning coffee"),
    ]

    db.executemany(
        """
        INSERT INTO expenses (user_id, category, amount, date, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        expenses,
    )
    db.commit()