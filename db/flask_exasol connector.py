import os
import re
from contextlib import contextmanager
from decimal import Decimal

import pyexasol

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


DEFAULT_STORE_ID = int(os.getenv("DEFAULT_STORE_ID", "1"))

ORDER_STATUSES = ("NEW", "PACKED", "OUT_FOR_DELIVERY", "DELIVERED", "CANCELLED")
STATUS_MESSAGES = {
    "NEW": "Order received, not packed yet",
    "PACKED": "Order is packed",
    "OUT_FOR_DELIVERY": "Order is out for delivery",
    "DELIVERED": "Order delivered",
    "CANCELLED": "Order cancelled",
}


what 

def _require_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def get_exasol_connection():
    try:
        return pyexasol.connect(
            dsn=_require_env("EXASOL_DSN"),
            user=_require_env("EXASOL_USER"),
            password=_require_env("EXASOL_PASSWORD"),
            encryption=True,
            autocommit=False,  # we commit/rollback ourselves so multi-step writes are atomic
        )
    except Exception as e:
        print(f"Connection error: {e}")
        return None


@contextmanager
def _connection():
    """Opens a connection, commits on success, rolls back on error, always closes."""
    conn = get_exasol_connection()
    if conn is None:
        raise ConnectionError("Could not connect to Exasol")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _num(value):
    return float(value) if isinstance(value, Decimal) else value


# ------------------------------------------------------- query file loader

_QUERIES = {}


