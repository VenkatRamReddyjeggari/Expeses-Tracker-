import os
import sqlite3
from datetime import date, datetime
from functools import wraps

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = os.environ.get("SPENDLY_SECRET_KEY", "dev-only-change-me")
# Lax keeps the session cookie off cross-site POSTs, so other sites can't submit our forms.
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

init_db()
seed_db()

CATEGORIES = ["Food", "Transport", "Bills", "Shopping", "Entertainment", "Health", "Education", "Other"]
MAX_AMOUNT = 10_000_000


@app.template_filter("inr")
def format_inr(amount):
    """Format a number the Indian way: 123456.5 -> 1,23,456.50"""
    whole, frac = f"{amount:.2f}".split(".")
    sign = "-" if whole.startswith("-") else ""
    whole = whole.lstrip("-")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        groups.insert(0, head)
        whole = ",".join(groups) + "," + tail
    return f"{sign}{whole}.{frac}"


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def parse_expense_form(form):
    """Validate the add/edit expense form. Returns (values, error)."""
    values = {
        "amount": form.get("amount", "").strip(),
        "category": form.get("category", ""),
        "date": form.get("date", "").strip(),
        "description": form.get("description", "").strip(),
    }

    try:
        amount = round(float(values["amount"]), 2)
    except ValueError:
        return values, "Enter a valid amount."
    if not 0 < amount <= MAX_AMOUNT:
        return values, f"Amount must be between ₹0.01 and ₹{MAX_AMOUNT:,}."

    if values["category"] not in CATEGORIES:
        return values, "Choose a category."

    try:
        datetime.strptime(values["date"], "%Y-%m-%d")
    except ValueError:
        return values, "Enter a valid date."

    if len(values["description"]) > 200:
        return values, "Description must be 200 characters or fewer."

    values["amount"] = amount
    return values, None


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    error = None
    if not name or not email or not password:
        error = "All fields are required."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."

    if error is None:
        conn = get_db()
        try:
            cur = conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, generate_password_hash(password, method="pbkdf2:sha256")),
            )
            conn.commit()
            user_id = cur.lastrowid
        except sqlite3.IntegrityError:
            error = "An account with that email already exists."
        finally:
            conn.close()

    if error:
        return render_template("register.html", error=error, name=name, email=email), 400

    session.clear()
    session["user_id"] = user_id
    session["user_name"] = name
    return redirect(url_for("profile"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.", email=email), 401

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
@login_required
def profile():
    user_id = session["user_id"]
    conn = get_db()
    user = conn.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if user is None:
        conn.close()
        session.clear()
        return redirect(url_for("login"))

    totals = conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0) AS total,
               COUNT(*)                 AS count,
               COALESCE(SUM(CASE WHEN strftime('%Y-%m', date) = strftime('%Y-%m', 'now', 'localtime')
                                 THEN amount END), 0) AS this_month
        FROM expenses WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    categories = conn.execute(
        """
        SELECT category, SUM(amount) AS total
        FROM expenses WHERE user_id = ?
        GROUP BY category ORDER BY total DESC
        """,
        (user_id,),
    ).fetchall()
    expenses = conn.execute(
        """
        SELECT id, amount, category, date, description
        FROM expenses WHERE user_id = ?
        ORDER BY date DESC, id DESC LIMIT 20
        """,
        (user_id,),
    ).fetchall()
    conn.close()

    return render_template(
        "profile.html", user=user, totals=totals, categories=categories, expenses=expenses
    )


@app.route("/expenses/add", methods=["GET", "POST"])
@login_required
def add_expense():
    if request.method == "GET":
        return render_template(
            "expense_form.html",
            categories=CATEGORIES,
            values={"date": date.today().isoformat()},
        )

    values, error = parse_expense_form(request.form)
    if error:
        return render_template(
            "expense_form.html", categories=CATEGORIES, values=values, error=error
        ), 400

    conn = get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (session["user_id"], values["amount"], values["category"], values["date"],
         values["description"] or None),
    )
    conn.commit()
    conn.close()

    flash(f"Added ₹{format_inr(values['amount'])} for {values['category']}.")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(id):
    conn = get_db()
    # Scoped to the signed-in user, so nobody can edit someone else's expense by guessing an id.
    expense = conn.execute(
        "SELECT * FROM expenses WHERE id = ? AND user_id = ?", (id, session["user_id"])
    ).fetchone()
    if expense is None:
        conn.close()
        abort(404)

    if request.method == "GET":
        conn.close()
        values = dict(expense)
        values["amount"] = f"{expense['amount']:.2f}"
        return render_template(
            "expense_form.html", categories=CATEGORIES, values=values, editing=True
        )

    values, error = parse_expense_form(request.form)
    if error:
        conn.close()
        return render_template(
            "expense_form.html", categories=CATEGORIES, values=values, error=error, editing=True
        ), 400

    conn.execute(
        "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? "
        "WHERE id = ? AND user_id = ?",
        (values["amount"], values["category"], values["date"], values["description"] or None,
         id, session["user_id"]),
    )
    conn.commit()
    conn.close()

    flash(f"Updated ₹{format_inr(values['amount'])} for {values['category']}.")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete", methods=["POST"])
@login_required
def delete_expense(id):
    conn = get_db()
    expense = conn.execute(
        "SELECT amount, category FROM expenses WHERE id = ? AND user_id = ?",
        (id, session["user_id"]),
    ).fetchone()
    if expense is None:
        conn.close()
        abort(404)

    conn.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (id, session["user_id"]))
    conn.commit()
    conn.close()

    flash(f"Deleted ₹{format_inr(expense['amount'])} for {expense['category']}.")
    return redirect(url_for("profile"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
