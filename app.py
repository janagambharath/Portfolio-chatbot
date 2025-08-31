import os
import logging
from flask import Flask, render_template, request, jsonify
import json
from datetime import datetime
from transformers import pipeline

# Logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.info("python-dotenv not available")

# Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key')
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
app.config['ENV'] = os.getenv('FLASK_ENV', 'production')

# Environment variables
PORT = int(os.getenv("PORT", 10000))
HOST = os.getenv("HOST", "0.0.0.0")

# Initialize GPT-2 pipeline (local, free)
try:
    generator = pipeline("text-generation", model="gpt2", tokenizer="gpt2")
    logger.info("✅ GPT-2 pipeline initialized")
except Exception as e:
    logger.error(f"❌ Error initializing GPT-2: {e}")
    generator = None

# Portfolio data
DEFAULT_PORTFOLIO = {
    "name": "AI Portfolio Assistant",
    "title": "Full Stack Developer & AI Specialist",
    "skills": ["Python", "Flask", "React", "Machine Learning", "AI Development"],
    "experience": "5+ years of development experience",
    "projects": [
        {"name": "AI Chatbot", "description": "Portfolio integrated chatbot"},
        {"name": "E-commerce Platform", "description": "Full-stack shopping platform"}
    ]
}

def load_portfolio():
    try:
        if os.path.exists("portfolio.json"):
            with open("portfolio.json","r",encoding="utf-8") as f:
                return json.load(f)
        return DEFAULT_PORTFOLIO
    except:
        return DEFAULT_PORTFOLIO

portfolio_data = load_portfolio()
chat_sessions = {}
MAX_SESSIONS = int(os.getenv('MAX_SESSIONS', '500'))

def cleanup_old_sessions():
    if len(chat_sessions) > MAX_SESSIONS:
        keep_count = int(MAX_SESSIONS * 0.8)
        sessions_to_keep = dict(list(chat_sessions.items())[-keep_count:])
        chat_sessions.clear()
        chat_sessions.update(sessions_to_keep)

def create_system_prompt():
    return f"Portfolio Info: {json.dumps(portfolio_data)}"

def fallback_response(user_input):
    if any(k in user_input.lower() for k in ['portfolio','skills','projects','experience']):
        skills_text = ', '.join(portfolio_data['skills'])
        projects_text = '\n'.join([f"{p['name']}: {p['description']}" for p in portfolio_data['projects']])
        return f"📋 Skills: {skills_text}\nProjects:\n{projects_text}\nExperience: {portfolio_data['experience']}"
    return f"🤖 Currently offline. You asked: {user_input}"

# Routes
@app.route("/")
def index():
    return render_template("index.html")  # Ensure you have templates/index.html

@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json()
        user_input = data.get("message","").strip()
        session_id = data.get("session_id", f"session_{int(datetime.now().timestamp())}")

        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        chat_sessions[session_id].append({"role":"user","content":user_input})

        if generator:
            prompt = f"{create_system_prompt()}\nUser: {user_input}\nAI:"
            response = generator(prompt, max_length=150, num_return_sequences=1)
            bot_reply = response[0]['generated_text'].split("AI:")[-1].strip()
            api_success = True
        else:
            bot_reply = fallback_response(user_input)
            api_success = False

        chat_sessions[session_id].append({"role":"assistant","content":bot_reply})
        if len(chat_sessions[session_id]) > 50:
            chat_sessions[session_id] = chat_sessions[session_id][-50:]

        return jsonify({"reply":bot_reply,"session_id":session_id,"status":"success" if api_success else "fallback"})
    except Exception as e:
        logger.error(f"/ask error: {e}")
        return jsonify({"reply":"❌ Error occurred","status":"error"}),500

@app.route("/health")
def health():
    return jsonify({"status":"healthy","api_available":bool(generator),"active_sessions":len(chat_sessions)})

@app.route("/portfolio")
def portfolio():
    return jsonify({"portfolio":portfolio_data})

# Run app
if __name__ == "__main__":
    logger.info(f"Starting GPT-2 Flask server on {HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=app.config['DEBUG'])
