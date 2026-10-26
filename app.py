"""Library Management System - Flask backend + SQLite."""

import os
import re
import sqlite3
from contextlib import closing
from datetime import date

from flask import Flask, g, jsonify, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "library.db")

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    static_url_path="",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    title     TEXT NOT NULL,
    author    TEXT NOT NULL,
    isbn      TEXT NOT NULL UNIQUE,
    category  TEXT NOT NULL DEFAULT 'General',
    available INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS members (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS issues (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id     INTEGER NOT NULL REFERENCES books(id),
    member_id   INTEGER NOT NULL REFERENCES members(id),
    issue_date  TEXT NOT NULL,
    return_date TEXT
);
"""

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def db_path():
    return app.config.get("DB_PATH", DB_PATH)


def init_db():
    """Create tables if they do not exist."""
    with closing(sqlite3.connect(db_path())) as db:
        db.executescript(SCHEMA)


def get_db():
    if "db" not in g:
        # Make sure tables exist even when started with `flask run`.
        init_db()
        g.db = sqlite3.connect(db_path())
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def error(msg, code):
    return jsonify({"error": msg}), code


def book_json(row):
    d = dict(row)
    d["available"] = bool(d["available"])
    return d


BOOK_SELECT = (
    "SELECT b.*, m.name AS issued_to FROM books b "
    "LEFT JOIN issues i ON i.book_id = b.id AND i.return_date IS NULL "
    "LEFT JOIN members m ON m.id = i.member_id "
)


@app.get("/")
def index():
    return app.send_static_file("index.html")


# ---------- Books ----------
@app.get("/api/books")
def list_books():
    q = request.args.get("q", "").strip()
    db = get_db()
    if q:
        like = f"%{q}%"
        rows = db.execute(
            BOOK_SELECT + "WHERE b.title LIKE ? OR b.author LIKE ? OR b.isbn LIKE ? "
            "OR b.category LIKE ? ORDER BY b.title",
            (like, like, like, like),
        ).fetchall()
    else:
        rows = db.execute(BOOK_SELECT + "ORDER BY b.title").fetchall()
    return jsonify([book_json(r) for r in rows])  # empty list = no match


@app.post("/api/books")
def add_book():
    data = request.get_json(silent=True) or {}
    title = str(data.get("title") or "").strip()
    author = str(data.get("author") or "").strip()
    isbn = str(data.get("isbn") or "").strip()
    category = str(data.get("category") or "General").strip() or "General"
    if not (title and author and isbn):
        return error("Title, author and ISBN are required.", 400)
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO books (title, author, isbn, category) VALUES (?,?,?,?)",
            (title, author, isbn, category),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return error("A book with this ISBN already exists.", 409)
    row = db.execute("SELECT * FROM books WHERE id=?", (cur.lastrowid,)).fetchone()
    return jsonify(book_json(row)), 201


@app.delete("/api/books/<int:book_id>")
def delete_book(book_id):
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    if not book:
        return error("Book not found.", 404)
    if not book["available"]:
        return error("This book is issued. Return it before deleting.", 409)
    db.execute("DELETE FROM issues WHERE book_id=?", (book_id,))
    db.execute("DELETE FROM books WHERE id=?", (book_id,))
    db.commit()
    return jsonify({"message": "Book deleted."})


@app.post("/api/books/<int:book_id>/issue")
def issue_book(book_id):
    data = request.get_json(silent=True) or {}
    member_id = data.get("member_id")
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    if not book:
        return error("Book not found.", 404)
    if not member_id or not db.execute(
        "SELECT 1 FROM members WHERE id=?", (member_id,)
    ).fetchone():
        return error("Choose a valid member.", 400)
    if not book["available"]:
        return error("This book is already issued.", 409)
    db.execute(
        "INSERT INTO issues (book_id, member_id, issue_date) VALUES (?,?,?)",
        (book_id, member_id, date.today().isoformat()),
    )
    db.execute("UPDATE books SET available=0 WHERE id=?", (book_id,))
    db.commit()
    return jsonify({"message": "Book issued."})


@app.post("/api/books/<int:book_id>/return")
def return_book(book_id):
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    if not book:
        return error("Book not found.", 404)
    if book["available"]:
        return error("This book was not issued.", 409)
    db.execute(
        "UPDATE issues SET return_date=? WHERE book_id=? AND return_date IS NULL",
        (date.today().isoformat(), book_id),
    )
    db.execute("UPDATE books SET available=1 WHERE id=?", (book_id,))
    db.commit()
    return jsonify({"message": "Book returned."})


# ---------- Members ----------
@app.get("/api/members")
def list_members():
    rows = get_db().execute("SELECT * FROM members ORDER BY name").fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/members")
def add_member():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip()
    if not (name and email):
        return error("Name and email are required.", 400)
    if not EMAIL_RE.match(email):
        return error("Enter a valid email address.", 400)
    db = get_db()
    try:
        cur = db.execute("INSERT INTO members (name, email) VALUES (?,?)", (name, email))
        db.commit()
    except sqlite3.IntegrityError:
        return error("A member with this email already exists.", 409)
    return jsonify({"id": cur.lastrowid, "name": name, "email": email}), 201


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
