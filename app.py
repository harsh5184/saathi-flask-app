from flask import Flask
import os


app = Flask(__name__)


@app.route("/")
def home():
    return "Hello from home second update"


@app.route("/about")
def about():
    return "This is the about page."


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
