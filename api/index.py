from flask import Flask, jsonify, request
from flask_cors import CORS  # Import CORS
import os
from firebase import db
from chat import chat_bp

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "saathi-chat-bot-wkvw-0a3188b551b8.json"


app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

app.register_blueprint(chat_bp)


@app.route("/")
def home():
    return "Hello from home second update"


@app.route("/about")
def about():
    return "This is the about page."


@app.route("/ticket/<ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    try:
        # Retrieve ticket details from Firestore
        ticket_ref = db.collection("tickets").document(ticket_id)
        ticket = ticket_ref.get()

        if ticket.exists:
            return jsonify(ticket.to_dict()), 200
        else:
            return jsonify({"error": "Ticket not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
