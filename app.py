"""KNODE Merchant: Flask app for neighbourhood grocery orders, backed by local Exasol Personal and Gemini."""
import os
import re
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, abort, jsonify, redirect, render_template, request, send_from_directory, session, url_for

import db
import gemini
from db import num, q, q1

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-only-secret")
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024
app.teardown_appcontext(db.release_request_connection)
UPLOADS = Path(__file__).parent / "uploads"
UPLOADS.mkdir(exist_ok=True)
STATES = {"pending": "Pending review", "ready": "Ready to pack", "completed": "Completed", "cancelled": "Cancelled"}
IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/heic": "heic", "image/heif": "heif"}
AUDIO_TYPES = {"audio/wav": "wav", "audio/x-wav": "wav", "audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/mp4": "m4a",
               "audio/x-m4a": "m4a", "audio/aac": "aac", "audio/ogg": "ogg", "audio/flac": "flac"}


# ---------- helpers ----------

def ago(ts):
    if isinstance(ts, str):
        ts = datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")
    mins = int((datetime.now() - ts).total_seconds() // 60)
    if mins < 1:
        return "just now"
    if mins < 60:
        return f"{mins} min ago"
    if mins < 24 * 60:
        return f"{mins // 60} h ago"
    return ts.strftime("%d %b")


def as_dt(ts):
    return datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S") if isinstance(ts, str) else ts


app.jinja_env.filters["ago"] = ago
app.jinja_env.filters["rs"] = lambda v: "₹" + f"{num(v):,}"
app.jinja_env.filters["qty"] = lambda v: f"{num(v):g}"


def merchant_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if "shop_id" not in session:
            return redirect(url_for("merchant_signin", next=request.path))
        return view(*a, **kw)
    return wrapped


def current_shop():
    return q1("SELECT * FROM shops WHERE shop_id = {}", session.get("shop_id"))


def current_customer():
    cid = session.get("customer_id")
    return q1("SELECT * FROM customers WHERE customer_id = {}", cid) if cid else None


def load_order(oid):
    o = q1("""SELECT o.*, c.customer_name, c.phone, c.address, s.shop_name FROM orders o
              JOIN customers c ON c.customer_id = o.customer_id JOIN shops s ON s.shop_id = o.shop_id
              WHERE o.order_id = {}""", oid)
    if not o:
        return None
    o["items"] = q("SELECT * FROM order_items WHERE order_id = {} ORDER BY line_no", oid)
    for i in o["items"]:
        i["line_total"] = num(float(i["qty"]) * float(i["unit_price"])) if i["unit_price"] is not None and i["available"] else 0
    o["state_label"] = STATES[o["order_state"]]
    return o


def can_view(o):
    return o and (session.get("shop_id") == o["shop_id"] or session.get("customer_id") == num(o["customer_id"]))


def recompute(oid):
    q("""UPDATE orders SET updated_at = {1}, total = (SELECT COALESCE(SUM(qty * unit_price), 0) FROM order_items
         WHERE order_id = {0} AND available AND unit_price IS NOT NULL) WHERE order_id = {0}""", oid, datetime.now().replace(microsecond=0))


def order_json(o):
    return {
        "order_id": num(o["order_id"]), "state": o["order_state"], "state_label": o["state_label"], "total": num(o["total"]),
        "items": [{"item_id": num(i["item_id"]), "name": i["item_name"], "raw": i["raw_text"], "qty": num(i["qty"]), "unit": i["unit"],
                   "price": num(i["unit_price"]) if i["unit_price"] is not None else None, "line_total": i["line_total"],
                   "available": bool(i["available"]), "matched": i["product_id"] is not None, "note": i["match_note"]} for i in o["items"]],
    }


def dashboard_data(shop_id):
    orders = q("""SELECT o.order_id, o.order_state, o.channel, o.total, o.created_at, c.customer_name,
                  (SELECT COUNT(*) FROM order_items i WHERE i.order_id = o.order_id) AS n_items,
                  (SELECT COUNT(*) FROM order_items i WHERE i.order_id = o.order_id AND NOT i.available) AS n_out
                  FROM orders o JOIN customers c ON c.customer_id = o.customer_id
                  WHERE o.shop_id = {} AND (o.order_state IN ('pending', 'ready') OR o.created_at >= {})
                  ORDER BY o.created_at DESC""", shop_id, datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
    queue = {k: [o for o in orders if o["order_state"] == k] for k in ("pending", "ready", "completed")}
    return queue


def stats(shop_id):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    days = []
    for d in range(6, -1, -1):
        start = today - timedelta(days=d)
        r = q1("""SELECT COALESCE(SUM(total), 0) AS s, COUNT(*) AS n FROM orders
                  WHERE shop_id = {} AND order_state = 'completed' AND created_at >= {} AND created_at < {}""", shop_id, start, start + timedelta(days=1))
        days.append({"label": "Today" if d == 0 else start.strftime("%a"), "sales": num(r["s"]), "orders": num(r["n"])})
    def top(since):
        return q("""SELECT i.item_name, SUM(i.qty) AS units, SUM(i.qty * i.unit_price) AS sales FROM order_items i
                    JOIN orders o ON o.order_id = i.order_id
                    WHERE o.shop_id = {} AND o.order_state = 'completed' AND i.available AND i.unit_price IS NOT NULL AND o.created_at >= {}
                    GROUP BY i.item_name ORDER BY sales DESC LIMIT 5""", shop_id, since)
    open_orders = q1("SELECT COUNT(*) AS n FROM orders WHERE shop_id = {} AND order_state IN ('pending', 'ready')", shop_id)["n"]
    return {"days": days, "today": days[-1], "week": sum(d["sales"] for d in days), "open": num(open_orders),
            "top_today": top(today), "top_week": top(today - timedelta(days=6))}


# ---------- pages ----------

@app.get("/")
def home():
    return render_template("home.html", shops=q("SELECT * FROM shops ORDER BY shop_name"), ai=gemini.enabled())


@app.route("/merchant/signin", methods=["GET", "POST"])
def merchant_signin():
    if request.method == "POST":
        shop = q1("SELECT shop_id FROM shops WHERE shop_id = {}", request.form.get("shop_id"))
        if shop:
            session["shop_id"] = shop["shop_id"]
            return redirect(request.args.get("next") or url_for("dashboard"))
    return render_template("merchant_signin.html", shops=q("SELECT * FROM shops ORDER BY shop_id DESC"))


@app.get("/merchant/signout")
def merchant_signout():
    session.pop("shop_id", None)
    return redirect(url_for("home"))


@app.get("/dashboard")
@merchant_required
def dashboard():
    shop = current_shop()
    return render_template("dashboard.html", shop=shop, queue=dashboard_data(shop["shop_id"]), stats=stats(shop["shop_id"]),
                           shop_link=request.host_url.rstrip("/") + url_for("shop_page", shop_id=shop["shop_id"]),
                           out_of_stock=q("SELECT * FROM products WHERE shop_id = {} AND NOT in_stock ORDER BY product_name", shop["shop_id"]),
                           ai=gemini.enabled(), model=gemini.model_name())


@app.get("/dashboard/queue")
@merchant_required
def dashboard_queue():
    """Order queue fragment the dashboard reloads every few seconds."""
    return render_template("_queue.html", queue=dashboard_data(session["shop_id"]))


@app.get("/dashboard/order/<int:oid>")
@merchant_required
def verify(oid):
    o = load_order(oid)
    if not o or o["shop_id"] != session["shop_id"]:
        abort(404)
    return render_template("verify.html", shop=current_shop(), o=o)


@app.get("/shop/<shop_id>")
def shop_page(shop_id):
    shop = q1("SELECT * FROM shops WHERE shop_id = {}", shop_id)
    if not shop:
        abort(404)
    cust = current_customer()
    recent = q("""SELECT order_id, order_state, total, created_at FROM orders WHERE shop_id = {} AND customer_id = {}
                  ORDER BY created_at DESC LIMIT 5""", shop_id, num(cust["customer_id"])) if cust else []
    return render_template("shop.html", shop=shop, cust=cust, recent=recent, states=STATES, ai=gemini.enabled())


@app.post("/shop/<shop_id>/signin")
def customer_signin(shop_id):
    name = request.form.get("name", "").strip()[:100]
    phone = re.sub(r"\D", "", request.form.get("phone", ""))[-10:]
    address = request.form.get("address", "").strip()[:200]
    if not name or len(phone) != 10:
        return redirect(url_for("shop_page", shop_id=shop_id, error="Enter your name and a 10-digit phone number."))
    c = q1("SELECT customer_id FROM customers WHERE phone = {}", phone)
    if c:
        cid = num(c["customer_id"])
        q("UPDATE customers SET customer_name = {}, address = COALESCE(NULLIF({}, ''), address) WHERE customer_id = {}", name, address, cid)
    else:
        cid = db.next_id("customers", "customer_id", 0)
        q("INSERT INTO customers VALUES ({}, {}, {}, {}, {})", cid, name, phone, address, datetime.now().replace(microsecond=0))
    session["customer_id"] = cid
    return redirect(url_for("shop_page", shop_id=shop_id))


@app.get("/shop/<shop_id>/signout")
def customer_signout(shop_id):
    session.pop("customer_id", None)
    return redirect(url_for("shop_page", shop_id=shop_id))


@app.get("/shop/<shop_id>/order/<int:oid>")
def order_status(shop_id, oid):
    o = load_order(oid)
    if not o or o["shop_id"] != shop_id or session.get("customer_id") != num(o["customer_id"]):
        abort(404)
    return render_template("order_status.html", shop=q1("SELECT * FROM shops WHERE shop_id = {}", shop_id), o=o)


@app.get("/uploads/<path:name>")
def upload(name):
    o = q1("SELECT * FROM orders WHERE upload_file = {}", name)
    if not can_view(o):
        abort(404)
    return send_from_directory(UPLOADS, name)


# ---------- API ----------

@app.post("/api/process-order")
def process_order():
    """Take a customer's photo, voice note or text, read it with Gemini and file an itemised bill for the shop."""
    cust = current_customer()
    shop = q1("SELECT * FROM shops WHERE shop_id = {}", request.form.get("shop_id"))
    if not cust:
        return jsonify(ok=False, message="Please sign in first."), 401
    if not shop:
        return jsonify(ok=False, message="Shop not found."), 404
    channel = request.form.get("channel", "text")
    text = request.form.get("text", "").strip()[:2000]
    note = request.form.get("note", "").strip()[:500]
    f = request.files.get("file")
    data = mime = None
    if f and f.filename:
        mime = (f.mimetype or "").split(";")[0].lower()
        allowed = IMAGE_TYPES if channel == "photo" else AUDIO_TYPES
        if mime not in allowed:
            return jsonify(ok=False, message="That file type isn't supported. Send a photo (JPG or PNG) or an audio file (WAV, MP3, M4A, OGG)."), 400
        data = f.read()
    if not data and not text:
        return jsonify(ok=False, message="Add a photo, a voice note or type your order."), 400

    catalog = q("SELECT product_id, product_name, unit, price, keywords, in_stock FROM products WHERE shop_id = {} ORDER BY product_id", shop["shop_id"])
    for p in catalog:
        p["price"] = num(p["price"])
    db.release_request_connection()  # don't hold a database connection while Gemini reads the order
    try:
        if gemini.enabled():
            parsed, engine = gemini.parse_order(catalog, channel, data=data, mime_type=mime, text=text or None)
        elif text and not data:
            parsed, engine = gemini.parse_typed_without_ai(catalog, text), "keyword matcher (no Gemini key)"
        else:
            return jsonify(ok=False, message="Reading photos and voice notes needs a Gemini API key on the server. Type your order instead, or ask the shop to add the key."), 503
    except Exception as e:  # network, quota or model errors from the Gemini API
        app.logger.exception("Gemini failed")
        detail = str(e)
        if "API_KEY_INVALID" in detail or "API key not valid" in detail:
            msg = "The shop's Gemini API key isn't valid. Check GEMINI_API_KEY in .env."
        elif "NOT_FOUND" in detail and "model" in detail.lower():
            msg = f"The Gemini model “{gemini.model_name()}” wasn't found. Check GEMINI_MODEL in .env."
        elif "RESOURCE_EXHAUSTED" in detail or "429" in detail:
            msg = "Too many orders at once for the free Gemini tier. Please try again in a minute."
        elif gemini.is_busy(e):
            msg = "Gemini is busy right now. Please try again in a minute."
        else:
            msg = f"Couldn't read the order right now ({type(e).__name__}). Please try again in a minute."
        return jsonify(ok=False, message=msg), 502
    if not parsed.items:
        return jsonify(ok=False, message="I couldn't find any items in that. Try a clearer photo, or type the items."), 422

    byid = {p["product_id"]: p for p in catalog}
    oid = db.next_id("orders", "order_id", 3000)
    now = datetime.now().replace(microsecond=0)
    fname = None
    if data:
        fname = f"order-{oid}.{(IMAGE_TYPES if channel == 'photo' else AUDIO_TYPES)[mime]}"
        (UPLOADS / fname).write_bytes(data)
    notes = "; ".join(x for x in [parsed.customer_note, note] if x) or None
    q("INSERT INTO orders VALUES ({}, {}, {}, 'pending', {}, {}, {}, {}, {}, 0, {}, {})",
      oid, shop["shop_id"], num(cust["customer_id"]), channel, fname, parsed.transcript[:4000], notes, engine, now, now)
    item_id = db.next_id("order_items", "item_id", 9000)
    for n, line in enumerate(parsed.items, start=1):
        p = byid.get(line.product_id)
        qty = max(float(line.quantity or 1), 0.5)
        if p:
            vals = (p["product_id"], p["product_name"], p["unit"], p["price"], bool(p["in_stock"]), None if p["in_stock"] else "Out of stock")
        else:
            vals = (None, line.item_name, line.unit, None, False, "Not sold at this shop")
        q("INSERT INTO order_items VALUES ({}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {})",
          item_id + n - 1, oid, n, vals[0], line.raw_text[:300], vals[1], qty, vals[2], vals[3], vals[4], vals[5])
    recompute(oid)
    return jsonify(ok=True, order_id=oid, redirect=url_for("order_status", shop_id=shop["shop_id"], oid=oid))


@app.get("/api/orders/<int:oid>")
def api_order(oid):
    o = load_order(oid)
    if not can_view(o):
        abort(404)
    return jsonify(order_json(o))


@app.post("/api/orders/<int:oid>/items/<int:item_id>/availability")
@merchant_required
def set_availability(oid, item_id):
    o = load_order(oid)
    if not o or o["shop_id"] != session["shop_id"]:
        abort(404)
    item = next((i for i in o["items"] if num(i["item_id"]) == item_id), None)
    if not item or item["product_id"] is None:
        return jsonify(ok=False, message="This item isn't in your catalog."), 400
    avail = bool((request.json or {}).get("available"))
    q("UPDATE order_items SET available = {}, match_note = {} WHERE item_id = {}", avail, None if avail else "Out of stock", item_id)
    q("UPDATE products SET in_stock = {} WHERE product_id = {}", avail, item["product_id"])
    recompute(oid)
    return jsonify(ok=True, order=order_json(load_order(oid)))


@app.post("/api/orders/<int:oid>/state")
@merchant_required
def set_state(oid):
    o = load_order(oid)
    if not o or o["shop_id"] != session["shop_id"]:
        abort(404)
    new = (request.json or {}).get("state")
    allowed = {"pending": {"ready", "cancelled"}, "ready": {"completed", "cancelled"}}
    if new not in allowed.get(o["order_state"], set()):
        return jsonify(ok=False, message="That step isn't possible for this order."), 400
    q("UPDATE orders SET order_state = {}, updated_at = {} WHERE order_id = {}", new, datetime.now().replace(microsecond=0), oid)
    return jsonify(ok=True)


@app.post("/api/products/<pid>/stock")
@merchant_required
def set_stock(pid):
    avail = bool((request.json or {}).get("in_stock"))
    q("UPDATE products SET in_stock = {} WHERE product_id = {} AND shop_id = {}", avail, pid, session["shop_id"])
    return jsonify(ok=True)


@app.post("/api/reset")
@merchant_required
def reset():
    db.reset_database()
    for f in UPLOADS.glob("order-*"):
        f.unlink()
    return jsonify(ok=True)


@app.errorhandler(500)
def server_error(e):
    cause = str(getattr(e, "original_exception", e) or "")
    if "license limit" in cause:
        msg = "The database has too many open connections. Close other KNODE apps or restart this one."
    elif "Connection refused" in cause or "ExaCommunicationError" in type(getattr(e, "original_exception", e)).__name__:
        msg = "Can't reach the Exasol database. Start it with: exasol start -d knode"
    else:
        msg = "Something went wrong on our side. Please try again."
    if request.path.startswith("/api/"):
        return jsonify(ok=False, message=msg), 500
    return render_template("error.html", message=msg), 500


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify(ok=False, message="Not found."), 404
    return render_template("error.html", message="That page doesn't exist, or you don't have access to it."), 404


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5050)), debug=False, threaded=True)
