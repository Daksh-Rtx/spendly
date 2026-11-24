from flask import Flask, abort, flash, redirect, render_template, request, url_for

from database.db import close_db, create_user, get_db, get_user_by_email, init_db, seed_db

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

# Register teardown so the SQLite connection is closed after each request.
app.teardown_appcontext(close_db)

# Initialise the database schema and seed sample data on startup.
with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
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


@app.route("/login")
def login():
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
    return "Logout — coming in Step 3"


@app.route("/profile")
def profile():
    return "Profile page — coming in Step 4"


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
