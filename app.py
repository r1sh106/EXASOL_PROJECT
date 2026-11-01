"""Knode demo backend: Flask API over a local Exasol Personal database."""
import html
import re
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory

import db
import seed_data
from db import q, q1

app = Flask(__name__, static_folder="static", static_url_path="")
app.teardown_appcontext(db.release_request_connection)
CUSTOMER_ID, CUSTOMER_NAME = "C1", "Meena"
NUMW = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "ten": 10, "half": 0.5}


def num(v):
    f = float(v or 0)
    return int(f) if f.is_integer() else round(f, 2)


def err(msg, code=400):
    return jsonify(ok=False, message=msg), code


# ---------- order understanding ----------

def has(seg, word):
    return re.search(r"\b" + re.escape(word) + r"\b", seg) is not None


def keywords(p):
    return [w.strip() for w in (p["aliases"] or "").split(",") + (p["cat_words"] or "").split(",") if w.strip()]


def read_qty(seg, p):
    for w in sorted(keywords(p), key=len, reverse=True):  # so "a4 paper" is not read as 4
        seg = re.sub(r"\b" + re.escape(w) + r"\b", " ", seg)
    s = re.sub(r"\b(an?|one|two|three|four|five|six|ten|half)\b", lambda m: str(NUMW[m.group(0)]), seg)
    u = re.search(r"(\d+(?:\.\d+)?)\s*(kgs?|g|gm|grams?|ml|l|ltr|litres?|liters?|m|metres?|meters?)\b", s)
    if u:  # "2kg onion" = 2 packs of 1kg; "atta 5kg" = 1 pack of 5kg
        return float(u.group(1)) if re.search(r"\b1\s?(kg|l|litre|metre)\b", p["product_name"], re.I) else 1
    n = re.search(r"\d+(?:\.\d+)?", s)
    return float(n.group(0)) if n else None


def parse(text, shop_id):
    prods = q("SELECT * FROM products WHERE shop_id = {} ORDER BY product_id", shop_id)
    byid = {p["product_id"]: p for p in prods}
    hist = {}
    for h in q("SELECT cat, product_id, usual_qty FROM purchase_history WHERE customer_id = {} AND shop_id = {}", CUSTOMER_ID, shop_id):
        hist.setdefault(h["cat"], []).append(h)
    aliases = sorted({(a.strip(), p["product_id"]) for p in prods for a in (p["aliases"] or "").split(",") if a.strip()}, key=lambda x: -len(x[0]))
    catw = sorted({(w.strip(), p["cat"]) for p in prods for w in p["cat_words"].split(",") if w.strip()}, key=lambda x: -len(x[0]))
    out = []
    for seg in re.split(r",|\n|\.(?!\d)|;|&|\band\b|\bplus\b|\balso\b", text.lower()):
        hit = next((pid for a, pid in aliases if has(seg, a)), None)
        if hit:
            qty = read_qty(seg, byid[hit])
            out.append({"product_id": hit, "qty": qty or 1, "note": ""})
            continue
        cat = next((c for w, c in catw if has(seg, w)), None)
        if not cat:
            continue
        h = hist.get(cat)
        if h and len(h) > 1:  # e.g. "vegetables" = her usual onion, tomato, potato
            out += [{"product_id": x["product_id"], "qty": num(x["usual_qty"]), "note": "usual items · from past orders"} for x in h]
            continue
        in_cat = [p for p in prods if p["cat"] == cat]
        pid = h[0]["product_id"] if h else in_cat[0]["product_id"]
        qty = read_qty(seg, byid[pid])
        if h:
            note = ("usual brand & qty" if qty is None else "usual brand") + " · from past orders"
        else:
            note = "shop's most popular · no past orders yet" if len(in_cat) > 1 else ""
        out.append({"product_id": pid, "qty": qty if qty is not None else (num(h[0]["usual_qty"]) if h else 1), "note": note})
    merged = {}
    for line in out:
        if line["product_id"] in merged:
            merged[line["product_id"]]["qty"] += line["qty"]
        else:
            merged[line["product_id"]] = dict(line)
    return list(merged.values())


# ---------- orders ----------

def recompute(order_id):
    q("""UPDATE orders SET total = (SELECT COALESCE(SUM(qty * unit_price), 0) FROM order_items WHERE order_id = {0}),
                           profit = (SELECT COALESCE(SUM(qty * (unit_price - unit_cost)), 0) FROM order_items WHERE order_id = {0})
         WHERE order_id = {0}""", order_id)


