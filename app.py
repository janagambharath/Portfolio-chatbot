import os
import logging
from flask import Flask, render_template, request, jsonify
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.info("python-dotenv not available, using system environment variables")

# Flask app initialization
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key-2025')
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
app.config['ENV'] = os.getenv('FLASK_ENV', 'production')

# Environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
PORT = int(os.getenv("PORT", 10000))
HOST = os.getenv("HOST", "0.0.0.0")

# Initialize DeepSeek client using GitHub token
client = None
try:
    if GITHUB_TOKEN:
        from deepsake import DeepSeek  # Make sure deepsake library is installed
        client = DeepSeek(auth_token=GITHUB_TOKEN)
        logger.info("✅ DeepSeek client initialized successfully with GitHub token")
    else:
        logger.warning("⚠️ No GitHub token found - running in fallback mode")
except Exception as e:
    logger.error(f"❌ Error initializing DeepSeek client: {e}")
    client = None

# Default portfolio data
DEFAULT_PORTFOLIO = {
    "name": "AI Portfolio Assistant",
    "title": "Full Stack Developer & AI Specialist",
    "skills": ["Python", "JavaScript", "React", "Flask", "FastAPI",
               "Machine Learning", "AI Development", "Node.js", 
               "MongoDB", "PostgreSQL", "Docker", "AWS", "Git",
               "HTML/CSS", "REST APIs", "Microservices"],
    "experience": "5+ years of development experience",
    "projects": [
        {"name": "AI Chatbot Platform", "tech": "Python, OpenAI, Flask, React",
         "description": "Intelligent conversational AI system with portfolio integration"},
        {"name": "E-commerce Platform", "tech": "React, Node.js, MongoDB, Stripe",
         "description": "Full-stack shopping platform with payment integration"},
        {"name": "Data Analytics Dashboard", "tech": "Python, Pandas, Plotly, D3.js",
         "description": "Real-time data visualization and analytics tool"},
        {"name": "Task Management System", "tech": "Flask, SQLAlchemy, Bootstrap, jQuery",
         "description": "Project management tool with team collaboration"},
        {"name": "Weather Prediction API", "tech": "Python, Scikit-learn, FastAPI",
         "description": "Machine learning API for weather forecasting"}
    ],
    "education": "Computer Science & AI/ML",
    "location": "Available for remote work worldwide",
    "contact": "Available through this chat interface",
    "certifications": ["AWS Cloud Practitioner", "Google Analytics", "Python Institute PCAP"],
    "languages": ["English (Native)", "Spanish (Conversational)"]
}

# Load portfolio from file or fallback
def load_portfolio():
    try:
        if os.path.exists("portfolio.json"):
            with open("portfolio.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info("📊 Portfolio loaded from file")
                return data
        else:
            logger.info("📊 Using default portfolio")
            return DEFAULT_PORTFOLIO
    except Exception as e:
        logger.error(f"Error loading portfolio: {e}")
        return DEFAULT_PORTFOLIO

portfolio_data = load_portfolio()

# In-memory session storage
chat_sessions = {}
MAX_SESSIONS = int(os.getenv('MAX_SESSIONS', '500'))

def cleanup_old_sessions():
    if len(chat_sessions) > MAX_SESSIONS:
        keep_count = int(MAX_SESSIONS * 0.8)
        sessions_to_keep = dict(list(chat_sessions.items())[-keep_count:])
        chat_sessions.clear()
        chat_sessions.update(sessions_to_keep)
        logger.info(f"🧹 Cleaned up sessions, keeping {len(chat_sessions)} sessions")

# System prompt
def create_system_prompt():
    return f"""You are an advanced AI assistant. Use portfolio info when relevant.
Portfolio data: {json.dumps(portfolio_data)}"""

# Fallback response if API unavailable
def get_smart_fallback_response(user_input):
    user_lower = user_input.lower()
    programming_keywords = ['code', 'programming', 'python', 'javascript', 'react', 'flask', 'html', 'css', 'debug', 'function', 'algorithm']
    if any(k in user_lower for k in programming_keywords):
        return "💻 I can help with Python, Flask, React, debugging, and more! Please ask a specific programming question."
    portfolio_keywords = ['portfolio', 'skills', 'experience', 'projects', 'background', 'about you', 'resume', 'cv', 'work']
    if any(k in user_lower for k in portfolio_keywords):
        skills_text = ', '.join(portfolio_data['skills'])
        projects_text = '\n'.join([f"{p['name']}: {p['description']}" for p in portfolio_data['projects']])
        return f"📋 Portfolio Info:\nSkills: {skills_text}\nProjects:\n{projects_text}"
    return f"🤖 Currently offline. You asked: '{user_input}'. I can still give programming, portfolio, or career guidance."

# Routes
@app.route("/")
def index():
    try:
        return render_template("index.html")
    except Exception as e:
        logger.error(f"Error serving index: {e}")
        return "<h1>AI Portfolio Assistant</h1><p>Template not found.</p>"

@app.route("/ask", methods=["POST"])
def ask():
    try:
        if len(chat_sessions) > 100:
            cleanup_old_sessions()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data"}), 400
        
        user_input = data.get("message", "").strip()
        session_id = data.get("session_id", f"session_{int(datetime.now().timestamp())}")
        if not user_input:
            return jsonify({"error": "Message cannot be empty"}), 400
        
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        chat_sessions[session_id].append({"role": "user", "content": user_input})
        
        bot_reply = ""
        api_success = False
        
        if client:
            try:
                messages = [{"role": "system", "content": create_system_prompt()}]
                recent_messages = chat_sessions[session_id][-10:]
                for msg in recent_messages:
                    messages.append({"role": msg["role"], "content": msg["content"]})
                
                response = client.chat(messages=messages, max_tokens=600, temperature=0.7)
                bot_reply = response['choices'][0]['message']['content'].strip()
                api_success = True
            except Exception as api_error:
                logger.error(f"API Error: {api_error}")
                bot_reply = get_smart_fallback_response(user_input)
        else:
            bot_reply = get_smart_fallback_response(user_input)
        
        chat_sessions[session_id].append({"role": "assistant", "content": bot_reply})
        if len(chat_sessions[session_id]) > 50:
            chat_sessions[session_id] = chat_sessions[session_id][-50:]
        
        return jsonify({
            "reply": bot_reply,
            "session_id": session_id,
            "status": "success" if api_success else "fallback",
            "api_available": api_success,
            "message_count": len(chat_sessions[session_id])
        })
    except Exception as e:
        logger.error(f"/ask error: {e}")
        return jsonify({"reply": "❌ Error occurred, fallback mode.", "status": "error"}), 500

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "api_available": bool(client),
        "active_sessions": len(chat_sessions),
        "timestamp": datetime.now().isoformat()
    })

@app.route("/portfolio")
def portfolio():
    return jsonify({"portfolio": portfolio_data, "timestamp": datetime.now().isoformat()})

# Run app
if __name__ == "__main__":
    logger.info(f"Starting server on {HOST}:{PORT} (API available: {bool(client)})")
    app.run(host=HOST, port=PORT, debug=app.config['DEBUG'])
