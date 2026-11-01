"""Exasol access for KNODE Merchant, using the official pyexasol driver."""
import os
import queue
import ssl
import threading
from datetime import datetime, timedelta
from pathlib import Path

import pyexasol
from flask import g, has_app_context

ROOT = Path(__file__).parent


def load_env():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()
SCHEMA = os.environ.get("EXA_SCHEMA", "KNODE_SHOP")
# Exasol Personal allows 20 parallel connections in total, so the app reuses a few
POOL_SIZE = int(os.environ.get("EXA_POOL_SIZE", "4"))
_idle = queue.LifoQueue()
_open = 0
_open_lock = threading.Lock()
_script_conn = None


def connect():
    dsn = os.environ.get("EXA_DSN", "127.0.0.1:8563")
    # The local Exasol Personal deployment uses a self-signed certificate and its launcher
    # says to turn off validation. Only do that for a database on this machine.
    sslopt = {"cert_reqs": ssl.CERT_NONE} if dsn.startswith(("127.0.0.1", "localhost")) else None
    return pyexasol.connect(dsn=dsn, user=os.environ.get("EXA_USER", "sys"), password=os.environ["EXA_PASSWORD"],
                            websocket_sslopt=sslopt, lower_ident=True, fetch_dict=True)


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
    """SQL literal for Exasol; strings get single quotes doubled."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, datetime):
        return "TIMESTAMP '" + v.strftime("%Y-%m-%d %H:%M:%S") + "'"
    return "'" + str(v).replace("'", "''") + "'"


def q(sql, *args):
    """Run SQL with {} placeholders filled by safe literals; return rows as dicts."""
    sql = sql.format(*[lit(a) for a in args])
    try:
        st = conn().execute(sql)
    except pyexasol.ExaCommunicationError:
        # the database restarted or dropped the link: reconnect once and retry
        if has_app_context() and "exa" in g:
            _discard(g.pop("exa"))
        st = conn().execute(sql)
    return st.fetchall() if st.result_type == "resultSet" else []


def q1(sql, *args):
    rows = q(sql, *args)
    return rows[0] if rows else None


def num(v):
    f = float(v or 0)
    return int(f) if f.is_integer() else round(f, 2)


def next_id(table, col, start):
    return num(q1(f"SELECT COALESCE(MAX({col}), {start}) + 1 AS n FROM {table}")["n"])


DDL = [
    """CREATE TABLE shops (shop_id VARCHAR(12) PRIMARY KEY, shop_name VARCHAR(100), owner_name VARCHAR(100),
        area VARCHAR(150), phone VARCHAR(30), opens VARCHAR(40))""",
    """CREATE TABLE products (product_id VARCHAR(12) PRIMARY KEY, shop_id VARCHAR(12), product_name VARCHAR(120),
        unit VARCHAR(30), price DECIMAL(10,2), in_stock BOOLEAN, keywords VARCHAR(300))""",
    """CREATE TABLE customers (customer_id DECIMAL(10,0) PRIMARY KEY, customer_name VARCHAR(100), phone VARCHAR(20),
        address VARCHAR(200), created_at TIMESTAMP)""",
    """CREATE TABLE orders (order_id DECIMAL(10,0) PRIMARY KEY, shop_id VARCHAR(12), customer_id DECIMAL(10,0),
        order_state VARCHAR(12), channel VARCHAR(10), upload_file VARCHAR(120), transcript VARCHAR(4000),
        customer_note VARCHAR(500), parsed_by VARCHAR(40), total DECIMAL(12,2), created_at TIMESTAMP, updated_at TIMESTAMP)""",
    """CREATE TABLE order_items (item_id DECIMAL(12,0) PRIMARY KEY, order_id DECIMAL(10,0), line_no DECIMAL(4,0),
        product_id VARCHAR(12), raw_text VARCHAR(300), item_name VARCHAR(120), qty DECIMAL(8,2), unit VARCHAR(30),
        unit_price DECIMAL(10,2), available BOOLEAN, match_note VARCHAR(200))""",
]


def insert(c, table, rows):
    if rows:
        c.execute(f"INSERT INTO {table} VALUES " + ",".join("(" + ",".join(lit(v) for v in r) + ")" for r in rows))


def reset_database():
    """Drop and recreate the schema with made-up shops, products and a day of orders."""
    import seed
    c = connect()
    c.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    c.execute(f"CREATE SCHEMA {SCHEMA}")
    c.execute(f"OPEN SCHEMA {SCHEMA}")
    for ddl in DDL:
        c.execute(ddl)
    insert(c, "shops", seed.SHOPS)
    insert(c, "products", [p[:5] + (True, p[5]) for p in seed.PRODUCTS])
    q_out = {p[0] for p in seed.PRODUCTS if p[0] in seed.OUT_OF_STOCK}
    if q_out:
        c.execute("UPDATE products SET in_stock = FALSE WHERE product_id IN (" + ",".join(lit(p) for p in q_out) + ")")
    now = datetime.now().replace(microsecond=0)
    insert(c, "customers", [(cid, name, phone, addr, now - timedelta(days=30)) for cid, name, phone, addr in seed.CUSTOMERS])
    prices = {p[0]: (p[2], p[3], p[4]) for p in seed.PRODUCTS}
    orders, items, item_id = [], [], 5000
    for oid, (shop, cid, state, channel, mins_ago, transcript, lines) in enumerate(seed.ORDERS, start=2001):
        at = now - timedelta(minutes=mins_ago)
        total = 0
        for n, (pid, qty, raw) in enumerate(lines, start=1):
            name, unit, price = prices[pid]
            item_id += 1
            items.append((item_id, oid, n, pid, raw, name, qty, unit, price, True, None))
            total += qty * price
        orders.append((oid, shop, cid, state, channel, None, transcript, None, "seed data", total, at, at))
    # Completed orders for the previous six days, so the sales chart has history
    oid = 1000
    for shop in [s[0] for s in seed.SHOPS]:
        catalog = [p for p in seed.PRODUCTS if p[1] == shop]
        for day in range(1, 7):
            for k in range(3 + (day * 7 + len(shop)) % 4):
                oid += 1
                at = (now - timedelta(days=day)).replace(hour=9 + k * 2, minute=(day * 13) % 60)
                total = 0
                for n in range(1, 4):
                    pid, _, name, unit, price, _ = catalog[(day * 5 + k * 3 + n * 7) % len(catalog)]
                    qty = 1 + (day + n) % 2
                    item_id += 1
                    items.append((item_id, oid, n, pid, name, name, qty, unit, price, True, None))
                    total += qty * price
                orders.append((oid, shop, 1 + (day + k) % 4, "completed", "text", None, None, None, "seed data", total, at, at))
    insert(c, "orders", orders)
    insert(c, "order_items", items)
    c.close()
    close_idle()  # pooled connections reopen against the new schema


if __name__ == "__main__":
    reset_database()
    print(f"Created schema {SCHEMA} with demo data.")