def add_items(order_id, lines):
    for line in lines:
        row = q1("SELECT qty FROM order_items WHERE order_id = {} AND product_id = {}", order_id, line["product_id"])
        if row:
            q("UPDATE order_items SET qty = qty + {} WHERE order_id = {} AND product_id = {}", line["qty"], order_id, line["product_id"])
        else:
            q("""INSERT INTO order_items SELECT {}, product_id, {}, price, cost, {} FROM products WHERE product_id = {}""",
              order_id, line["qty"], line["note"], line["product_id"])
    recompute(order_id)


def new_order_id():
    return num(q1("SELECT COALESCE(MAX(order_id), 1041) + 1 AS n FROM orders")["n"])


def bill(order_id):
    o = q1("SELECT o.*, s.shop_name FROM orders o JOIN shops s ON s.shop_id = o.shop_id WHERE order_id = {}", order_id)
    if not o:
        return None
    items = q("""SELECT i.product_id, p.product_name, i.qty, i.unit_price, i.note, p.stock FROM order_items i
                 JOIN products p ON p.product_id = i.product_id WHERE i.order_id = {} ORDER BY p.product_id""", order_id)
    return {
        "order_id": num(o["order_id"]), "shop_id": o["shop_id"], "shop_name": o["shop_name"], "state": o["order_state"],
        "pay_mode": o["pay_mode"], "total": num(o["total"]), "profit": num(o["profit"]), "customer": o["customer_name"],
        "lines": [{"name": i["product_name"], "qty": num(i["qty"]), "amount": num(float(i["qty"]) * float(i["unit_price"])),
                   "note": i["note"] or "", "short": float(i["qty"]) > float(i["stock"]), "stock": num(i["stock"])} for i in items],
    }


def sell(order_id):
    """Take stock out and put a khata order on the customer's account."""
    o = q1("SELECT shop_id, customer_name, pay_mode, total FROM orders WHERE order_id = {}", order_id)
    for i in q("SELECT product_id, qty FROM order_items WHERE order_id = {}", order_id):
        q("UPDATE products SET stock = GREATEST(stock - {}, 0) WHERE product_id = {}", i["qty"], i["product_id"])
    q("UPDATE orders SET order_state = 'packed', packed_at = {} WHERE order_id = {}", now(), order_id)
    if o["pay_mode"] == "khata":
        if not q1("SELECT 1 AS x FROM khata WHERE shop_id = {} AND customer_name = {}", o["shop_id"], o["customer_name"]):
            q("INSERT INTO khata VALUES ({}, {}, 0, 0)", o["shop_id"], o["customer_name"])
        q("UPDATE khata SET balance = balance + {} WHERE shop_id = {} AND customer_name = {}", o["total"], o["shop_id"], o["customer_name"])


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------- reports ----------

def today(shop_id):
    b = q1("SELECT * FROM today_baseline WHERE shop_id = {}", shop_id)
    t = q1("""SELECT COALESCE(SUM(total), 0) AS sales, COALESCE(SUM(profit), 0) AS profit, COUNT(*) AS n
              FROM orders WHERE shop_id = {} AND order_state = 'packed'""", shop_id)
    return {"sales": num(b["sales"]) + num(t["sales"]), "profit": num(b["profit"]) + num(t["profit"]),
            "orders": num(b["order_count"]) + num(t["n"]), "phone": num(t["n"])}


