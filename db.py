import sqlite3
from flask import g
from config import DATABASE_URL, get_db_path

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

def get_db():
    if "db" not in g:
        if DATABASE_URL and psycopg2:
            g.db = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            g.db = sqlite3.connect(str(get_db_path()), check_same_thread=False, timeout=10.0)
            g.db.row_factory = sqlite3.Row
            try:
                g.db.execute("PRAGMA journal_mode=WAL")
                g.db.execute("PRAGMA synchronous=NORMAL")
                g.db.execute("PRAGMA foreign_keys=ON")
            except Exception:
                pass
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def db_execute(sql, params=()):
    db = get_db()
    cur = db.cursor()
    if DATABASE_URL and psycopg2:
        sql = sql.replace("?", "%s")
    cur.execute(sql, params)
    db.commit()
    return cur

def db_execute_returning_id(sql, params=()):
    db = get_db()
    cur = db.cursor()
    if DATABASE_URL and psycopg2:
        sql = sql.replace("?", "%s")
        if sql.strip().upper().startswith("INSERT") and "RETURNING" not in sql.upper():
            sql = sql.rstrip("; \n") + " RETURNING id"
        cur.execute(sql, params)
        result = cur.fetchone()
        db.commit()
        return result[0] if result else None
    else:
        cur.execute(sql, params)
        db.commit()
        return cur.lastrowid

def db_fetchall(sql, params=()):
    db = get_db()
    cur = db.cursor()
    if DATABASE_URL and psycopg2:
        sql = sql.replace("?", "%s")
    cur.execute(sql, params)
    return cur.fetchall()

def db_fetchone(sql, params=()):
    rows = db_fetchall(sql, params)
    return rows[0] if rows else None

