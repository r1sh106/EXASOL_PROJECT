#pip install flask requests python-dotenv
import os
import requests

from flask import Flask, request, jsonify
from text_reader import process_and_store_image,init_db

init_db()

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
    """Receives incoming messages (text or images) from users and executes chatbot logic."""
    body = request.get_json() or {}

    try:
        # Validate that the incoming payload contains WhatsApp message data
        if (
            body.get("object")
            and body.get("entry")
            and body["entry"][0].get("changes")
            and body["entry"][0]["changes"][0].get("value").get("messages")
        ):
            change_value = body["entry"][0]["changes"][0]["value"]
            message_data = change_value["messages"][0]
            
            sender_phone = message_data.get("from")  # Customer's WhatsApp phone number
            msg_type = message_data.get("type")

            # --- 1. Handle Regular Text Messages ---
            if msg_type == "text":
                message_body = message_data.get("text", {}).get("body", "").strip()

                if not message_body:
                    return jsonify({"status": "ignored"}), 200

                # State Machine Logic
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

            # --- 2. Handle Image / Written Notes ---
            elif msg_type == "image":
                image_id = message_data["image"]["id"]
                
                # Fetch image download URL from Meta Graph API
                media_headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
                media_res = requests.get(
                    f"https://graph.facebook.com/{GRAPH_API_VERSION}/{image_id}", 
                    headers=media_headers
                )
                media_url = media_res.json().get("url")
                
                # Download binary image data
                img_bytes = requests.get(media_url, headers=media_headers).content
                
                # Save locally temporarily for Gemini to process
                temp_filename = f"temp_{sender_phone}.jpg"
                with open(temp_filename, "wb") as f:
                    f.write(img_bytes)
                    
                try:
                    # Run text extraction using text_reader.py
                    process_and_store_image(temp_filename)
                    send_whatsapp_message(
                        sender_phone, 
                        "📸 Got your note/image! I've extracted the text and saved it to the database."
                    )
                except Exception as e:
                    send_whatsapp_message(sender_phone, f"Sorry, I couldn't read that image: {e}")
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)

            # --- 3. Handle Unsupported Media Types ---
            else:
                send_whatsapp_message(
                    sender_phone, 
                    "Sorry, I can currently only process text messages and photos/written notes."
                )

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"Error processing webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    # Run the Flask app on port 5000 (Use ngrok or a public URL to expose it to Meta)
    app.run(port=5000, debug=True)
