import sqlite3
from pathlib import Path

from flask import current_app, g

from db.schema import init_schema


def _connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    if "db" not in g:
        g.db = _connect(current_app.config["DATABASE_PATH"])
    return g.db


def get_readonly_db():
    if "db_ro" not in g:
        uri = Path(current_app.config["DATABASE_PATH"]).resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        g.db_ro = conn
    return g.db_ro


def close_db(exc=None):
    for key in ("db", "db_ro"):
        conn = g.pop(key, None)
        if conn is not None:
            conn.close()


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_schema(get_db())
