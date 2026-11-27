"""Pure query helpers for Spendly profile page — no Flask imports at module level.

Each function calls get_db() internally and manages its own connection.
All queries use ? placeholders — never f-strings in SQL.
"""

from datetime import datetime

from database.db import get_db


def _apply_date_range(query, params, start_date, end_date):
    """Append inclusive ``date`` bounds to *query* and extend *params*.

    Returns ``(query, params)`` so callers can keep building their SQL.
    Only appends clauses when a bound is provided, so callers that pass
    ``None`` for both get the unfiltered query.
    """
    if start_date is not None:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date is not None:
        query += " AND date <= ?"
        params.append(end_date)
    return query, params


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


def get_summary_stats(user_id, start_date=None, end_date=None):
    """Return dict with total_spent, transaction_count, top_category.

    If user has no expenses: {"total_spent": 0, "transaction_count": 0, "top_category": "—"}.
    Amounts are Python floats; formatting (₹, %.2f) is done in the template.

    Optional ``start_date`` / ``end_date`` (YYYY-MM-DD) bounds filter the
    expense rows by ``date``. Invalid or missing values are treated as no filter.
    """
    db = get_db()

    summary_query = """
        SELECT
            COALESCE(SUM(amount), 0) AS total_spent,
            COUNT(*) AS transaction_count
        FROM expenses
        WHERE user_id = ?
    """
    summary_params = [user_id]
    summary_query, summary_params = _apply_date_range(
        summary_query, summary_params, start_date, end_date
    )

    row = db.execute(
        summary_query,
        summary_params,
    ).fetchone()

    # Top category: category with highest SUM(amount)
    top_query = """
        SELECT category, SUM(amount) AS cat_total
        FROM expenses
        WHERE user_id = ?
    """
    top_params = [user_id]
    top_query, top_params = _apply_date_range(
        top_query, top_params, start_date, end_date
    )
    top_query += " GROUP BY category ORDER BY cat_total DESC LIMIT 1"

    top = db.execute(
        top_query,
        top_params,
    ).fetchone()

    if row["transaction_count"] == 0:
        return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

    return {
        "total_spent": row["total_spent"],
        "transaction_count": row["transaction_count"],
        "top_category": top["category"] if top else "—",
    }


def get_recent_transactions(user_id, limit=10, start_date=None, end_date=None):
    """Return list of dicts: date, description, category, amount (newest first).

    Limit defaults to 10. Returns empty list if user has no expenses.

    Optional ``start_date`` / ``end_date`` (YYYY-MM-DD) bounds filter the
    expense rows by ``date``. Invalid or missing values are treated as no filter.
    """
    db = get_db()

    query = """
        SELECT date, description, category, amount
        FROM expenses
        WHERE user_id = ?
    """
    params = [user_id]
    query, params = _apply_date_range(query, params, start_date, end_date)
    query += " ORDER BY date DESC, id DESC LIMIT ?"
    params.append(limit)

    rows = db.execute(
        query,
        params,
    ).fetchall()

    return [dict(r) for r in rows]


def get_category_breakdown(user_id, start_date=None, end_date=None):
    """Return list of dicts: name, amount, pct (integer %, rounded, sum to 100).

    Ordered by amount DESC. Returns empty list if user has no expenses.

    Optional ``start_date`` / ``end_date`` (YYYY-MM-DD) bounds filter the
    expense rows by ``date``. Invalid or missing values are treated as no filter.
    """
    db = get_db()

    query = """
        SELECT category AS name, SUM(amount) AS amount
        FROM expenses
        WHERE user_id = ?
    """
    params = [user_id]
    query, params = _apply_date_range(query, params, start_date, end_date)
    query += " GROUP BY category ORDER BY amount DESC"

    rows = db.execute(
        query,
        params,
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