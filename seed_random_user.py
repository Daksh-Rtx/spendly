#!/usr/bin/env python3
"""Generate and insert a random Indian user into the Spendly database."""

import os
import random
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

import sqlite3

# Database path (same as in database/db.py)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(PROJECT_ROOT, "spendly.db")

# Common Indian first names across regions
FIRST_NAMES = [
    # North Indian
    "Aarav", "Aditya", "Arjun", "Dev", "Dhruv", "Karan", "Krish", "Kunal",
    "Manav", "Neel", "Rahul", "Rohan", "Samar", "Shaurya", "Vivaan", "Yash",
    # South Indian
    "Adithya", "Akash", "Anand", "Arun", "Ganesh", "Karthik", "Madhav",
    "Naveen", "Pranav", "Rajesh", "Sanjay", "Suresh", "Venkatesh", "Vijay",
    # East Indian
    "Abhijeet", "Anirudh", "Debashish", "Koushik", "Mainak", "Pritam",
    "Ritwik", "Sourav", "Subham", "Swarnav",
    # West Indian
    "Amit", "Ankit", "Darshan", "Harsh", "Jay", "Ketan", "Mihir", "Nirav",
    "Parth", "Raj", "Sahil", "Tushar", "Viraj",
    # Female names
    "Aditi", "Ananya", "Anjali", "Deepika", "Divya", "Isha", "Kavya",
    "Meera", "Neha", "Pooja", "Priya", "Riya", "Sanya", "Shreya", "Sneha",
    "Tanvi", "Vidya",
]

# Common Indian last names across regions
LAST_NAMES = [
    # North Indian
    "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Agarwal", "Jain",
    "Mishra", "Tiwari", "Pandey", "Chauhan", "Rajput", "Yadav",
    # South Indian
    "Reddy", "Rao", "Nair", "Iyer", "Iyengar", "Menon", "Pillai",
    "Krishnan", "Subramanian", "Venkataraman",
    # East Indian
    "Banerjee", "Chatterjee", "Mukherjee", "Ghosh", "Das", "Roy",
    "Sen", "Bose", "Dutta", "Chakraborty",
    # West Indian
    "Patel", "Shah", "Mehta", "Desai", "Joshi", "Dave", "Trivedi",
    "Modi", "Bhatt", "Parekh",
]

# Email domains
EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "icloud.com"]


def generate_random_name():
    """Generate a realistic Indian name."""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return f"{first} {last}"


def generate_email(name):
    """Generate email from name with random number suffix."""
    # Convert to lowercase, replace spaces with dots
    base = name.lower().replace(" ", ".")
    # Add random 2-3 digit number
    suffix = random.randint(10, 999)
    domain = random.choice(EMAIL_DOMAINS)
    return f"{base}{suffix}@{domain}"


def get_db():
    """Get database connection (same pattern as database/db.py)."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def email_exists(email):
    """Check if email already exists in users table."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def insert_user(name, email, password_hash):
    """Insert user into database."""
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (name, email, password_hash, datetime.now().isoformat()),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def main():
    # Password hash for "password123"
    password_hash = generate_password_hash("password123")

    # Generate unique user
    max_attempts = 10
    for attempt in range(max_attempts):
        name = generate_random_name()
        email = generate_email(name)

        if not email_exists(email):
            user_id = insert_user(name, email, password_hash)
            print(f"User created successfully!")
            print(f"  id: {user_id}")
            print(f"  name: {name}")
            print(f"  email: {email}")
            return 0

        print(f"Email {email} already exists, retrying... ({attempt + 1}/{max_attempts})")

    print("Failed to generate unique email after maximum attempts")
    return 1


if __name__ == "__main__":
    sys.exit(main())