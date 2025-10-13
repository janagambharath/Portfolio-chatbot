# app.py
import os
import json
import time
import atexit
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, render_template, send_from_directory, g
from openai import OpenAI  # using OpenAI client pointed at openrouter (as in your original)

# ====== Configuration ======
ENV = os.getenv("FLASK_ENV", "production")
PORT = int(os.getenv("PORT", 10000))
SITE_URL = os.getenv("SITE_URL", "https://bharath-portfolio-lvea.onrender.com/")
SITE_NAME = os.getenv("SITE_NAME", "Bharath's AI Portfolio")
API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
SESSIONS_FILE = os.getenv("SESSIONS_FILE", "chat_sessions.json")
PORTFOLIO_FILE = os.getenv("PORTFOLIO_FILE", "portfolio.json")
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW_SEC", "60"))  # seconds
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "30"))  # max requests per window per IP
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "16"))
MAX_API_RETRIES = int(os.getenv("MAX_API_RETRIES", "2"))

# ====== App init ======
app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "replace-with-a-secret")

# ====== Logging ======
logger = logging.getLogger("bharath_ai_assistant")
logger.setLevel(logging.DEBUG if ENV == "development" else logging.INFO)
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
logger.addHandler(console)
file_handler = RotatingFileHandler("assistant.log", maxBytes=2_000_000, backupCount=3)
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

# ====== Simple in-memory stores ======
chat_sessions = {}           # session_id -> list of messages (dicts with role+content)
rate_limits = {}             # ip -> {"count": int, "window_start": timestamp}
startup_time = datetime.utcnow()

# ====== Load / persist portfolio ======
def load_json_file(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"{path} not found, using default.")
        return default
    except Exception as e:
        logger.exception(f"Failed to load {path}: {e}")
        return default

def save_json_file(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            return True
    except Exception as e:
        logger.exception(f"Failed to save {path}: {e}")
        return False

portfolio_data = load_json_file(PORTFOLIO_FILE, {
    "personal_info": {
        "name": "Bharath",
        "role": "Aspiring AI Engineer",
        "location": "Hyderabad, India",
        "email": "",
        "linkedin": "",
        "github": ""
    },
    "skills": ["Python", "C", "Flask", "HTML", "CSS", "AI & Chatbots", "DSA"],
    "projects": [
        {"name": "Billing System", "description": "Function-based billing system"},
        {"name": "Portfolio Website", "description": "Personal website with chatbot"}
    ]
})

# Try to restore sessions if file exists
_restored_sessions = load_json_file(SESSIONS_FILE, {})
if isinstance(_restored_sessions, dict):
    chat_sessions.update(_restored_sessions)
    logger.info(f"Restored {len(chat_sessions)} sessions from {SESSIONS_FILE}")

# Save sessions on exit
def persist_sessions_on_exit():
    try:
        save_json_file(SESSIONS_FILE, chat_sessions)
        logger.info("Chat sessions persisted on exit.")
    except Exception:
        logger.exception("Failed to persist sessions on exit.")

atexit.register(persist_sessions_on_exit)

# ====== Initialize OpenAI (OpenRouter) client ======
client = None
if API_KEY:
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=API_KEY,
        )
        logger.info("✅ OpenAI/OpenRouter client initialized")
    except Exception as e:
        logger.exception("⚠️ Failed to initialize OpenAI client: %s", e)
        client = None
else:
    logger.warning("⚠️ No API key found; AI API client not initialized. Using fallback responses.")

