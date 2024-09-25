import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate(
    "saathi-chat-bot-wkvw-firebase-adminsdk-bessw-72831bc4d3.json"
)
firebase_admin.initialize_app(cred)
db = firestore.client()