def health(shop_id, clock):
    m = q("SELECT * FROM monthly_sales WHERE shop_id = {} ORDER BY month_start", shop_id)
    prev, cur = m[-2], m[-1]
    growth = float(cur["sales"]) / float(prev["sales"]) - 1
    margin = float(cur["profit"]) / float(cur["sales"])
    owed = num(q1("SELECT COALESCE(SUM(balance), 0) AS b FROM khata WHERE shop_id = {}", shop_id)["b"])
    old = q("SELECT customer_name, balance, days_open FROM khata WHERE shop_id = {} AND balance > 0 AND days_open > 30", shop_id)
    low = q("SELECT product_name FROM products WHERE shop_id = {} AND stock < 6 ORDER BY product_id", shop_id)
    late = q("SELECT customer_name FROM routines WHERE shop_id = {} AND routine_state = 'pending' AND due_minute <= {}", shop_id, clock)
    e = html.escape
    pct = lambda x: f"{round(x * 100, 1)}%"
    rs = lambda v: "₹" + f"{num(v):,}"
    factors = [
        {"name": "Sales growth", "s": "good" if growth > 0.05 else "watch" if growth > -0.05 else "bad",
         "why": f"Sales {'up' if growth >= 0 else 'down'} {pct(abs(growth))} in October vs September"},
        {"name": "Profit margin", "s": "good" if margin >= 0.12 else "watch" if margin >= 0.08 else "bad",
         "why": f"{pct(margin)} margin in October (target 12% or more)"},
        {"name": "Credit to collect", "s": "watch" if old else "good",
         "why": (f"{rs(owed)} on khata · " + ", ".join(f"{e(k['customer_name'])} owes {rs(k['balance'])} for {num(k['days_open'])} days" for k in old))
                if old else f"{rs(owed)} on khata, all recent"},
        {"name": "Stock levels", "s": "bad" if len(low) >= 3 else "watch" if low else "good",
         "why": ("Running low: " + ", ".join(e(p["product_name"]) for p in low)) if low else "All items above reorder level"},
        {"name": "Regular orders", "s": "watch" if late else "good",
         "why": (f"{len(late)} overdue today: " + ", ".join(e(r["customer_name"]) for r in late)) if late else "All regular orders on time"},
    ]
    score = sum({"good": 20, "watch": 12, "bad": 5}[f["s"]] for f in factors)
    return {"score": score, "label": "Healthy" if score >= 80 else "Needs attention" if score >= 60 else "At risk", "factors": factors}


def report(shop_id, clock):
    months = [{"m": r["month_start"].strftime("%b") if hasattr(r["month_start"], "strftime") else datetime.strptime(str(r["month_start"]), "%Y-%m-%d").strftime("%b"),
               "sales": num(r["sales"]), "profit": num(r["profit"]), "orders": num(r["order_count"]), "phone": num(r["phone_pct"])}
              for r in q("SELECT * FROM monthly_sales WHERE shop_id = {} ORDER BY month_start", shop_id)]
    tops = [[r["product_name"], num(r["sales"])] for r in q("SELECT product_name, sales FROM top_sellers WHERE shop_id = {} ORDER BY sales DESC", shop_id)]
    return {"today": today(shop_id), "months": months, "top": tops, "health": health(shop_id, clock)}


# ---------- routes ----------

@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/shops")
def shops():
    rows = q("""SELECT s.*, (SELECT COUNT(*) FROM products p WHERE p.shop_id = s.shop_id) AS product_count
                FROM shops s ORDER BY distance_m""")
    return jsonify([{**r, "distance_m": num(r["distance_m"]), "years_open": num(r["years_open"]), "product_count": num(r["product_count"])} for r in rows])


@app.get("/api/shops/<shop_id>")
def shop(shop_id):
    clock = int(request.args.get("clock", 540))
    s = q1("SELECT * FROM shops WHERE shop_id = {}", shop_id)
    if not s:
        return err("No such shop", 404)
    prods = q("SELECT * FROM products WHERE shop_id = {} ORDER BY product_id", shop_id)
    names = {p["product_id"]: p["product_name"] for p in prods}
    routines = []
    for r in q("SELECT * FROM routines WHERE shop_id = {} ORDER BY due_minute", shop_id):
        items = [(pid, num(qty)) for pid, qty in (x.split(":") for x in r["items"].split(","))]
        routines.append({"id": r["routine_id"], "who": r["customer_name"], "label": r["schedule_label"], "due": num(r["due_minute"]),
                         "state": r["routine_state"], "reminders": num(r["reminders"]),
                         "items": [{"name": names[pid], "qty": qty} for pid, qty in items]})
    hist = {}
    for h in q("""SELECT h.cat, p.product_name, h.usual_qty FROM purchase_history h JOIN products p ON p.product_id = h.product_id
                  WHERE h.customer_id = {} AND h.shop_id = {} ORDER BY h.cat, p.product_id""", CUSTOMER_ID, shop_id):
        hist.setdefault(h["cat"], []).append({"name": h["product_name"], "qty": num(h["usual_qty"])})
    return jsonify({
        "shop": {**s, "distance_m": num(s["distance_m"]), "years_open": num(s["years_open"])},
        "products": [{"id": p["product_id"], "name": p["product_name"], "price": num(p["price"]), "cost": num(p["cost"]), "stock": num(p["stock"])} for p in prods],
        "khata": [{"who": k["customer_name"], "balance": num(k["balance"])} for k in q("SELECT * FROM khata WHERE shop_id = {} ORDER BY customer_name = 'Meena' DESC, balance DESC", shop_id)],
        "routines": routines, "history": hist, "samples": seed_data.SAMPLES.get(shop_id, {}),
        "report": report(shop_id, clock),
    })


