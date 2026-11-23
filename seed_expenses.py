#!/usr/bin/env python3
"""Seed realistic dummy expenses for a specific user."""

import os
import sys
import sqlite3
import random
from datetime import datetime, timedelta

# Add the project root to the path so we can import from database
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(PROJECT_ROOT, "spendly.db")


def get_db_connection():
    """Return a SQLite connection with row_factory and foreign keys enabled."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def verify_user_exists(user_id):
    """Check if user exists in the database."""
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()
        return row
    finally:
        conn.close()


def generate_expenses(user_id, count, months):
    """Generate and insert realistic expenses."""
    # Category distribution with weights (Food most common, Health/Entertainment least)
    categories = {
        "Food": {"weight": 30, "min_amt": 50, "max_amt": 800, "descriptions": [
            "Lunch at local dhaba", "Dinner with friends", "Breakfast at cafe",
            "Street food snacks", "Grocery shopping", "Food delivery order",
            "Weekend brunch", "Office canteen meal", "Sweet treats"
        ]},
        "Transport": {"weight": 20, "min_amt": 20, "max_amt": 500, "descriptions": [
            "Metro card recharge", "Auto rickshaw fare", "Bus pass monthly",
            "Petrol for scooter", "Cab to office", "Train ticket",
            "Parking fees", "Uber/Ola ride", "Bike service"
        ]},
        "Bills": {"weight": 15, "min_amt": 200, "max_amt": 3000, "descriptions": [
            "Electricity bill", "Water bill", "Internet recharge",
            "Mobile postpaid bill", "Gas cylinder refill", "DTH recharge",
            "Maintenance charges", "Society maintenance"
        ]},
        "Health": {"weight": 8, "min_amt": 100, "max_amt": 2000, "descriptions": [
            "Doctor consultation", "Medicines from pharmacy", "Dental checkup",
            "Eye checkup", "Physiotherapy session", "Lab tests",
            "Health checkup package", "Vitamins and supplements"
        ]},
        "Entertainment": {"weight": 7, "min_amt": 100, "max_amt": 1500, "descriptions": [
            "Movie tickets", "Netflix subscription", "Concert tickets",
            "Gaming session", "Bowling with friends", "Theme park visit",
            "Comedy show", "Streaming service renewal"
        ]},
        "Shopping": {"weight": 12, "min_amt": 200, "max_amt": 5000, "descriptions": [
            "Clothes shopping", "Electronics purchase", "Home decor items",
            "Books and stationery", "Footwear", "Accessories",
            "Kitchen appliances", "Gift for family", "Online shopping"
        ]},
        "Other": {"weight": 8, "min_amt": 50, "max_amt": 1000, "descriptions": [
            "Charity donation", "Gift for friend", "Repair charges",
            "Subscription renewal", "Emergency expense", "Miscellaneous",
            "Pet care", "Plant nursery"
        ]}
    }

    # Build weighted list for random selection
    weighted_categories = []
    for cat, info in categories.items():
        weighted_categories.extend([cat] * info["weight"])

    conn = get_db_connection()
    inserted = []

    try:
        # Start transaction
        conn.execute("BEGIN")

        # Calculate date range: spread across past <months> months
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=months * 30)

        for _ in range(count):
            # Random date within range
            random_days = random.randint(0, (end_date - start_date).days)
            expense_date = start_date + timedelta(days=random_days)

            # Select category based on weights
            category = random.choice(weighted_categories)
            cat_info = categories[category]

            # Generate realistic amount
            amount = round(random.uniform(cat_info["min_amt"], cat_info["max_amt"]), 2)

            # Select random description
            description = random.choice(cat_info["descriptions"])

            # Insert expense
            cursor = conn.execute(
                """
                INSERT INTO expenses (user_id, category, amount, date, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, category, amount, expense_date.isoformat(), description)
            )

            inserted.append({
                "id": cursor.lastrowid,
                "category": category,
                "amount": amount,
                "date": expense_date.isoformat(),
                "description": description
            })

        conn.commit()
        return inserted, start_date, end_date

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def main():
    # Parse arguments
    if len(sys.argv) != 4:
        print("Usage: /seed-expenses <user_id> <count> <months>")
        print("Example: /seed-expenses 1 50 6")
        sys.exit(1)

    try:
        user_id = int(sys.argv[1])
        count = int(sys.argv[2])
        months = int(sys.argv[3])
    except ValueError:
        print("Usage: /seed-expenses <user_id> <count> <months>")
        print("Example: /seed-expenses 1 50 6")
        sys.exit(1)

    # Verify user exists
    user = verify_user_exists(user_id)
    if not user:
        print(f"No user found with id {user_id}.")
        sys.exit(1)

    print(f"Seeding expenses for user: {user['name']} ({user['email']})")

    # Generate and insert expenses
    inserted, start_date, end_date = generate_expenses(user_id, count, months)

    # Print confirmation
    print(f"\n✓ Inserted {len(inserted)} expenses")
    print(f"  Date range: {start_date} to {end_date}")
    print(f"\nSample of inserted records (up to 5):")
    for i, exp in enumerate(inserted[:5], 1):
        print(f"  {i}. ID: {exp['id']} | {exp['date']} | {exp['category']} | ₹{exp['amount']:.2f} | {exp['description']}")


if __name__ == "__main__":
    main()