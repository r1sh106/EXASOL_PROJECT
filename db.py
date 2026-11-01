"""Exasol access for Knode: connection, schema and seed data, using the official pyexasol driver."""
import os
import queue
import ssl
import threading
from pathlib import Path

import pyexasol
from flask import g, has_app_context

import seed_data as D


def load_env():
    env_file = Path(__file__).with_name(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()
SCHEMA = os.environ.get("EXA_SCHEMA", "KNODE")
# Exasol Personal allows 20 parallel connections in total, so the app reuses a few
POOL_SIZE = int(os.environ.get("EXA_POOL_SIZE", "3"))
_idle = queue.LifoQueue()
_open = 0
_open_lock = threading.Lock()
_script_conn = None


def connect():
    dsn = os.environ.get("EXA_DSN", "127.0.0.1:8563")
    # Exasol Personal's local deployment uses a self-signed certificate, so the launcher says
    # to disable certificate validation. Only do this for a database on this machine.
    sslopt = {"cert_reqs": ssl.CERT_NONE} if dsn.startswith(("127.0.0.1", "localhost")) else None
    return pyexasol.connect(
        dsn=dsn,
        user=os.environ.get("EXA_USER", "sys"),
        password=os.environ["EXA_PASSWORD"],
        websocket_sslopt=sslopt,
        lower_ident=True,  # return column names in lower case
        fetch_dict=True,
    )


def _new_conn():
    c = connect()
    c.execute(f"OPEN SCHEMA {SCHEMA}")
    return c


def _discard(c):
    global _open
    with _open_lock:
        _open -= 1
    try:
        c.close()
    except Exception:
        pass


def _acquire():
    """Take an idle pooled connection, open a new one if under the limit, or wait for one."""
    global _open
    while True:
        try:
            c = _idle.get_nowait()
        except queue.Empty:
            with _open_lock:
                may_open = _open < POOL_SIZE
                if may_open:
                    _open += 1
            if may_open:
                try:
                    return _new_conn()
                except Exception:
                    with _open_lock:
                        _open -= 1
                    raise
            c = _idle.get(timeout=30)
        if c.is_closed:
            _discard(c)
            continue
        return c


def release_request_connection(exc=None):
    """Flask teardown: hand the request's connection back to the pool."""
    c = g.pop("exa", None)
    if c is not None:
        if c.is_closed:
            _discard(c)
        else:
            _idle.put(c)


def close_idle():
    while True:
        try:
            _discard(_idle.get_nowait())
        except queue.Empty:
            return


def conn():
    """The current request's pooled connection (or one shared connection outside Flask)."""
    global _script_conn
    if has_app_context():
        if "exa" not in g:
            g.exa = _acquire()
        return g.exa
    if _script_conn is None or _script_conn.is_closed:
        _script_conn = _new_conn()
    return _script_conn


def lit(v):
    """SQL literal for Exasol. Strings are quoted with single quotes doubled."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def q(sql, *args):
    """Run SQL with {} placeholders filled by safe literals, return rows as dicts."""
    st = conn().execute(sql.format(*[lit(a) for a in args]))
    return st.fetchall() if st.result_type == "resultSet" else []


def q1(sql, *args):
    rows = q(sql, *args)
    return rows[0] if rows else None


def insert(c, table, rows):
    if rows:
        c.execute(f"INSERT INTO {table} VALUES " + ",".join("(" + ",".join(lit(v) for v in r) + ")" for r in rows))


DDL = [
    """CREATE TABLE customers (customer_id VARCHAR(10) PRIMARY KEY, customer_name VARCHAR(100), address VARCHAR(200))""",
    """CREATE TABLE shops (shop_id VARCHAR(10) PRIMARY KEY, shop_name VARCHAR(100), kind VARCHAR(30), owner_name VARCHAR(100),
        bot_phone VARCHAR(30), landmark VARCHAR(150), distance_m DECIMAL(6,0), years_open DECIMAL(4,0),
        has_knode BOOLEAN, tagline VARCHAR(150))""",
    """CREATE TABLE products (product_id VARCHAR(10) PRIMARY KEY, shop_id VARCHAR(10), product_name VARCHAR(100),
        cat VARCHAR(30), cat_words VARCHAR(300), aliases VARCHAR(300), price DECIMAL(10,2), cost DECIMAL(10,2), stock DECIMAL(8,0))""",
    """CREATE TABLE purchase_history (customer_id VARCHAR(10), shop_id VARCHAR(10), cat VARCHAR(30), product_id VARCHAR(10), usual_qty DECIMAL(6,2))""",
    """CREATE TABLE khata (shop_id VARCHAR(10), customer_name VARCHAR(100), balance DECIMAL(12,2), days_open DECIMAL(5,0))""",
    """CREATE TABLE routines (routine_id VARCHAR(10) PRIMARY KEY, shop_id VARCHAR(10), customer_name VARCHAR(100), items VARCHAR(500),
        due_minute DECIMAL(5,0), schedule_label VARCHAR(60), routine_state VARCHAR(10), reminders DECIMAL(4,0))""",
    """CREATE TABLE orders (order_id DECIMAL(10,0) PRIMARY KEY, shop_id VARCHAR(10), customer_name VARCHAR(100), channel VARCHAR(10),
        raw_text VARCHAR(2000), order_state VARCHAR(12), pay_mode VARCHAR(10), total DECIMAL(12,2), profit DECIMAL(12,2),
        created_at TIMESTAMP, packed_at TIMESTAMP)""",
    """CREATE TABLE order_items (order_id DECIMAL(10,0), product_id VARCHAR(10), qty DECIMAL(8,2), unit_price DECIMAL(10,2),
        unit_cost DECIMAL(10,2), note VARCHAR(100))""",
    """CREATE TABLE monthly_sales (shop_id VARCHAR(10), month_start DATE, sales DECIMAL(12,2), profit DECIMAL(12,2),
        order_count DECIMAL(8,0), phone_pct DECIMAL(5,0))""",
    """CREATE TABLE top_sellers (shop_id VARCHAR(10), month_start DATE, product_name VARCHAR(100), sales DECIMAL(12,2))""",
    """CREATE TABLE today_baseline (shop_id VARCHAR(10) PRIMARY KEY, sales DECIMAL(12,2), profit DECIMAL(12,2), order_count DECIMAL(8,0))""",
]


def reset_database():
    """Drop and recreate the KNODE schema with fresh demo data."""
    c = connect()
    c.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    c.execute(f"CREATE SCHEMA {SCHEMA}")
    c.execute(f"OPEN SCHEMA {SCHEMA}")
    for ddl in DDL:
        c.execute(ddl)
    cu = D.CUSTOMER
    insert(c, "customers", [(cu["customer_id"], cu["customer_name"], cu["address"])])
    insert(c, "shops", [(s["shop_id"], s["shop_name"], s["kind"], s["owner_name"], s["bot_phone"], s["landmark"],
                         s["distance_m"], s["years_open"], s["has_knode"], s["tagline"]) for s in D.SHOPS])
    insert(c, "products", D.PRODUCTS)
    insert(c, "purchase_history", D.HISTORY)
    insert(c, "khata", D.KHATA)
    insert(c, "routines", [r + (0,) for r in D.ROUTINES])
    insert(c, "monthly_sales", [(sid, D.MONTH_LABELS[i], *m) for sid, ms in D.MONTHLY.items() for i, m in enumerate(ms)])
    tops = []
    for sid, ms in D.MONTHLY.items():
        oct_sales = ms[-1][0]
        prods = sorted([p for p in D.PRODUCTS if p[1] == sid], key=lambda p: -p[6])[:5]
        tops += [(sid, D.MONTH_LABELS[-1], p[2], round(oct_sales * share, -1)) for p, share in zip(prods, D.TOP_SHARE)]
    insert(c, "top_sellers", tops)
    insert(c, "today_baseline", [(sid, *v) for sid, v in D.TODAY_BASELINE.items()])
    c.close()
    close_idle()  # pooled connections reopen against the new schema


if __name__ == "__main__":
    reset_database()
    print(f"Created schema {SCHEMA} with demo data.")
