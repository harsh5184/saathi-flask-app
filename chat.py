from flask import Blueprint, jsonify, request
from firebase import db
from firebase_admin import firestore
from datetime import datetime

# Create a Blueprint for the chat routes
chat_bp = Blueprint("chat", __name__)


# /chat route
@chat_bp.route("/chat", methods=["POST"])
def handle_chat():
    data = request.get_json()
    user_id = data["userId"]
    user_message = data["message"]["text"]
    chat_id = data.get("chatId")

    # Validate user ID (optional but recommended)
    user_ref = db.collection("users").document(user_id).get()
    if not user_ref.exists:
        return jsonify({"error": "Invalid user ID"}), 400

    current_timestamp = datetime.utcnow().isoformat()
    # If no chat ID, create a new chat document
    if not chat_id:
        chat_ref = db.collection("chats").add(
            {"userId": user_id, "messages": [], "timestamp": current_timestamp}
        )
        chat_id = chat_ref[1].id

        # Add chat ID to user's document
        db.collection("users").document(user_id).update(
            {
                "chats": firestore.ArrayUnion(
                    [{"chatId": chat_id, "timestamp": current_timestamp}]
                )
            }
        )

    print(current_timestamp)

    user_message = {
        "text": user_message,
        "sender": "user",
        "timestamp": current_timestamp,
    }
    # Append the user's message to the chat document
    db.collection("chats").document(chat_id).update(
        {"messages": firestore.ArrayUnion([user_message])}
    )

    # Get bot reply (Handle errors if Dialogflow is unavailable)
    try:
        bot_reply = get_bot_response(user_message)
    except Exception as e:
        return jsonify({"error": "Failed to get bot response", "details": str(e)}), 500

    # Append bot's message to chat
    bot_message = {
        "text": bot_reply,
        "sender": "bot",
        "timestamp": current_timestamp,
    }
    try:
        db.collection("chats").document(chat_id).update(
            {"messages": firestore.ArrayUnion([bot_message])}
        )
    except Exception as e:
        return (
            jsonify({"error": "Failed to append bot response", "details": str(e)}),
            500,
        )

    # Return response to the frontend
    return jsonify({"chatId": chat_id, "botMessage": bot_reply})


# Helper function to get bot response from Dialogflow
def get_bot_response(user_message):
    # Set up Dialogflow API call here to send the user_message and get a response
    # Example of making a request to Dialogflow and handling the reply
    return (
        "This is a response from Dialogflows."  # Replace with actual Dialogflow logic
    )
