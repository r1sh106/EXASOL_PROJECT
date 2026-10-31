#pip install flask requests
import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Configuration (Use environment variables in production)
TOKEN = os.getenv("WHATSAPP_TOKEN", "YOUR_WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_ID", "YOUR_PHONE_NUMBER_ID")
VERIFY_TOKEN = "my_secure_verify_token"

# In-memory session store to track conversation state per customer phone number
# Structure: { sender_id: { "state": "...", "raw_order": "...", "location": "...", "timing": "..." } }
user_sessions = {}

# Imaginary pricing catalog for demo items
PRICE_CATALOG = {
    "milk": 3.50,
    "bread": 2.50,
    "eggs": 4.00,
    "butter": 5.00,
    "rice": 10.00,
    "sugar": 2.00,
    "default": 3.00  # Fallback price for unlisted items
}

# 1. Webhook Verification Endpoint (Required by Meta)
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Verification failed", 403
    return "Invalid request", 400

# 2. Incoming Webhook Message Listener
@app.route("/webhook", methods=["POST"])
def handle_incoming_message():
    body = request.get_json()

    try:
        if body.get("object") == "whatsapp_business_account":
            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    if "messages" in value:
                        message = value["messages"][0]
                        sender_id = message["from"]  # Customer phone number
                        message_text = message.get("text", {}).get("body", "").strip()

                        if message_text:
                            handle_conversation_flow(sender_id, message_text)
            
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "not found"}), 404
    except Exception as e:
        print(f"Webhook processing error: {e}")
        return jsonify({"status": "error"}), 500

# 3. Core Stateful Conversation Machine
def handle_conversation_flow(sender_id, text):
    session = user_sessions.get(sender_id, {"state": "IDLE"})
    state = session.get("state")

    if state == "IDLE" or state == "COMPLETED":
        # Step A: Pick up the order from the customer's initial message
        session = {
            "state": "WAITING_FOR_LOCATION",
            "raw_order": text,
            "location": None,
            "timing": None
        }
        user_sessions[sender_id] = session

        send_whatsapp_message(
            sender_id,
            f"🛒 *Order Received!*\n\nWe noted your items: *\"{text}\"*.\n\n📍 Please share your **delivery address/location** to proceed:"
        )

    elif state == "WAITING_FOR_LOCATION":
        # Step B: Collect location and ask for delivery timing
        session["location"] = text
        session["state"] = "WAITING_FOR_TIMING"
        user_sessions[sender_id] = session

        send_whatsapp_message(
            sender_id,
            "🕒 Got your location!\n\nWhen would you like your order delivered?\n(e.g., *⚡ Quick / ASAP*, *🕒 Today 6:00 PM - 8:00 PM*, or *📅 Tomorrow Morning*)"
        )

    elif state == "WAITING_FOR_TIMING":
        # Step C: Collect timing, generate itemized summary with imaginary prices, and reset session
        session["timing"] = text
        session["state"] = "COMPLETED"
        user_sessions[sender_id] = session

        summary_message = generate_order_summary(session)
        send_whatsapp_message(sender_id, summary_message)

    else:
        user_sessions[sender_id] = {"state": "IDLE"}
        send_whatsapp_message(sender_id, "Hello! Send us your grocery list or order details to get started.")

# 4. Helper: Parse items, calculate imaginary prices, and build summary
def generate_order_summary(session):
    # Split items by comma or newline
    import re
    items_list = [item.strip() for item in re.split(r',|\n', session["raw_order"]) if item.strip()]
    total_amount = 0.0
    itemized_lines = []

    for index, item in enumerate(items_list, 1):
        lower_item = item.lower()
        price = PRICE_CATALOG["default"]

        # Match keyword against imaginary pricing catalog
        for key, val in PRICE_CATALOG.items():
            if key in lower_item:
                price = val
                break
        
        total_amount += price
        itemized_lines.append(f"{index}. {item} - ${price:.2f}")

    itemized_text = "\n".join(itemized_lines)

    return (
        "📋 *FINAL ORDER SUMMARY* 📋\n\n"
        f"*Items Ordered:*\n{itemized_text}\n\n"
        f"💰 *Estimated Total:* ${total_amount:.2f}\n"
        f"📍 *Delivery Location:* {session['location']}\n"
        f"⏰ *Delivery Timing:* {session['timing']}\n\n"
        "✅ *Status:* Order registered successfully! The shopkeeper will review and dispatch your order shortly. Thank you! 🙏"
    )

# 5. Helper function to push messages via Meta Graph API
def send_whatsapp_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "text",
        "text": {"body": message_text}
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending WhatsApp message: {e.response.json() if e.response else e}")

if __name__ == "__main__":
    app.run(port=3000, debug=True)