@app.post("/api/shops/<shop_id>/onboard")
def onboard(shop_id):
    owner = (request.json or {}).get("owner_name", "").strip()
    q("UPDATE shops SET has_knode = TRUE, owner_name = COALESCE({}, owner_name) WHERE shop_id = {}", owner or None, shop_id)
    return jsonify(ok=True)


@app.post("/api/shops/<shop_id>/orders")
def create_order(shop_id):
    body = request.json or {}
    text, channel = body.get("text", "").strip(), body.get("channel", "text")
    s = q1("SELECT has_knode FROM shops WHERE shop_id = {}", shop_id)
    if not s or not s["has_knode"]:
        return err("This shop is not on Knode yet.")
    lines = parse(text, shop_id)
    if not lines:
        return jsonify(ok=False, message="Sorry, I couldn't find any of this shop's products in that. Try naming the items, like “2 milk and bread”.")
    oid = new_order_id()
    pay = "khata" if re.search(r"account|khata|credit|udhaar|udhar", text, re.I) else None
    q("INSERT INTO orders VALUES ({}, {}, {}, {}, {}, 'review', {}, 0, 0, {}, NULL)", oid, shop_id, CUSTOMER_NAME, channel, text[:2000], pay, now())
    add_items(oid, lines)
    return jsonify(ok=True, bill=bill(oid))


@app.post("/api/orders/<int:order_id>/message")
def order_message(order_id):
    """Customer replies while reviewing a bill: confirm, add or remove items."""
    t = (request.json or {}).get("text", "").strip().lower()
    o = q1("SELECT shop_id, order_state FROM orders WHERE order_id = {}", order_id)
    if not o or o["order_state"] != "review":
        return err("That bill is no longer open.")
    if re.match(r"^(confirm|ok|okay|yes|correct|done|fine)\b", t):
        return jsonify(ok=True, action="confirm", bill=bill(order_id))
    rem = re.match(r"^(remove|no|cancel|without|drop|don'?t)\b(.*)", t)
    if rem:
        ids = [line["product_id"] for line in parse(rem.group(2), o["shop_id"])]
        found = [i for i in ids if q1("SELECT 1 AS x FROM order_items WHERE order_id = {} AND product_id = {}", order_id, i)]
        if not found:
            return jsonify(ok=True, action="error", message="I couldn't find that item on your bill.")
        for i in found:
            q("DELETE FROM order_items WHERE order_id = {} AND product_id = {}", order_id, i)
        if not q1("SELECT 1 AS x FROM order_items WHERE order_id = {}", order_id):
            q("UPDATE orders SET order_state = 'cancelled' WHERE order_id = {}", order_id)
            return jsonify(ok=True, action="empty", message="Your bill is empty now. Send a new order any time.")
        recompute(order_id)
        return jsonify(ok=True, action="bill", message="Removed. Here is the updated bill:", bill=bill(order_id))
    add = re.match(r"^(add|also|plus|and|one more)\b(.*)", t)
    extra = parse(add.group(2) if add else t, o["shop_id"])
    if not extra:
        return jsonify(ok=True, action="error", message="I didn't catch that. Reply “add …”, “remove …”, or tap Confirm.")
    add_items(order_id, extra)
    return jsonify(ok=True, action="bill", message="Added. Here is the updated bill:", bill=bill(order_id))


@app.post("/api/orders/<int:order_id>/confirm")
def confirm(order_id):
    pay = (request.json or {}).get("pay_mode")
    o = q1("SELECT order_state, pay_mode FROM orders WHERE order_id = {}", order_id)
    if not o or o["order_state"] != "review":
        return err("That bill is no longer open.")
    pay = pay or o["pay_mode"]
    if pay not in ("khata", "cash"):
        return err("Choose how to pay.")
    q("UPDATE orders SET order_state = 'confirmed', pay_mode = {} WHERE order_id = {}", pay, order_id)
    return jsonify(ok=True, bill=bill(order_id))


