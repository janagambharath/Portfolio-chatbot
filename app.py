# app.py
"""
Flask chatbot server using OpenRouter (deepseek/deepseek-chat-v3.1:free).

Environment variables:
- OPENROUTER_API_KEY  (required to use the API; app runs with fallback if missing)
- PORT                (optional, default 10000)
- SITE_URL            (optional, used as HTTP-Referer header)
- SITE_NAME           (optional, used as X-Title header)
- PORTFOLIO_FILE      (optional, default portfolio.json)
- SESSIONS_FILE       (optional, default chat_sessions.json)

Run:
    python app.py
"""

import os
import json
import time
import atexit
import logging
from datetime import datetime
from functools import wraps

import requests
from flask import Flask, request, jsonify, render_template, send_from_directory

# ---- Configuration ----
PORT = int(os.getenv("PORT", 10000))
SITE_URL = os.getenv("SITE_URL", "https://bharath-portfolio-lvea.onrender.com/")
SITE_NAME = os.getenv("SITE_NAME", "Bharath's AI Portfolio")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
PORTFOLIO_FILE = os.getenv("PORTFOLIO_FILE", "portfolio.json")
SESSIONS_FILE = os.getenv("SESSIONS_FILE", "chat_sessions.json")
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "16"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW_SEC", "60"))
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "30"))

# ---- Logging ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("bharath_ai_app")

# ---- App init ----
app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["JSON_SORT_KEYS"] = False

# ---- In-memory stores ----
chat_sessions = {}
rate_limits = {}
startup_time = datetime.utcnow()

