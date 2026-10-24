pip install flask requests python-dotenv
import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load credentials from environment variables for security
# (Set these in your OS environment or .env file)
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "YOUR_PERMANENT_OR_TEMP_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "YOUR_PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "my_secure_verify_token")

GRAPH_API_VERSION = "v21.0"
WHATSAPP_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/messages"

# Simple in-memory session store to keep track of user conversation states
# Format: { "phone_number": {"step": "ASKED_ITEM", "item": None} }
user_sessions = {}

def send_whatsapp_message(recipient_phone, message_text):
    """Sends a text message back to the user via WhatsApp Cloud API."""
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient_phone,
        "type": "text",
        "text": {"preview_url": False, "body": message_text},
    }
    
    response = requests.post(WHATSAPP_URL, json=payload, headers=headers)
    if response.status_code != 200:
        print(f"Failed to send message: {response.text}")
    return response.json()


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """Handles the webhook verification handshake with Meta."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            return "Verification token mismatch", 403
    return "Invalid verification request", 400


@app.route("/webhook", methods=["POST"])
def receive_message():
    """Receives incoming messages from users and executes chatbot logic."""
    body = request.get_json()

    # Check if the incoming payload is a WhatsApp status update or message
    try:
        if (
            body.get("object")
            and body.get("entry")
            and body["entry"][0].get("changes")
            and body["entry"][0]["changes"][0].get("value").get("messages")
        ):
            change_value = body["entry"][0]["changes"][0]["value"]
            message_data = change_value["messages"][0]
            
            sender_phone = message_data["from"]  # Customer's WhatsApp phone number
            message_body = message_data.get("text", {}).get("body", "").strip()

            if not message_body:
                return jsonify({"status": "ignored"}), 200

            # --- Chatbot Flow Logic ---
            user_state = user_sessions.get(sender_phone, {"step": "WELCOME", "item": None})

            if user_state["step"] == "WELCOME" or message_body.lower() in ["hi", "hello", "menu", "start"]:
                user_sessions[sender_phone] = {"step": "WAITING_FOR_ORDER", "item": None}
                send_whatsapp_message(
                    sender_phone, 
                    "Welcome to *QuickBite Store*! 🍔\nWhat would you like to order today? Please type your item/dish name:"
                )

            elif user_state["step"] == "WAITING_FOR_ORDER":
                user_sessions[sender_phone] = {"step": "WAITING_FOR_TIME", "item": message_body}
                send_whatsapp_message(
                    sender_phone, 
                    f"Great choice! You selected: *{message_body}*.\nWhen would you like it delivered? (e.g., 'As soon as possible', or 'Today at 7:30 PM')"
                )

            elif user_state["step"] == "WAITING_FOR_TIME":
                ordered_item = user_state["item"]
                delivery_time = message_body
                
                # Clear session state / complete order
                user_sessions.pop(sender_phone, None)
                
                confirmation_msg = (
                    f"✅ *Order Confirmed!*\n\n"
                    f"🍔 *Item:* {ordered_item}\n"
                    f"⏰ *Delivery Time:* {delivery_time}\n\n"
                    f"Thank you for ordering with us! We will notify you when it's on the way."
                )
                send_whatsapp_message(sender_phone, confirmation_msg)

            else:
                user_sessions[sender_phone] = {"step": "WAITING_FOR_ORDER", "item": None}
                send_whatsapp_message(
                    sender_phone, 
                    "Let's start over. What item would you like to order?"
                )

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"Error processing webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    # Run the Flask app on port 5000 (Use ngrok or a public URL to expose it to Meta)
    app.run(port=5000, debug=True)
