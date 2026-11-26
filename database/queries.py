"""Pure query helpers for Spendly profile page — no Flask imports at module level.

Each function calls get_db() internally and manages its own connection.
All queries use ? placeholders — never f-strings in SQL.
"""

from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    """Return dict with name, email, member_since for the user, or None.

    Formats created_at as "Month YYYY" (e.g. "November 2026").
    """
    db = get_db()
    row = db.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        return None
    dt = datetime.fromisoformat(row["created_at"])
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": dt.strftime("%B %Y"),
    }


def get_summary_stats(user_id):
    """Return dict with total_spent, transaction_count, top_category.

    If user has no expenses: {"total_spent": 0, "transaction_count": 0, "top_category": "—"}.
    Amounts are Python floats; formatting (₹, %.2f) is done in the template.
    """
    db = get_db()

    # Summary: total spent and count
    row = db.execute(
        """
        SELECT
            COALESCE(SUM(amount), 0) AS total_spent,
            COUNT(*) AS transaction_count
        FROM expenses
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()

    # Top category: category with highest SUM(amount)
    top = db.execute(
        """
        SELECT category, SUM(amount) AS cat_total
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY cat_total DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()

    if row["transaction_count"] == 0:
        return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

    return {
        "total_spent": row["total_spent"],
        "transaction_count": row["transaction_count"],
        "top_category": top["category"] if top else "—",
    }


def get_recent_transactions(user_id, limit=10):
    """Return list of dicts: date, description, category, amount (newest first).

    Limit defaults to 10. Returns empty list if user has no expenses.
    """
    db = get_db()
    rows = db.execute(
        """
        SELECT date, description, category, amount
        FROM expenses
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()

    return [dict(r) for r in rows]


def get_category_breakdown(user_id):
    """Return list of dicts: name, amount, pct (integer %, rounded, sum to 100).

    Ordered by amount DESC. Returns empty list if user has no expenses.
    """
    db = get_db()
    rows = db.execute(
        """
        SELECT category AS name, SUM(amount) AS amount
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY amount DESC
        """,
        (user_id,),
    ).fetchall()

    if not rows:
        return []

    total = sum(r["amount"] for r in rows)

    # Compute integer percentages; adjust largest to absorb rounding remainder
    result = []
    for r in rows:
        pct = round(r["amount"] * 100 / total) if total else 0
        result.append(
            {"name": r["name"], "amount": r["amount"], "pct": pct}
        )

    # Adjust largest category to make percentages sum to 100
    diff = 100 - sum(r["pct"] for r in result)
    if diff != 0 and result:
        # Find the first (largest amount) category and adjust it
        # result is already ordered by amount DESC, so index 0 is largest
        result[0]["pct"] += diff

    return result