# ---- Helpers: load/save JSON ----
def load_json_file(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.info("File not found: %s (using default)", path)
        return default
    except Exception as e:
        logger.exception("Error loading %s: %s", path, e)
        return default

def save_json_file(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.exception("Failed to save %s: %s", path, e)
        return False

# ---- Load portfolio ----
default_portfolio = {
    "personal_info": {
        "name": "Bharath",
        "role": "Aspiring AI Engineer",
        "location": "Hyderabad, India",
        "email": "janagambharath1107@gmail.com",
        "linkedin": "https://www.linkedin.com/in/janagam-bharath-9ab1b235b/",
        "github": "https://github.com/janagambharath"
    },
    "skills": ["Python", "C", "Flask", "HTML", "CSS", "AI & Chatbots", "DSA"],
    "projects": [
        {"name": "Billing System", "description": "Function-based billing system"},
        {"name": "Portfolio Website", "description": "Personal website with chatbot"}
    ],
    "youtube": {"channel_name": "Bharath Ai", "focus": "AI and Python tutorials"}
}

portfolio_data = load_json_file(PORTFOLIO_FILE, default_portfolio)

# Try restore sessions on startup
_restored = load_json_file(SESSIONS_FILE, {})
if isinstance(_restored, dict):
    chat_sessions.update(_restored)
    logger.info("Restored %d sessions from %s", len(chat_sessions), SESSIONS_FILE)

# Persist sessions on exit
def persist_sessions_on_exit():
    save_json_file(SESSIONS_FILE, chat_sessions)
    logger.info("Persisted chat sessions to %s", SESSIONS_FILE)

atexit.register(persist_sessions_on_exit)

# ---- Rate limiting decorator (simple IP-based in-memory) ----
def rate_limit():
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
                    return jsonify({"error": "rate_limited", "retry_after": retry_after}), 429
            return f(*args, **kwargs)
        return wrapped
    return decorator

# ---- System prompt & fallback ----
def get_system_prompt():
    p = portfolio_data.get("personal_info", {})
    name = p.get("name", "Bharath")
    role = p.get("role", "Aspiring AI Engineer")
    location = p.get("location", "Hyderabad, India")
    email = p.get("email", "")
    linkedin = p.get("linkedin", "")
    github = p.get("github", "")
    skills = portfolio_data.get("skills", [])
    projects = portfolio_data.get("projects", [])
    youtube = portfolio_data.get("youtube", {})

    proj_text = "\n".join([f"- {p.get('name','Unknown')}: {p.get('description','')}" for p in projects])
    skills_text = ", ".join(skills)

    prompt = (
        f"You are {name}'s AI assistant. Keep responses friendly and concise (3-5 sentences).\n\n"
        f"Portfolio Information:\n"
        f"- Name: {name}\n- Role: {role}\n- Location: {location}\n- Email: {email}\n- LinkedIn: {linkedin}\n- GitHub: {github}\n\n"
        f"Skills: {skills_text}\n\n"
        f"Projects:\n{proj_text}\n\n"
        f"YouTube Channel: {youtube.get('channel_name','')} - {youtube.get('focus','')}\n\n"
        "Guidelines: Be helpful and enthusiastic. Do not use markdown. Keep answers natural and conversational."
    )
    return prompt

def get_enhanced_fallback(user_input):
    personal = portfolio_data.get("personal_info", {})
    name = personal.get("name", "Bharath")
    role = personal.get("role", "Aspiring AI Engineer")
    location = personal.get("location", "Hyderabad, India")
    skills = portfolio_data.get("skills", [])
    youtube = portfolio_data.get("youtube", {})

    text = (user_input or "").lower()
    if any(k in text for k in ["portfolio", "skills", "projects", "about", "who"]):
        skills_short = ", ".join(skills[:6]) if skills else "programming and AI"
        return f"I'm {name}, an {role} based in {location}. I build practical projects and focus on learning-by-doing. My skills include {skills_short}. Ask me about a specific project or skill!"
    if any(k in text for k in ["learn", "study", "how", "advice"]):
        return "I learn best with projects — start with the basics, build small apps, and gradually increase complexity. Ask me for a step-by-step plan for any topic."
    if any(k in text for k in ["contact", "email", "reach"]):
        email = personal.get("email", "")
        linkedin = personal.get("linkedin", "")
        return f"You can reach me at {email} or via LinkedIn: {linkedin}."
    if any(k in text for k in ["youtube", "channel", "videos"]):
        return f"I run a YouTube channel called '{youtube.get('channel_name','Bharath Ai')}' focused on {youtube.get('focus','AI & Python tutorials')}."
    return f"Hi — I'm {name}'s AI assistant. I can help with projects, learning plans, or portfolio info. What would you like to know?"

# ---- OpenRouter API call (requests) ----
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def call_openrouter_api(messages, model="deepseek/deepseek-chat-v3.1:free", max_tokens=400, temperature=0.7, timeout=15):
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not configured")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # optional but helpful for OpenRouter ranking/analytics
        "HTTP-Referer": SITE_URL,
        "X-Title": SITE_NAME
    }

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=timeout)
    if resp.status_code != 200:
        # include body for debugging
        text = resp.text
        logger.warning("OpenRouter API error %s: %s", resp.status_code, text[:400])
        raise RuntimeError(f"OpenRouter API error {resp.status_code}: {text[:200]}")

    data = resp.json()

    # Try several common shapes to extract reply safely
    # Preferred: choices[0].message.content
    try:
        choices = data.get("choices")
        if choices and isinstance(choices, list):
            first = choices[0]
            # new-style: first['message']['content']
            msg = first.get("message", {}) or {}
            if isinstance(msg, dict) and msg.get("content"):
                return msg["content"]
            # sometimes content in 'text' or 'output'
            if first.get("text"):
                return first["text"]
            if first.get("output"):
                if isinstance(first["output"], str):
                    return first["output"]
                # output might be dict/array - try to stringify shortest useful
                return json.dumps(first["output"]) 
    except Exception as e:
        logger.debug("Error parsing choices: %s", e)

    # fallback: try top-level 'output' or 'message'
    if data.get("output"):
        if isinstance(data["output"], str):
            return data["output"]
        return json.dumps(data["output"])
    if data.get("message"):
        if isinstance(data["message"], str):
            return data["message"]
        return json.dumps(data["message"])

    # last resort
    raise RuntimeError("Unexpected OpenRouter response shape")

# ---- Routes ----
@app.route("/googlefa59b4f8aa3dd794.html")
def google_verify():
    return send_from_directory("static", "googlefa59b4f8aa3dd794.html")

@app.route("/")
def index():
    try:
        return render_template("index.html")
    except Exception as e:
        logger.exception("Template error: %s", e)
        personal = portfolio_data.get("personal_info", {})
        name = personal.get("name", "Bharath")
        role = personal.get("role", "Aspiring AI Engineer")
        skills = portfolio_data.get("skills", [])
        return f"""
        <!doctype html><html><head><meta charset='utf-8'><title>{name} Chatbot</title></head><body style='font-family:Arial;padding:40px;text-align:center;'>
        <h1>🤖 {name}'s AI Assistant</h1><p>{role}</p><p>Top skills: {', '.join(skills[:5])}</p><a href='/health'>Health</a></body></html>
        """

