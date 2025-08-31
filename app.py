from flask import Flask, render_template, request, jsonify
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

app = Flask(__name__)

# Load .env file
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

# Load portfolio info
with open("portfolio.json", "r") as f:
    portfolio_data = json.load(f)

# OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY
)

# Chat history
chat_history = []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    user_input = request.json.get("message")
    chat_history.append({"role": "user", "content": user_input})

    # Include portfolio info in context
    messages = [{"role": "system", "content": f"Use this portfolio info: {portfolio_data}"}] + chat_history

    response = client.chat.completions.create(
        model="deepseek/deepseek-chat-v3.1:free",
        messages=messages
    )

    bot_reply = response.choices[0].message.content
    chat_history.append({"role": "assistant", "content": bot_reply})
    return jsonify({"reply": bot_reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
