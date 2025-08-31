from flask import Flask, render_template, request, Response, stream_with_context
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

# Load portfolio info
with open("portfolio.json", "r") as f:
    portfolio_data = json.load(f)

# OpenRouter client
client = OpenAI(api_key=API_KEY, base_url="https://openrouter.ai/api/v1")

chat_history = []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    user_input = request.json.get("message")
    chat_history.append({"role": "user", "content": user_input})

    messages = [{"role": "system", "content": f"Use this portfolio info: {portfolio_data}"}] + chat_history

    # Streaming response
    def generate():
        stream = client.chat.completions.stream(
            model="deepseek/deepseek-chat-v3.1:free",
            messages=messages
        )
        bot_reply = ""
        for event in stream:
            if event.type == "message":
                chunk = event.delta.get("content", "")
                bot_reply += chunk
                yield f"data: {chunk}\n\n"
        chat_history.append({"role": "assistant", "content": bot_reply})

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