@app.route("/health")
def health():
    personal = portfolio_data.get("personal_info", {})
    name = personal.get("name", "Bharath")
    projects = portfolio_data.get("projects", [])
    skills = portfolio_data.get("skills", [])
    uptime = int((datetime.utcnow() - startup_time).total_seconds())
    return jsonify({
        "status": "healthy",
        "api_configured": bool(OPENROUTER_API_KEY),
        "portfolio_name": name,
        "projects_count": len(projects),
        "skills_count": len(skills),
        "uptime_seconds": uptime,
        "server_time_utc": datetime.utcnow().isoformat() + "Z"
    })

@app.route("/portfolio")
def portfolio():
    return jsonify(portfolio_data)

@app.route("/sessions")
def sessions():
    # For debug only - remove or protect in production
    return jsonify({"session_count": len(chat_sessions), "sessions": {k: len(v) for k, v in chat_sessions.items()}})

@app.route("/ask", methods=["POST"])
@rate_limit()
def ask():
    """
    POST /ask
    JSON input: {"message": "<text>", "session_id": "<optional>"}
    Response: {"reply": "<text>", "session_id":"<id>", "status": "success|fallback|error"}
    """
    try:
        data = request.get_json(silent=True) or {}
        user_input = (data.get("message") or "").strip()
        session_id = data.get("session_id") or f"session_{int(time.time()*1000)}"

        if not user_input:
            return jsonify({"error": "message_required"}), 400

        # init session if missing
        session = chat_sessions.setdefault(session_id, [])
        # append user turn (store only role+content)
        session.append({"role": "user", "content": user_input, "ts": datetime.utcnow().isoformat()})
        # trim
        if len(session) > MAX_HISTORY_TURNS * 2:
            session = session[-(MAX_HISTORY_TURNS):]
            chat_sessions[session_id] = session

        bot_reply = ""
        api_success = False

        if OPENROUTER_API_KEY:
            try:
                # build messages for model: system + recent turns (role/content)
                system_msg = {"role": "system", "content": get_system_prompt()}
                # include last MAX_HISTORY_TURNS turns (converted)
                recent = [{"role": m.get("role"), "content": m.get("content")} for m in session[-MAX_HISTORY_TURNS:]]
                messages = [system_msg] + recent
                logger.info("Calling OpenRouter with %d messages (session=%s)", len(messages), session_id)
                bot_reply = call_openrouter_api(messages)
                api_success = True
                logger.info("OpenRouter replied (len=%d chars)", len(bot_reply or ""))
            except Exception as e:
                logger.exception("OpenRouter API failed: %s", e)
                bot_reply = get_enhanced_fallback(user_input)
                api_success = False
        else:
            logger.info("No OPENROUTER_API_KEY - using fallback.")
            bot_reply = get_enhanced_fallback(user_input)
            api_success = False

        # append assistant reply to session
        session.append({"role": "assistant", "content": bot_reply, "ts": datetime.utcnow().isoformat()})
        # trim session
        if len(session) > MAX_HISTORY_TURNS:
            chat_sessions[session_id] = session[-MAX_HISTORY_TURNS:]

        # persist occasionally (every 6 messages)
        if len(session) % 6 == 0:
            save_json_file(SESSIONS_FILE, chat_sessions)

        return jsonify({
            "reply": bot_reply,
            "session_id": session_id,
            "status": "success" if api_success else "fallback"
        })
    except Exception as e:
        logger.exception("Unhandled error in /ask: %s", e)
        personal = portfolio_data.get("personal_info", {})
        name = personal.get("name", "Bharath")
        return jsonify({
            "reply": f"Hi! I'm {name}'s AI assistant. Something went wrong — please try again.",
            "status": "error"
        }), 200

# ---- Main ----
if __name__ == "__main__":
    personal = portfolio_data.get("personal_info", {})
    logger.info("Starting %s's AI Assistant on port %s", personal.get("name", "Bharath"), PORT)
    logger.info("OpenRouter API configured: %s", bool(OPENROUTER_API_KEY))
    app.run(host="0.0.0.0", port=PORT, debug=os.getenv("FLASK_ENV") == "development")
