# server.py  –  Flask-REST-API für News-System (Clever Cloud)
from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import datetime
import os

app = Flask(__name__)
CORS(app)                       # erlaubt Requests vom Desktop-Client

# Datenbank-Datei im gleichen Ordner (Clever Cloud lässt Schreibzugriff zu)
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "news_system.db")

# ---------- Hilfsfunktionen ----------
def dict_factory(cursor, row):
    """Wandelt SQLite-Zeile in Dict um"""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def get_db():
    con = sqlite3.connect(DB_FILE)
    con.row_factory = dict_factory
    return con

def init_db():
    """Erstellt Tabellen, falls sie nicht existieren"""
    with get_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                content     TEXT NOT NULL,
                author      TEXT NOT NULL,
                created_date TEXT NOT NULL,
                modified_date TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        # Default-Admin einfügen, falls leer
        cur = con.execute("SELECT COUNT(*) FROM admins").fetchone()
        if cur["COUNT(*)"] == 0:
            import hashlib
            pw_hash = hashlib.sha256("BAxd0800..??".encode()).hexdigest()
            con.execute("INSERT INTO admins(username, password) VALUES (?,?)",
                        ("Frank", pw_hash))
        con.commit()

# ---------- Routes ----------
@app.route("/news", methods=["GET"])
def get_news():
    """Alle News abrufen (neueste zuerst)"""
    with get_db() as con:
        rows = con.execute(
            "SELECT * FROM news ORDER BY created_date DESC"
        ).fetchall()
    return jsonify(rows)

@app.route("/news/<int:news_id>", methods=["GET"])
def get_news_by_id(news_id):
    """Einzelnen News-Eintrag abrufen"""
    with get_db() as con:
        row = con.execute("SELECT * FROM news WHERE id = ?", (news_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(row)

@app.route("/news", methods=["POST"])
def add_news():
    """Neue News anlegen"""
    data = request.json
    if not data or not data.get("title") or not data.get("content") or not data.get("author"):
        return jsonify({"error": "title, content, author required"}), 400

    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO news(title, content, author, created_date) VALUES (?,?,?,?)",
            (data["title"], data["content"], data["author"], now)
        )
        con.commit()
        new_id = cur.lastrowid
    return jsonify({"id": new_id}), 201

@app.route("/news/<int:news_id>", methods=["PUT"])
def update_news(news_id):
    """News bearbeiten"""
    data = request.json
    if not data or not data.get("title") or not data.get("content"):
        return jsonify({"error": "title and content required"}), 400

    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as con:
        con.execute(
            "UPDATE news SET title = ?, content = ?, modified_date = ? WHERE id = ?",
            (data["title"], data["content"], now, news_id)
        )
        con.commit()
    return jsonify({"status": "updated"})

@app.route("/news/<int:news_id>", methods=["DELETE"])
def delete_news(news_id):
    """News löschen"""
    with get_db() as con:
        con.execute("DELETE FROM news WHERE id = ?", (news_id,))
        con.commit()
    return jsonify({"status": "deleted"})

# ---------- Start ----------
if __name__ == "__main__":
    init_db()                       # Tabellen/Admin anlegen
    # Clever Cloud setzt PORT per Umgebungsvariable
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)