# ====== Utilities ======
def rate_limit():
    """Simple IP-based rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.headers.get("X-Forwarded-For", request.remote_addr)
            now = time.time()
            entry = rate_limits.get(ip)
            if not entry or now - entry["window_start"] > RATE_LIMIT_WINDOW:
                rate_limits[ip] = {"count": 1, "window_start": now}
            else:
                entry["count"] += 1
                if entry["count"] > RATE_LIMIT_MAX:
                    retry_after = int(RATE_LIMIT_WINDOW - (now - entry["window_start"]))
                    logger.warning("Rate limit exceeded for IP %s", ip)
                    return jsonify({"error": "rate_limited", "retry_after": retry_after}), 429
            return f(*args, **kwargs)
        return wrapped
    return decorator

def clean_user_input(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return text.strip()

def get_system_prompt():
    personal = portfolio_data.get("personal_info", {})
    name = personal.get("name", "Bharath")
    role = personal.get("role", "Aspiring AI Engineer")
    location = personal.get("location", "Hyderabad, India")
    email = personal.get("email", "")
    linkedin = personal.get("linkedin", "")
    github = personal.get("github", "")
    skills = portfolio_data.get("skills", [])
    projects = portfolio_data.get("projects", [])
    youtube = portfolio_data.get("youtube", {})

    # Keep system prompt compact but informative
    projects_text = "\n".join([f"- {p.get('name','Unknown')}: {p.get('description','')}" for p in projects])
    skills_text = ", ".join(skills)

    prompt = (
        f"You are an assistant for {name}. Keep responses friendly, conversational and concise (3-5 sentences). "
        f"Portfolio: Name: {name}; Role: {role}; Location: {location}; Email: {email}; LinkedIn: {linkedin}; GitHub: {github}. "
        f"Skills: {skills_text}. Projects:\n{projects_text}\n"
        "Guidelines: provide helpful, real-world examples when appropriate, keep answers concise, do not use markdown or bullets in the reply, and show personality."
    )
    return prompt

def get_enhanced_fallback(user_input: str) -> str:
    # Keep original fallback logic but slightly compressed
    user_lower = (user_input or "").lower()
    personal = portfolio_data.get("personal_info", {})
    name = personal.get("name", "Bharath")
    role = personal.get("role", "Aspiring AI Engineer")
    location = personal.get("location", "Hyderabad, India")
    skills = portfolio_data.get("skills", [])
    youtube = portfolio_data.get("youtube", {})

    if any(k in user_lower for k in ['portfolio', 'skills', 'experience', 'projects', 'about', 'who']):
        skills_str = ', '.join(skills[:5]) or "programming and AI"
        return (f"I'm {name}, an {role} from {location}. I'm passionate about building practical projects and learning by doing. "
                f"My skills include {skills_str}. Notable projects include a C-based billing system and this portfolio website. What would you like to know?")
    if any(k in user_lower for k in ['learn', 'study', 'how', 'advice']):
        return ("Great question! I learn best by building projects: starting with fundamentals (C for logic), then Python and Flask for web + AI. "
                "Practice, reading docs, and small projects made the biggest difference. Which skill are you focusing on?")
    if any(k in user_lower for k in ['contact', 'email', 'reach']):
        email = personal.get("email", "")
        linkedin = personal.get("linkedin", "")
        github = personal.get("github", "")
        contact_parts = []
        if email: contact_parts.append(email)
        if linkedin: contact_parts.append(linkedin)
        if github: contact_parts.append(github)
        contact = " | ".join(contact_parts) if contact_parts else "No public contact configured."
        return f"You can reach me here: {contact}"
    if any(k in user_lower for k in ['youtube', 'channel', 'videos', 'content']):
        channel = youtube.get("channel_name", "Bharath Ai")
        focus = youtube.get("focus", "AI and Python tutorials")
        return (f"I run '{channel}' focusing on {focus}. I make project-based tutorials to help learners become LLM engineers.")
    # default friendly fallback
    return (f"Hi — I'm {name}'s AI assistant. I can talk about programming, portfolios, projects and learning strategies. "
            "Ask me anything about tech or projects and I'll help!")

# ====== AI API call with retry ======
def call_ai_api(messages):
    if not client:
        raise RuntimeError("API client not configured")
    last_err = None
    for attempt in range(1, MAX_API_RETRIES + 2):
        try:
            logger.debug("Calling AI API (attempt %d) with %d messages", attempt, len(messages))
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": SITE_URL,
                    "X-Title": SITE_NAME,
                },
                model="deepseek/deepseek-chat-v3.1:free",
                messages=messages,
                max_tokens=450,
                temperature=0.7,
            )
            # compat with returned structure
            reply = completion.choices[0].message.content
            logger.debug("AI API success - reply length %d", len(reply or ""))
            return reply
        except Exception as e:
            last_err = e
            logger.warning("AI API attempt %d failed: %s", attempt, e)
            time.sleep(0.5 * attempt)  # gentle backoff
    # If all retries fail
    logger.exception("All AI API attempts failed: %s", last_err)
    raise last_err

# ====== Routes ======

@app.route("/googlefa59b4f8aa3dd794.html")
def google_verify():
    # serve verification file if present in static/
    return send_from_directory("static", "googlefa59b4f8aa3dd794.html")

@app.route("/")
def index():
    try:
        return render_template("index.html")
    except Exception as e:
        logger.exception("Template render failed: %s", e)
        personal = portfolio_data.get("personal_info", {})
        name = personal.get("name", "Bharath")
        role = personal.get("role", "Aspiring AI Engineer")
        skills = portfolio_data.get("skills", [])
        return f"""
        <!doctype html>
        <html>
          <head><meta charset="utf-8"><title>{name} - AI Assistant</title></head>
          <body style="font-family: Arial; background:#f6f6f6; padding:30px; text-align:center;">
            <h1>🤖 {name}'s AI Assistant</h1>
            <p style="color:#555">{role}</p>
            <p>Top skills: {', '.join(skills[:5])}</p>
            <p><a href="/health">Health</a> • <a href="/portfolio">Portfolio JSON</a></p>
          </body>
        </html>
        """

@app.route("/health")
def health():
    personal = portfolio_data.get("personal_info", {})
    name = personal.get("name", "Bharath")
    projects = portfolio_data.get("projects", [])
    skills = portfolio_data.get("skills", [])
    uptime = (datetime.utcnow() - startup_time).total_seconds()
    return jsonify({
        "status": "healthy",
        "api_configured": bool(client),
        "portfolio_name": name,
        "projects_count": len(projects),
        "skills_count": len(skills),
        "client_type": "OpenAI SDK (via OpenRouter)" if client else None,
        "uptime_seconds": int(uptime),
        "server_time_utc": datetime.utcnow().isoformat() + "Z"
    })

@app.route("/portfolio")
def portfolio():
    return jsonify(portfolio_data)

@app.route("/sessions")
def sessions_debug():
    # lightweight debugging endpoint (do not expose in production without auth)
    return jsonify({
        "session_count": len(chat_sessions),
        "sessions": {k: len(v) for k, v in chat_sessions.items()}
    })

@app.route("/ask", methods=["POST"])
@rate_limit()
def ask():
    """
    Main chat endpoint (JSON).
    Request: { "message": "<text>", "session_id": "<optional>" }
    Response: { "reply": "<text>", "session_id": "<id>", "status": "success|fallback|error" }
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        user_input = clean_user_input(data.get("message", ""))
        if not user_input:
            return jsonify({"error": "message_required"}), 400

        session_id = data.get("session_id") or f"session_{int(time.time()*1000)}"
        # initialize session if new
        session = chat_sessions.setdefault(session_id, [])
        if len(session) > MAX_HISTORY_TURNS:
            session = session[-MAX_HISTORY_TURNS:]
            chat_sessions[session_id] = session

        # append user turn
        session.append({"role": "user", "content": user_input, "ts": datetime.utcnow().isoformat()})
        logger.info("Received message for session %s: %s", session_id, (user_input[:200] + "...") if len(user_input)>200 else user_input)

        bot_reply = ""
        api_success = False

        if client:
            try:
                # build messages: system + last few turns
                messages = [{"role": "system", "content": get_system_prompt()}] + [
                    {"role": m.get("role"), "content": m.get("content")} for m in session[-MAX_HISTORY_TURNS:]
                ]
                bot_reply = call_ai_api(messages)
                api_success = True
            except Exception as e:
                logger.warning("API failed, falling back: %s", e)
                bot_reply = get_enhanced_fallback(user_input)
                api_success = False
        else:
            logger.info("No API client - using fallback")
            bot_reply = get_enhanced_fallback(user_input)

        # append assistant message
        session.append({"role": "assistant", "content": bot_reply, "ts": datetime.utcnow().isoformat()})
        # keep trimmed
        if len(session) > MAX_HISTORY_TURNS:
            chat_sessions[session_id] = session[-MAX_HISTORY_TURNS:]

        # optionally persist sessions every N messages (lightweight)
        if len(session) % 6 == 0:
            save_json_file(SESSIONS_FILE, chat_sessions)

        return jsonify({
            "reply": bot_reply,
            "session_id": session_id,
            "status": "success" if api_success else "fallback"
        })
    except Exception as e:
        logger.exception("Unhandled error in /ask: %s", e)
        # return friendly assistant message on error (200 to avoid client-side crashes)
        personal = portfolio_data.get("personal_info", {})
        name = personal.get("name", "Bharath")
        fallback = (f"Hi! I'm {name}'s AI assistant. Something went wrong handling your request, but I'm here to help — try asking again. "
                    "If the problem persists, check the server logs.")
        return jsonify({"reply": fallback, "status": "error"}), 200

# ====== Run ======
if __name__ == "__main__":
    personal = portfolio_data.get("personal_info", {})
    logger.info("🚀 Starting %s's AI Assistant", personal.get("name", "Bharath"))
    logger.info("🔑 API configured: %s", bool(client))
    app.run(host="0.0.0.0", port=PORT, debug=(ENV == "development"))
