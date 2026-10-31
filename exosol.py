# Install dependencies:
# pip install flask requests

import os
import re
import requests

from flask import Flask, request, jsonify

app = Flask(__name__)

# -----------------------------------------
# 1. CONFIGURATION
# -----------------------------------------

TOKEN = os.getenv(
    "WHATSAPP_TOKEN",
    "YOUR_WHATSAPP_ACCESS_TOKEN"
)

PHONE_NUMBER_ID = os.getenv(
    "WHATSAPP_PHONE_ID",
    "YOUR_PHONE_NUMBER_ID"
)

VERIFY_TOKEN = os.getenv(
    "VERIFY_TOKEN",
    "my_secure_verify_token"
)

API_VERSION = os.getenv(
    "WHATSAPP_API_VERSION",
    "v23.0"
)

# -----------------------------------------
# 2. SESSION STORAGE
# -----------------------------------------

user_sessions = {}

# -----------------------------------------
# 3. PRODUCT PRICE CATALOG
# -----------------------------------------

PRICE_CATALOG = {
    "milk": 3.50,
    "bread": 2.50,
    "eggs": 4.00,
    "butter": 5.00,
    "rice": 10.00,
    "sugar": 2.00,
    "default": 3.00
}


# -----------------------------------------
# 4. WHATSAPP WEBHOOK VERIFICATION
# -----------------------------------------

@app.route("/webhook", methods=["GET"])
def verify_webhook():

    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:

        print("Webhook verified successfully!")

        return challenge, 200

    return "Verification failed", 403


# -----------------------------------------
# 5. RECEIVE WHATSAPP MESSAGES
# -----------------------------------------

@app.route("/webhook", methods=["POST"])
def handle_incoming_message():

    body = request.get_json(silent=True)

    if not body:
        return jsonify({"status": "Invalid JSON"}), 400

    if body.get("object") != "whatsapp_business_account":
        return jsonify({"status": "Not a WhatsApp event"}), 404

    try:

        for entry in body.get("entry", []):

            for change in entry.get("changes", []):

                value = change.get("value", {})

                messages = value.get("messages", [])

                for message in messages:

                    sender_id = message.get("from")

                    if not sender_id:
                        continue

                    message_type = message.get("type")

                    if message_type == "text":

                        message_text = message.get(
                            "text", {}
                        ).get("body", "").strip()

                        if message_text:

                            print(
                                f"Message from {sender_id}: "
                                f"{message_text}"
                            )

                            handle_conversation_flow(
                                sender_id,
                                message_text
                            )

                    else:

                        send_whatsapp_message(
                            sender_id,
                            "Please send your grocery order as text."
                        )

        return jsonify({"status": "success"}), 200

    except Exception as e:

        print("Webhook processing error:", str(e))

        return jsonify({"status": "error"}), 500


# -----------------------------------------
# 6. CONVERSATION FLOW
# -----------------------------------------

def handle_conversation_flow(sender_id, text):

    session = user_sessions.get(
        sender_id,
        {"state": "IDLE"}
    )

    state = session.get("state")

    # STEP A: RECEIVE ORDER

    if state in ["IDLE", "COMPLETED"]:

        session = {
            "state": "WAITING_FOR_LOCATION",
            "raw_order": text,
            "location": None,
            "timing": None
        }

        user_sessions[sender_id] = session

        send_whatsapp_message(
            sender_id,

            f"🛒 Order Received!\n\n"
            f"We noted your items:\n"
            f"{text}\n\n"
            f"📍 Please share your delivery address:"
        )

    # STEP B: RECEIVE LOCATION

    elif state == "WAITING_FOR_LOCATION":

        session["location"] = text

        session["state"] = "WAITING_FOR_TIMING"

        user_sessions[sender_id] = session

        send_whatsapp_message(
            sender_id,

            "📍 Location received!\n\n"

            "When would you like your order delivered?\n\n"

            "1. ASAP\n"
            "2. Today Evening\n"
            "3. Tomorrow Morning\n"
            "4. Specify your preferred time"
        )

    # STEP C: RECEIVE DELIVERY TIME

    elif state == "WAITING_FOR_TIMING":

        session["timing"] = text

        session["state"] = "COMPLETED"

        user_sessions[sender_id] = session

        summary = generate_order_summary(session)

        send_whatsapp_message(
            sender_id,
            summary
        )

    else:

        user_sessions[sender_id] = {
            "state": "IDLE"
        }

        send_whatsapp_message(
            sender_id,

            "Welcome to our grocery store!\n\n"
            "Please send your grocery list to get started."
        )


# -----------------------------------------
# 7. GENERATE ORDER SUMMARY
# -----------------------------------------

def generate_order_summary(session):

    items_list = [
        item.strip()

        for item in re.split(
            r',|\n',
            session["raw_order"]
        )

        if item.strip()
    ]

    total_amount = 0.0

    itemized_lines = []

    for index, item in enumerate(items_list, 1):

        lower_item = item.lower()

        price = PRICE_CATALOG["default"]

        for key, val in PRICE_CATALOG.items():

            if key != "default" and key in lower_item:

                price = val

                break

        total_amount += price

        itemized_lines.append(
            f"{index}. {item} - ${price:.2f}"
        )

    itemized_text = "\n".join(itemized_lines)

    return (

        "📋 FINAL ORDER SUMMARY\n\n"

        f"🛒 Items Ordered:\n"
        f"{itemized_text}\n\n"

        f"💰 Estimated Total: ${total_amount:.2f}\n\n"

        f"📍 Delivery Location:\n"
        f"{session['location']}\n\n"

        f"⏰ Delivery Timing:\n"
        f"{session['timing']}\n\n"

        "✅ Order registered successfully!\n\n"

        "The shopkeeper will review your order "
        "and arrange delivery shortly.\n\n"

        "Thank you for shopping with us! 🙏"
    )


# -----------------------------------------
# 8. SEND WHATSAPP MESSAGE
# -----------------------------------------

def send_whatsapp_message(recipient_id, message_text):

    if (
        TOKEN == "YOUR_WHATSAPP_ACCESS_TOKEN"
        or PHONE_NUMBER_ID == "YOUR_PHONE_NUMBER_ID"
    ):

        print("ERROR: Configure your WhatsApp credentials.")

        return False

    url = (
        f"https://graph.facebook.com/"
        f"{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    )

    headers = {

        "Authorization": f"Bearer {TOKEN}",

        "Content-Type": "application/json"

    }

    payload = {

        "messaging_product": "whatsapp",

        "to": recipient_id,

        "type": "text",

        "text": {

            "body": message_text

        }

    }

    try:

        response = requests.post(

            url,

            json=payload,

            headers=headers,

            timeout=15

        )

        response.raise_for_status()

        print("WhatsApp message sent successfully!")

        return True

    except requests.exceptions.RequestException as e:

        print("WhatsApp API Error:", str(e))

        if e.response is not None:

            print("API Response:", e.response.text)

        return False


# -----------------------------------------
# 9. HOME ROUTE
# -----------------------------------------

@app.route("/", methods=["GET"])
def home():

    return "WhatsApp Grocery Ordering Bot is Running!"


# -----------------------------------------
# 10. RUN FLASK APPLICATION
# -----------------------------------------

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=3000,

        debug=True

    )