@app.post("/api/orders/<int:order_id>/pack")
def pack(order_id):
    o = q1("SELECT shop_id, order_state FROM orders WHERE order_id = {}", order_id)
    if not o or o["order_state"] != "confirmed":
        return err("This order is not waiting to be packed.")
    ids = [r["product_id"] for r in q("SELECT product_id FROM order_items WHERE order_id = {}", order_id)]
    sell(order_id)
    b = bill(order_id)
    bal = q1("SELECT balance FROM khata WHERE shop_id = {} AND customer_name = {}", o["shop_id"], CUSTOMER_NAME)
    low = [{"name": p["product_name"], "stock": num(p["stock"])} for p in q("SELECT product_name, stock, product_id FROM products ORDER BY product_id")
           if p["product_id"] in ids and num(p["stock"]) < 6]
    return jsonify(ok=True, bill=b, khata_balance=num(bal["balance"]) if bal else 0, low_stock=low, today=today(o["shop_id"]))


@app.post("/api/routines/<routine_id>/remind")
def remind(routine_id):
    q("UPDATE routines SET reminders = reminders + 1 WHERE routine_id = {}", routine_id)
    return jsonify(ok=True)


@app.post("/api/routines/<routine_id>/deliver")
def deliver(routine_id):
    r = q1("SELECT * FROM routines WHERE routine_id = {}", routine_id)
    if not r or r["routine_state"] == "done":
        return err("Already delivered.")
    oid = new_order_id()
    q("INSERT INTO orders VALUES ({}, {}, {}, 'routine', {}, 'confirmed', 'khata', 0, 0, {}, NULL)", oid, r["shop_id"], r["customer_name"], r["items"], now())
    add_items(oid, [{"product_id": pid, "qty": float(qty), "note": "regular order"} for pid, qty in (x.split(":") for x in r["items"].split(","))])
    sell(oid)
    q("UPDATE routines SET routine_state = 'done' WHERE routine_id = {}", routine_id)
    o = q1("SELECT total FROM orders WHERE order_id = {}", oid)
    return jsonify(ok=True, amount=num(o["total"]), who=r["customer_name"])


@app.post("/api/shops/<shop_id>/command")
def command(shop_id):
    """Shop owner's own messages to the bot."""
    body = request.json or {}
    t, clock = body.get("text", "").strip().lower(), int(body.get("clock", 540))
    e = html.escape
    rs = lambda v: "₹" + f"{num(v):,}"
    k = re.match(r"^khata\s+(.+)", t)
    if k:
        row = q1("SELECT customer_name, balance FROM khata WHERE shop_id = {} AND LOWER(customer_name) LIKE {}", shop_id, "%" + k.group(1).strip() + "%")
        return jsonify(html=f"{e(row['customer_name'])} owes <b>{rs(row['balance'])}</b>." if row else f"No khata found for “{e(k.group(1))}”.")
    st = re.match(r"^stock\s+(.+)", t)
    if st:
        w = st.group(1).strip()
        rows = q("SELECT product_name, stock, price FROM products WHERE shop_id = {} AND (LOWER(product_name) LIKE {} OR cat = {}) ORDER BY product_id",
                 shop_id, "%" + w + "%", w)
        return jsonify(html="<br>".join(f"{e(p['product_name'])}: <b>{num(p['stock'])}</b> · {rs(p['price'])}" for p in rows) or f"I couldn't find “{e(w)}” in stock.")
    if re.search(r"report|profit|sales|health", t):
        r = report(shop_id, clock)
        td, o, h = r["today"], r["months"][-1], r["health"]
        issues = "<br>".join("• " + f["why"] for f in h["factors"] if f["s"] != "good") or "Everything looks good."
        return jsonify(html=f"<b>Today so far</b><br>Sales {rs(td['sales'])} · Profit {rs(td['profit'])} · {td['orders']} orders<br><br>"
                            f"<b>October</b><br>Sales {rs(o['sales'])} · Profit {rs(o['profit'])} ({round(o['profit'] / o['sales'] * 100, 1)}% margin)<br><br>"
                            f"<b>Business health: {h['score']}/100, {h['label']}</b><br>{issues}")
    return jsonify(html="Try <i>“report”</i>, <i>“stock rice”</i> or <i>“khata Meena”</i>.")


@app.post("/api/reset")
def reset():
    db.reset_database()
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
