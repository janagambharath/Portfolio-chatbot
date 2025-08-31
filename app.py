from flask import Flask, render_template, request, Response
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

app = Flask(__name__)

# Load .env file
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

# OpenRouter client
client = OpenAI(api_key=API_KEY, base_url="https://openrouter.ai/api/v1")

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
    messages = [{"role": "system", "content": "Use this portfolio info wisely"}] + chat_history

    def generate():
        # Stream response from Deepseek/OpenRouter
        stream = client.chat.completions.stream(
            model="deepseek/deepseek-chat-v3.1:free",
            messages=messages
        )
        for event in stream:
            if event.type == "message":
                # Send content word by word
                words = event.delta.split()
                for word in words:
                    yield word + " "
    
    return Response(generate(), mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
