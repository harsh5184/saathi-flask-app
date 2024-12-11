from flask import Blueprint, jsonify, request
from firebase import db
from firebase_admin import firestore
from datetime import datetime
from google.cloud import dialogflow_v2 as dialogflow
import re


# Create a Blueprint for the chat routes
chat_bp = Blueprint("chat", __name__)

latest_number_of_tickets = []


def update_latest_ticket_count(response):
    """
    Updates the local array `latest_number_of_tickets` with the latest non-empty value
    of the 'number-of-tickets' parameter from the response.
    """
    # Extract the 'number-of-tickets' parameter value
    ticket_numbers = response.query_result.parameters.get("number-of-tickets", [])

    # If ticket numbers are found and the list is not empty, update the local array
    if ticket_numbers:
        # Update the array with the latest value
        latest_number_of_tickets[:] = (
            ticket_numbers  # Clear existing values and update with the latest
        )
        print("Updated latest_number_of_tickets:", latest_number_of_tickets)
    else:
        print("No valid number-of-tickets found, array not updated.")


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
        bot_reply, response = get_bot_response(user_message, chat_id)
        update_latest_ticket_count(response)
    except Exception as e:
        return jsonify({"error": "Failed to get bot response", "details": str(e)}), 500

    print(latest_number_of_tickets)
    # Process ticket creation on Proceed_to_Payment intent
    ticket_id = None
    if response.query_result.intent.display_name == "Proceed_to_Payment":
        try:
            print("ticket creation initiated")
            ticket_id = handle_ticket_creation(
                user_id, chat_id, latest_number_of_tickets
            )
        except Exception as e:
            return jsonify({"error": "Failed to create ticket", "details": str(e)}), 500

    # Append bot's message to chat
    bot_message = {
        "text": bot_reply,
        "sender": "bot",
        "timestamp": current_timestamp,
    }
    if ticket_id is not None:
        bot_message["ticketId"] = ticket_id
        bot_message["text"] = (
            bot_reply
            + "\n Payment Complete \n Here is your ticket for "
            + str(sum(latest_number_of_tickets))
            + " person(s)"
        )
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
    response_data = {"chatId": chat_id, "botMessage": bot_message["text"]}
    if ticket_id:
        response_data["ticketId"] = ticket_id

    return jsonify(response_data)


def get_bot_response(user_message, chat_id):
    project_id = "saathi-chat-bot-wkvw"  # Replace with your Dialogflow project ID
    session_id = chat_id  # Replace or generate a session ID
    text_input = dialogflow.TextInput(text=user_message["text"], language_code="en")
    query_input = dialogflow.QueryInput(text=text_input)

    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)

    response = session_client.detect_intent(
        request={"session": session, "query_input": query_input}
    )

    print(response.query_result.intent.display_name)

    refined_response = refine_bot_response(
        response.query_result.fulfillment_text, response
    )

    return refined_response, response


def refine_bot_response(bot_response, response):
    """
    Refines the bot's response by replacing the text from the first instance
    of any number to the last instance of a number with the sum of the tickets.
    """
    parameters = response.query_result.parameters
    ticket_numbers = parameters.get("number-of-tickets", [])

    if ticket_numbers:
        total_tickets = int(sum(ticket_numbers))
        # Update the parameters with the latest total
        response.query_result.parameters["number-of-tickets"] = [total_tickets]

        # Find the range of text containing the numbers using regex
        pattern = r"\d+(?:, \d+)*(?: and \d+)?"
        match = re.search(pattern, bot_response)

        if match:
            bot_response = (
                bot_response[: match.start()]
                + str(total_tickets)
                + bot_response[match.end() :]
            )

    return bot_response


def handle_ticket_creation(user_id, chat_id, ticket_numbers):
    """
    Handles the creation of a new ticket document in Firestore.
    """

    if not ticket_numbers:
        raise ValueError("No ticket numbers found in parameters.")

    total_tickets = sum(ticket_numbers)
    current_timestamp = datetime.utcnow().isoformat()

    # Create a new ticket document
    ticket_ref = db.collection("tickets").add(
        {
            "userId": user_id,
            "totalTickets": total_tickets,
            "timestamp": current_timestamp,
            "pricePerTicket": 100,
            "totalPrice": total_tickets * 100,
            "chatId": chat_id,
            "museum": "National Museum, New Delhi",
        }
    )
    ticket_id = ticket_ref[1].id

    # Add ticket ID to user's document
    db.collection("users").document(user_id).update(
        {
            "tickets": firestore.ArrayUnion(
                [{"ticketId": ticket_id, "timestamp": current_timestamp}]
            )
        }
    )
    # Return the ticket ID
    return ticket_id
