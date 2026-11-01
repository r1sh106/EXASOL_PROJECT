# KNODE demo

Phone ordering for small neighbourhood shops. A customer picks a nearby shop, sends an order as a voice note, text or photo of a list, and the shop's helper bot turns it into a bill. The shop packs it, and credit (khata), stock, profit and the business report update. Phones are simulated in the browser.

All shops, products and brands are made up.

- **Frontend:** `static/index.html` (plain HTML, CSS and JavaScript)
- **Backend:** Flask (`app.py`)
- **Database:** Exasol Personal running locally, accessed with the official `pyexasol` driver (`db.py`)
- **Demo data:** `seed_data.py`

## 1. Install Exasol Personal (local)

Use Exasol's official launcher: https://github.com/exasol/exasol-personal

- On Windows, run these in WSL (Ubuntu, AMD64). Linux and WSL need Podman installed.
- On macOS, you need macOS 15 or later on Apple Silicon.

```bash
curl https://downloads.exasol.com/exasol-personal/installer.sh | sh
exasol version
exasol install local -d knode
```

`exasol info -d knode` shows the connection details. The database listens on `127.0.0.1:8563` with user `sys`, and the password is in `~/.exasol/personal/deployments/knode/secrets.json`.

Start and stop the database later with:

```bash
exasol stop -d knode
exasol start -d knode
```

## 2. Set up the app

```bash
pip install -r requirements.txt
copy .env.example .env      # macOS/Linux: cp .env.example .env
```

Put the password from `secrets.json` into `.env` as `EXA_PASSWORD`.

## 3. Load the demo data

```bash
python db.py
```

This creates the `KNODE` schema and fills it with 7 shops, 54 products, customer credit, regular orders and 6 months of sales. Run it again, or press **Reset demo data** in the app, to start fresh.

## 4. Run

```bash
python app.py
```

Open http://localhost:5000.

## How to demo it

1. Pick a shop in **Shops near Meena**. Shops tagged "Not on Knode yet" can't take phone orders.
2. Pick one of those and press **Sign up & create helper bot** to put it on Knode.
3. Send a sample order (voice note, text or photo), or type one. Vague words like "biscuits" or "vegetables" are matched to Meena's usual items at that shop.
4. Reply "add …" or "remove …", then confirm and choose khata or cash.
5. On the shop owner's phone, tap **Packed order**. Stock, khata and the report update from Exasol.
6. Press **+1 hour** to see reminders for regular orders. In the owner's chat, try `report`, `stock milk` or `khata Meena`.

## Tables (schema `KNODE`)

| Table | Holds |
|---|---|
| `shops` | Neighbourhood shops, distance, years open, whether they're on Knode |
| `products` | Products per shop with price, cost, stock and the words customers use for them |
| `customers`, `purchase_history` | The customer and her usual buys per shop |
| `khata` | Credit balances per shop |
| `routines` | Regular orders that trigger reminders |
| `orders`, `order_items` | Every order from the demo |
| `monthly_sales`, `top_sellers`, `today_baseline` | Report data |

## Note on certificates

The local Exasol Personal deployment uses a self-signed certificate, and its launcher says to turn off certificate validation. `db.py` does that only when the database address is `127.0.0.1` or `localhost`.
