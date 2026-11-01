# KNODE Merchant

A mobile-friendly web app for neighbourhood grocery shops. The shopkeeper shares a link. Customers open it, sign in once, and send their order as a photo of a handwritten list, a voice note, or typed text. Gemini reads the order and builds an itemised bill from the shop's catalog. The shopkeeper checks the bill, switches off anything out of stock (the customer sees this), and moves the order through the queue.

All shops, products and customers are made up.

**Built with:**
- **Backend:** Flask (`app.py`)
- **Database:** Exasol Personal running locally, through the official `pyexasol` driver (`db.py`)
- **AI:** Google Gemini through the official `google-genai` SDK (`gemini.py`), using structured JSON output
- **Frontend:** Bootstrap 5.3 with Jinja templates (`templates/`, `static/`)

## Pages and routes

| Route | What it is |
|---|---|
| `/` | Start page with links |
| `/merchant/signin` | Demo merchant sign-in (pick a shop) |
| `/dashboard` | Shop link, order queue (Pending for review / Ready to pack / Completed), daily sales, top-selling items, out-of-stock list |
| `/dashboard/order/<id>` | Merchant verification screen: itemised bill, in-stock switches, what the customer sent, Confirm / Packed / Cancel |
| `/shop/<shopID>` | Customer order page: sign in once, then upload a photo, record or upload a voice note, or type |
| `/shop/<shopID>/order/<id>` | Customer's order status and bill, refreshed every 5 seconds, with unavailable items explained |
| `POST /api/process-order` | Takes the upload, sends it to Gemini with the shop's catalog, saves the itemised bill as a pending order |

Prices always come from the shop's catalog in Exasol, never from the AI. Items the shop doesn't sell are kept on the bill as "Not sold at this shop". Items marked out of stock are left out of the total.

## Setup

### 1. Exasol Personal (local)

Use the official launcher (https://github.com/exasol/exasol-personal). On Windows, run these in WSL Ubuntu with Podman installed:

```bash
curl https://downloads.exasol.com/exasol-personal/installer.sh | sh
exasol install local -d knode
exasol info -d knode
```

The password is in `~/.exasol/personal/deployments/knode/secrets.json`.

### 2. Python packages

```bash
pip install -r requirements.txt
```

### 3. Settings

Copy `.env.example` to `.env` and fill in:

- `EXA_PASSWORD`: from `secrets.json`
- `GEMINI_API_KEY`: free key from https://aistudio.google.com/apikey
- `GEMINI_MODEL`: defaults to `gemini-3.8-flash`. Change it if Google renames the model.
- `GEMINI_FALLBACK_MODELS`: tried in order when the main model is overloaded (503) or rate-limited (429). Defaults to `gemini-3.7-flash,gemini-3.5-flash,gemini-flash-latest`. The model that read each order is shown on the verification screen.
- `FLASK_SECRET`: any long random string

Without a Gemini key, typed orders still work through a simple keyword matcher. Photos and voice notes need the key.

### 4. Load demo data, then run

```bash
python db.py
python app.py
```

Open http://localhost:5050. To try it from a phone on the same Wi-Fi, start with `HOST=0.0.0.0` and open `http://<your-computer-ip>:5050`. Phones can upload photos and audio files over plain http. Recording in the browser needs https or localhost.

## Demo walkthrough

1. Open **/merchant/signin**, pick New Wave Grocers, and copy the shop link.
2. Open the link in another browser or a private window. Sign in, for example with phone `9876500001` (Meena).
3. Send an order: photo, voice note, or typed (e.g. `2 milk, onion 2kg, coffee, paneer, mango pickle`).
4. Within 5 seconds it appears under **Pending for review** on the dashboard. Open it, switch off an item, and press **Confirm & send to packing**.
5. The customer's page shows the item as unavailable and the new total. Then press **Packed & delivered**.

## Troubleshooting

- **"Too many open connections" / Exasol licence limit:** Exasol Personal allows 20 parallel connections. The app keeps a small reusable pool, 4 by default (`EXA_POOL_SIZE` in `.env`). If you run several apps against the same database, keep their pools small, or restart the app to free its connections.
- **"Can't reach the Exasol database":** start it with `exasol start -d knode` in WSL.
- **"Gemini is busy right now":** Google's free tier is overloaded. The app already tries the fallback models, so wait a minute and send again.

## Tables (schema `KNODE_SHOP`)

| Table | Holds |
|---|---|
| `shops` | Shop details |
| `products` | Catalog per shop: name, unit, price, in stock, keywords |
| `customers` | Customers who signed in (name, phone, address) |
| `orders` | One row per order: state, channel, uploaded file, transcript, total, which model read it |
| `order_items` | Bill lines: what the customer wrote, matched product, quantity, price, available |