def _load_queries():
    """Reads queries.sql. Each query starts with a '-- name: <name>' line."""
    name = None
    with open(os.path.join(BASE_DIR, "queries.sql"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("-- name:"):
                name = line.split(":", 1)[1].strip()
                _QUERIES[name] = []
            elif name:
                _QUERIES[name].append(line)
    for key, lines in _QUERIES.items():
        _QUERIES[key] = "".join(lines).strip().rstrip(";")


def q(name):
    """Returns the SQL text of a named query from queries.sql."""
    if not _QUERIES:
        _load_queries()
    return _QUERIES[name]


# ------------------------------------------------------------------- helpers

def _parse_items(items):
    """Accepts {"Burger": 2} or {"Burger": {"quantity": 2, "price": 120}}."""
    if not isinstance(items, dict) or not items:
        raise ValueError("items must be a non-empty dictionary")
    parsed = []
    for name, value in items.items():
        if isinstance(value, dict):
            qty, price = value.get("quantity", 1), value.get("price")
        else:
            qty, price = value, None
        qty = int(qty)
        if qty <= 0:
            raise ValueError(f"Quantity for '{name}' must be greater than 0")
        parsed.append((str(name).strip(), qty, None if price is None else float(price)))
    return parsed


def _parse_delivery(delivery):
    """quick / normal / after n days (also accepts a plain int n)."""
    if isinstance(delivery, int):
        return f"after {delivery} days"
    text = str(delivery).strip().lower()
    if text in ("quick", "normal"):
        return text
    match = re.search(r"\d+", text)
    if match:
        return f"after {int(match.group())} days"
    raise ValueError("delivery must be 'quick', 'normal' or 'after n days'")


# ------------------------------------------------------------------- setup

def setup_tables():
    """Creates all tables. Order matters because of foreign keys."""
    sql_files = [
        "store.sql", "customers.sql", "orders.sql",
        "order_items.sql", "sales.sql", "credit.sql",
    ]
    executed, missing = [], []
    try:
        with _connection() as conn:
            for file_name in sql_files:
                path = os.path.join(BASE_DIR, file_name)
                if not os.path.exists(path):
                    missing.append(file_name)
                    continue
                with open(path, "r", encoding="utf-8") as f:
                    conn.execute(f.read())
                executed.append(file_name)
        return {"status": "success", "executed": executed, "missing": missing}
    except Exception as e:
        return {"status": "error", "message": str(e), "executed": executed}


def test_db():
    """Quickly tests if the database responds."""
    try:
        with _connection() as conn:
            now = conn.execute(q("now")).fetchval()
        return {"status": "success", "current_time": str(now)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ------------------------------------------------------------ 1) customers

def add_customer(data):
    """data = {"customerName": ..., "phoneNumber": ..., "location": ...}
    Creates the customer, or updates name/location if the phone already exists."""
    name = (data.get("customerName") or "").strip()
    phone = (data.get("phoneNumber") or "").strip()
    location = (data.get("location") or "").strip() or None
    if not name or not phone:
        raise ValueError("customerName and phoneNumber are required")

    params = {"name": name, "phone": phone, "loc": location}
    with _connection() as conn:
        exists = conn.execute(q("customer_exists"), params).fetchval()
        conn.execute(q("update_customer" if exists else "insert_customer"), params)
    return {"phoneNumber": phone, "created": not exists}


# --------------------------------------------------------------- 2) orders

def add_order(data, store_id=None):
    """data = {"phoneNumber": ..., "items": {"Burger": 2, "Fries": {"quantity": 1, "price": 80}},
               "delivery": "quick" | "normal" | "after 3 days"}
    Returns the generated order ID (show this to the customer)."""
    phone = (data.get("phoneNumber") or "").strip()
    items = _parse_items(data.get("items"))
    delivery = _parse_delivery(data.get("delivery"))
    store_id = DEFAULT_STORE_ID if store_id is None else store_id

    with _connection() as conn:
        customer_name = conn.execute(q("get_customer_name"), {"phone": phone}).fetchval()
        if customer_name is None:
            raise ValueError("Customer not registered. Call add_customer() first.")

        conn.execute(
            q("insert_order"),
            {"sid": store_id, "name": customer_name, "phone": phone, "dt": delivery},
        )
        # Exasol has no RETURNING, so read back the newest order of this customer (same transaction)
        order_id = int(conn.execute(q("latest_order_id"), {"phone": phone}).fetchval())

        for item, qty, price in items:
            conn.execute(
                q("insert_item"),
                {"oid": order_id, "item": item, "qty": qty, "price": price},
            )
    return order_id


def get_order_status(order_id):
    """Returns status of an order: NEW / PACKED / OUT_FOR_DELIVERY / DELIVERED / CANCELLED."""
    with _connection() as conn:
        row = conn.execute(q("order_info"), {"oid": int(order_id)}).fetchone()
        if row is None:
            return {"found": False, "message": "Order not found"}
        items = conn.execute(q("order_items"), {"oid": int(order_id)}).fetchall()
    status = row[0]
    return {
        "found": True,
        "orderId": int(order_id),
        "status": status,
        "message": STATUS_MESSAGES.get(status, status),
        "delivery": row[1],
        "placedAt": str(row[2]),
        "items": [{"item": i[0], "quantity": int(i[1])} for i in items],
    }


def update_order_status(order_id, new_status):
    """For the shopkeeper side. Moving an order to DELIVERED also records it in SALES (once)."""
    new_status = new_status.strip().upper()
    if new_status not in ORDER_STATUSES:
        raise ValueError(f"status must be one of {ORDER_STATUSES}")
    params = {"oid": int(order_id), "st": new_status}

    with _connection() as conn:
        current = conn.execute(q("current_status"), params).fetchval()
        if current is None:
            return {"found": False, "message": "Order not found"}

        conn.execute(q("update_status"), params)

        if new_status == "DELIVERED" and current != "DELIVERED":
            conn.execute(q("record_delivered_sales"), params)
    return {"found": True, "orderId": int(order_id), "status": new_status}


# ---------------------------------------------------------------- 3) report

def get_report(store_id=None):
    """Total sales of the store (all customers) + list of credits that are due."""
    store_id = DEFAULT_STORE_ID if store_id is None else store_id
    params = {"sid": store_id}

    with _connection() as conn:
        sales = conn.execute(q("sales_summary"), params).fetchone()
        credits = conn.execute(q("credits_due"), params).fetchall()

    credit_list = [{"customer": c[0], "amountDue": _num(c[1])} for c in credits]
    return {
        "storeId": store_id,
        "sales": {
            "totalSalesRecords": int(sales[0]),
            "totalRevenue": _num(sales[1]),
            "totalUnitsSold": int(sales[2]),
        },
        "creditsDue": {
            "totalDue": sum(c["amountDue"] for c in credit_list),
            "customers": credit_list,
        },
    }


if __name__ == "__main__":
    print(test_db())
