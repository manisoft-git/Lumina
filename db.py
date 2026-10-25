import sqlite3
from flask import g
from config import DATABASE_URL, get_db_path

try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool
except ImportError:
    psycopg2 = None

_pg_pool = None

def get_pg_pool():
    global _pg_pool
    if _pg_pool is None and DATABASE_URL and psycopg2:
        try:
            _pg_pool = psycopg2.pool.ThreadedConnectionPool(minconn=1, maxconn=10, dsn=DATABASE_URL)
        except Exception:
            _pg_pool = None
    return _pg_pool

def get_db():
    if "db" not in g:
        if DATABASE_URL and psycopg2:
            pool = get_pg_pool()
            if pool:
                g.db = pool.getconn()
                g.is_pooled_pg = True
            else:
                g.db = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
                g.is_pooled_pg = False
        else:
            g.db = sqlite3.connect(str(get_db_path()), check_same_thread=False, timeout=10.0)
            g.db.row_factory = sqlite3.Row
            try:
                g.db.execute("PRAGMA journal_mode=WAL")
                g.db.execute("PRAGMA synchronous=NORMAL")
                g.db.execute("PRAGMA foreign_keys=ON")
                g.db.execute("PRAGMA busy_timeout=5000")
                g.db.execute("PRAGMA cache_size=-64000")
                g.db.execute("PRAGMA temp_store=MEMORY")
                g.db.execute("PRAGMA mmap_size=268435456")
            except Exception:
                pass
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        if getattr(g, "is_pooled_pg", False) and _pg_pool:
            try:
                _pg_pool.putconn(db)
            except Exception:
                db.close()
        else:
            try:
                db.close()
            except Exception:
                pass

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
        if not result:
            return None
        if hasattr(result, "get") and result.get("id") is not None:
            return result["id"]
        return result[0]
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
