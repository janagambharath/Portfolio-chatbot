import os
import json
import time
import atexit
import logging
import uuid
from datetime import datetime
from functools import wraps

import requests
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

# ---- Configuration ----
PORT = int(os.getenv("PORT", 10000))
SITE_URL = os.getenv("SITE_URL", "https://bharath-portfolio-lvea.onrender.com/")
SITE_NAME = os.getenv("SITE_NAME", "Bharath's AI Portfolio")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.2-3b-instruct:free")
PORTFOLIO_FILE = os.getenv("PORTFOLIO_FILE", "portfolio.json")
SESSIONS_FILE = os.getenv("SESSIONS_FILE", "chat_sessions.json")
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "8"))  # 8 turns = 16 messages
MAX_SESSIONS = int(os.getenv("MAX_SESSIONS", "1000"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW_SEC", "60"))
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "30"))

# ---- Logging ----
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log") if os.getenv("LOG_FILE") else logging.NullHandler()
    ]
)
logger = logging.getLogger("bharath_ai_app")

# ---- App init ----
app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["JSON_SORT_KEYS"] = False
CORS(app)  # ✅ FIX: Enable CORS for cross-origin requests

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
        "name": "Janagam Bharath",
        "role": "AI / LLM Engineer",
        "location": "Hyderabad, India",
        "email": "janagambharath1107@gmail.com",
        "linkedin": "https://www.linkedin.com/in/janagam-bharath-9ab1b235b/",
        "github": "https://github.com/janagambharath"
    },
    "skills": {"all_skills": ["Python", "Flask", "AI", "NLP", "RAG", "Vector Databases"]},
    "projects": [],
    "youtube": {"channel_name": "Bharath AI", "focus": "AI and LLM tutorials"}
}

portfolio_data = load_json_file(PORTFOLIO_FILE, default_portfolio)

# Restore sessions on startup
_restored = load_json_file(SESSIONS_FILE, {})
if isinstance(_restored, dict):
    chat_sessions.update(_restored)
    logger.info("Restored %d sessions from %s", len(chat_sessions), SESSIONS_FILE)

# Persist sessions on exit
def persist_sessions_on_exit():
    save_json_file(SESSIONS_FILE, chat_sessions)
    logger.info("Persisted chat sessions to %s", SESSIONS_FILE)

atexit.register(persist_sessions_on_exit)

# ---- Rate limiting decorator ----
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
                    logger.warning(f"Rate limit exceeded for IP: {ip}")
                    return jsonify({"error": "rate_limited", "retry_after": retry_after}), 429
            return f(*args, **kwargs)
        return wrapped
    return decorator

# ---- System prompt & fallback ----
def get_system_prompt():
    p = portfolio_data.get("personal_info", {})
    name = p.get("name", "Janagam Bharath")
    role = p.get("role", "AI / LLM Engineer")
    location = p.get("location", "Hyderabad, India")
    email = p.get("email", "janagambharath1107@gmail.com")
    linkedin = p.get("linkedin", "")
    github = p.get("github", "")
    summary = p.get("summary", "")
    
    # Get skills - handle both old and new format
    skills_data = portfolio_data.get("skills", {})
    if isinstance(skills_data, dict):
        all_skills = skills_data.get("all_skills", [])
        languages = skills_data.get("languages", [])
        ai_frameworks = skills_data.get("ai_ml_frameworks", [])
        nlp = skills_data.get("nlp_concepts", [])
    else:
        all_skills = skills_data if isinstance(skills_data, list) else []
        languages = []
        ai_frameworks = []
        nlp = []
    
    # Get projects
    projects = portfolio_data.get("projects", [])
    proj_text = ""
    for proj in projects:
        name_p = proj.get("name", "Unknown Project")
        desc = proj.get("description", "")
        tech = proj.get("technologies", [])
        demo = proj.get("live_demo", "")
        proj_text += f"\n- {name_p}: {desc}"
        if tech:
            proj_text += f" | Tech: {', '.join(tech[:3])}"
        if demo:
            proj_text += f" | Demo: {demo}"
    
    # Get achievements
    achievements = portfolio_data.get("achievements", [])
    achievements_text = "\n".join([f"- {a}" for a in achievements[:4]]) if achievements else ""
    
    # Get YouTube info
    youtube = portfolio_data.get("youtube", {})
    yt_name = youtube.get("channel_name", "Bharath AI")
    yt_focus = youtube.get("focus", "AI and LLM tutorials")
    
    # Get education
    education = portfolio_data.get("education", [])
    edu_text = ""
    if education and len(education) > 0:
        edu_text = f"\n- Current: {education[0].get('degree', '')} at {education[0].get('institution', 'Hyderabad')}"
    
    skills_summary = ", ".join(all_skills[:10]) if all_skills else "Python, Flask, AI, NLP, RAG"
    
    prompt = (
        f"You are {name}'s AI assistant. Keep responses friendly, concise (3-5 sentences), and enthusiastic.\n\n"
        f"=== PORTFOLIO INFORMATION ===\n"
        f"Name: {name}\n"
        f"Role: {role}\n"
        f"Location: {location}\n"
        f"Email: {email}\n"
        f"LinkedIn: {linkedin}\n"
        f"GitHub: {github}\n"
        f"\nSummary: {summary}\n"
        f"\n=== SKILLS ===\n"
        f"Core Skills: {skills_summary}\n"
    )
    
    if languages:
        prompt += f"Languages: {', '.join(languages)}\n"
    if ai_frameworks:
        prompt += f"AI/ML: {', '.join(ai_frameworks)}\n"
    if nlp:
        prompt += f"NLP Expertise: {', '.join(nlp)}\n"
    
    prompt += f"\n=== PROJECTS ==={proj_text}\n"
    
    if achievements_text:
        prompt += f"\n=== KEY ACHIEVEMENTS ===\n{achievements_text}\n"
    
    if edu_text:
        prompt += f"\n=== EDUCATION ==={edu_text}\n"
    
    prompt += (
        f"\n=== YOUTUBE CHANNEL ===\n"
        f"Channel: {yt_name}\n"
        f"Focus: {yt_focus}\n"
        f"\n=== GUIDELINES ===\n"
        f"- Be helpful, enthusiastic, and conversational\n"
        f"- Keep answers natural and engaging (no markdown formatting)\n"
        f"- When asked about projects, mention the live demo links\n"
        f"- Highlight Bharath's expertise in AI/LLM, NLP, RAG systems, and practical deployment\n"
        f"- Emphasize his achievement of deploying 3 live AI apps before turning 18\n"
        f"- If asked technical questions, demonstrate knowledge of NLP, embeddings, vector databases, and Flask\n"
    )
    
    return prompt

def get_enhanced_fallback(user_input):
    personal = portfolio_data.get("personal_info", {})
    name = personal.get("name", "Janagam Bharath")
    role = personal.get("role", "AI / LLM Engineer")
    location = personal.get("location", "Hyderabad, India")
    
    skills_data = portfolio_data.get("skills", {})
    if isinstance(skills_data, dict):
        skills = skills_data.get("all_skills", [])
    else:
        skills = skills_data if isinstance(skills_data, list) else []
    
    projects = portfolio_data.get("projects", [])
    youtube = portfolio_data.get("youtube", {})
    achievements = portfolio_data.get("achievements", [])

    text = (user_input or "").lower()
    
    # Portfolio/About queries
    if any(k in text for k in ["portfolio", "about", "who are you", "who is", "introduce"]):
        skills_short = ", ".join(skills[:6]) if skills else "AI/ML, NLP, Flask, RAG"
        return f"Hi! I'm {name}, an {role} based in {location}. I specialize in building real-world AI applications using NLP, RAG systems, and Flask. My core skills include {skills_short}. I've deployed 3 live AI apps before turning 18! Ask me about any specific project or skill."
    
    # Skills queries
    if any(k in text for k in ["skill", "technology", "tech stack", "what do you know"]):
        if skills:
            primary = ", ".join(skills[:8])
            return f"I'm proficient in {primary}. I specialize in AI/LLM development, NLP, RAG systems, vector databases, and deploying AI apps on Hugging Face Spaces and Render. Want to know more about any specific technology?"
        return "I work with Python, Flask, Hugging Face, NLP, RAG, Vector Databases, and AI deployment. Ask me about any specific skill!"
    
    # Projects queries
    if any(k in text for k in ["project", "built", "created", "work", "portfolio"]):
        if projects and len(projects) > 0:
            proj_names = [p.get("name", "") for p in projects[:3]]
            return f"I've built several AI projects including {', '.join(proj_names)}. My most notable work includes Rythu AI (crop disease detection), Memory to Lyrics Generator (multilingual AI), and this Portfolio Chatbot! Which project would you like to know more about?"
        return "I've built AI projects including crop disease detection, multilingual lyrics generators, and AI chatbots. Ask me about any specific project!"
    
    # Learning/Education queries
    if any(k in text for k in ["learn", "study", "education", "how did you", "advice"]):
        return "I'm currently pursuing Diploma in ECE and planning B.Tech in CSE. I learn through building real projects — that's how I mastered NLP, RAG, and LLM development. My approach: start with basics, build small projects, and scale up. Want a learning roadmap for AI/ML?"
    
    # Contact queries
    if any(k in text for k in ["contact", "email", "reach", "hire"]):
        email = personal.get("email", "")
        linkedin = personal.get("linkedin", "")
        github = personal.get("github", "")
        return f"You can reach me at {email}. Connect with me on LinkedIn: {linkedin} or check my GitHub: {github}. I'm open to AI/ML opportunities and collaborations!"
    
    # YouTube queries
    if any(k in text for k in ["youtube", "channel", "videos", "tutorial"]):
        yt_name = youtube.get("channel_name", "Bharath AI")
        yt_focus = youtube.get("focus", "AI and LLM tutorials")
        return f"I run '{yt_name}' on YouTube, where I teach {yt_focus}. The goal is to help people become LLM Engineers through practical, project-based learning. Check it out!"
    
    # Achievements/Goals
    if any(k in text for k in ["achievement", "goal", "future", "plan", "proud"]):
        if achievements:
            return f"I'm proud to have {achievements[0].lower()}. My goal is to become a top AI/LLM Engineer, build production-ready RAG systems, and help others learn AI through my YouTube channel. I focus on solving real-world problems with AI!"
        return "I've deployed 3 live AI apps before 18! My goal is to master LLM engineering, build impactful AI products, and teach AI through YouTube."
    
    # Technical queries
    if any(k in text for k in ["rag", "vector", "embedding", "nlp", "llm", "hugging face", "fine-tun"]):
        return "I work extensively with RAG systems, vector databases, embeddings, and NLP pipelines. I use Hugging Face for model deployment, implement TF-IDF, tokenization, and embedding-based retrieval. I'm also learning fine-tuning techniques for LLMs. What specific technical topic interests you?"
    
    # Default friendly response
    return f"Hi! I'm {name}'s AI assistant. I can tell you about my AI/ML projects, NLP expertise, skills in RAG systems, or my YouTube channel. I've built 3 live AI applications and love teaching AI concepts. What would you like to know?"

# ---- OpenRouter API call (requests) ----
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def call_openrouter_api(messages, model=None, max_tokens=800, temperature=0.7, timeout=30):
    """
    ✅ FIXED: Better error handling, timeout increased, detailed error messages
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not configured")

    if model is None:
        model = DEFAULT_MODEL

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": SITE_URL,
        "X-Title": SITE_NAME
    }

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=timeout)
    except requests.exceptions.Timeout:
        logger.error("OpenRouter API timeout after %d seconds", timeout)
        raise RuntimeError(f"OpenRouter API timeout after {timeout} seconds")
    except requests.exceptions.ConnectionError as e:
        logger.error("OpenRouter API connection error: %s", e)
        raise RuntimeError("Cannot connect to OpenRouter API. Please check your internet connection.")
    except Exception as e:
        logger.error("OpenRouter API request error: %s", e)
        raise RuntimeError(f"OpenRouter API request failed: {str(e)}")

    # ✅ FIX: Better error handling for different status codes
    if resp.status_code != 200:
        text = resp.text
        logger.warning("OpenRouter API error %s: %s", resp.status_code, text[:400])
        
        error_msg = f"OpenRouter API error {resp.status_code}"
        if resp.status_code == 401:
            error_msg = "Invalid API key. Please check OPENROUTER_API_KEY environment variable."
        elif resp.status_code == 429:
            error_msg = "Rate limit exceeded. Please try again later."
        elif resp.status_code == 500:
            error_msg = "OpenRouter service error. Please try again."
        elif resp.status_code == 400:
            error_msg = "Bad request to OpenRouter API. Check your model name and parameters."
        
        raise RuntimeError(f"{error_msg}: {text[:200]}")

    data = resp.json()
    try:
        choices = data.get("choices")
        if choices and isinstance(choices, list):
            first = choices[0]
            msg = first.get("message", {}) or {}
            if isinstance(msg, dict) and msg.get("content"):
                return msg["content"]
            if first.get("text"):
                return first["text"]
            if first.get("output"):
                if isinstance(first["output"], str):
                    return first["output"]
                return json.dumps(first["output"])
    except Exception as e:
        logger.debug("Error parsing choices: %s", e)

    if data.get("output"):
        if isinstance(data["output"], str):
            return data["output"]
        return json.dumps(data["output"])
    if data.get("message"):
        if isinstance(data["message"], str):
            return data["message"]
        return json.dumps(data["message"])

    logger.error("Unexpected OpenRouter response: %s", json.dumps(data)[:500])
    raise RuntimeError("Unexpected OpenRouter response shape")

# ---- Session cleanup ----
def cleanup_old_sessions():
    """
    ✅ FIX: Prevent infinite session growth
    """
    global chat_sessions
    if len(chat_sessions) > MAX_SESSIONS:
        logger.info("Cleaning up old sessions (current: %d, max: %d)", len(chat_sessions), MAX_SESSIONS)
        # Sort by last message timestamp (most recent first)
        sorted_sessions = sorted(
            chat_sessions.items(), 
            key=lambda x: x[1][-1].get('ts', '') if x[1] else '', 
            reverse=True
        )
        # Keep only the most recent MAX_SESSIONS
        chat_sessions = dict(sorted_sessions[:MAX_SESSIONS])
        logger.info("Kept %d most recent sessions", len(chat_sessions))

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
        name = personal.get("name", "Janagam Bharath")
        role = personal.get("role", "AI / LLM Engineer")
        skills_data = portfolio_data.get("skills", {})
        if isinstance(skills_data, dict):
            skills = skills_data.get("all_skills", [])
        else:
            skills = skills_data if isinstance(skills_data, list) else []
        return f"""
        <!doctype html><html><head><meta charset='utf-8'><title>{name} Chatbot</title></head><body style='font-family:Arial;padding:40px;text-align:center;'>
        <h1>🤖 {name}'s AI Assistant</h1><p>{role}</p><p>Top skills: {', '.join(skills[:5])}</p><a href='/health'>Health</a></body></html>
        """

@app.route("/health")
def health():
    """
    ✅ FIX: Added API key length for debugging (without exposing the key)
    """
    personal = portfolio_data.get("personal_info", {})
    name = personal.get("name", "Janagam Bharath")
    projects = portfolio_data.get("projects", [])
    skills_data = portfolio_data.get("skills", {})
    if isinstance(skills_data, dict):
        skills_count = len(skills_data.get("all_skills", []))
    else:
        skills_count = len(skills_data) if isinstance(skills_data, list) else 0
    uptime = int((datetime.utcnow() - startup_time).total_seconds())
    
    api_configured = bool(OPENROUTER_API_KEY)
    
    # Log warning if API key not configured
    if not api_configured:
        logger.warning("Health check: OpenRouter API key NOT configured!")
    
    return jsonify({
        "status": "healthy",
        "api_configured": api_configured,
        "api_key_length": len(OPENROUTER_API_KEY) if OPENROUTER_API_KEY else 0,
        "model": DEFAULT_MODEL,
        "portfolio_name": name,
        "projects_count": len(projects),
        "skills_count": skills_count,
        "active_sessions": len(chat_sessions),
        "uptime_seconds": uptime,
        "server_time_utc": datetime.utcnow().isoformat() + "Z"
    })

@app.route("/portfolio")
def portfolio():
    return jsonify(portfolio_data)

@app.route("/sessions")
def sessions():
    return jsonify({
        "session_count": len(chat_sessions), 
        "sessions": {k: len(v) for k, v in chat_sessions.items()}
    })

@app.route("/ask", methods=["POST"])
@rate_limit()
def ask():
    """
    ✅ FIXED:
    - UUID-based session IDs (no collision)
    - Proper JSON error handling
    - Consistent session trimming (16 messages = 8 turns)
    - Request ID logging
    - Better error messages
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] New chat request")
    
    try:
        # ✅ FIX: Better JSON parsing with proper error handling
        try:
            data = request.get_json(force=True)
            if not data:
                logger.warning(f"[{request_id}] Empty JSON body")
                return jsonify({"error": "invalid_json", "message": "Request body must be valid JSON"}), 400
        except Exception as e:
            logger.error(f"[{request_id}] JSON parse error: {e}")
            return jsonify({"error": "invalid_json", "message": str(e)}), 400
        
        user_input = (data.get("message") or "").strip()
        # ✅ FIX: Use UUID for session IDs to avoid collisions
        session_id = data.get("session_id") or f"session_{uuid.uuid4().hex}"

        if not user_input:
            logger.warning(f"[{request_id}] Empty message")
            return jsonify({"error": "message_required", "message": "Message cannot be empty"}), 400

        logger.info(f"[{request_id}] Session: {session_id[:16]}..., Message: {user_input[:50]}...")

        # Get or create session
        session = chat_sessions.setdefault(session_id, [])
        
        # Add user message
        session.append({
            "role": "user", 
            "content": user_input, 
            "ts": datetime.utcnow().isoformat()
        })
        
        # ✅ FIX: Consistent session trimming (keep last 16 messages = 8 turns)
        if len(session) > MAX_HISTORY_TURNS * 2:
            session = session[-(MAX_HISTORY_TURNS * 2):]
            chat_sessions[session_id] = session
            logger.debug(f"[{request_id}] Trimmed session to {len(session)} messages")

        bot_reply = ""
        api_success = False

        if OPENROUTER_API_KEY:
            try:
                system_msg = {"role": "system", "content": get_system_prompt()}
                # ✅ FIX: Build message history correctly (last 16 messages = 8 turns)
                recent = [
                    {"role": m.get("role"), "content": m.get("content")} 
                    for m in session[-(MAX_HISTORY_TURNS * 2):]
                ]
                messages = [system_msg] + recent
                
                logger.info(f"[{request_id}] Calling OpenRouter with {len(messages)} messages")
                bot_reply = call_openrouter_api(messages)
                api_success = True
                logger.info(f"[{request_id}] OpenRouter replied ({len(bot_reply)} chars)")
                
            except Exception as e:
                logger.exception(f"[{request_id}] OpenRouter API failed: {e}")
                bot_reply = get_enhanced_fallback(user_input)
                api_success = False
                logger.info(f"[{request_id}] Using fallback response")
        else:
            logger.warning(f"[{request_id}] No OPENROUTER_API_KEY - using fallback")
            bot_reply = get_enhanced_fallback(user_input)
            api_success = False

        # Add assistant response
        session.append({
            "role": "assistant", 
            "content": bot_reply, 
            "ts": datetime.utcnow().isoformat()
        })
        
        # ✅ FIX: Consistent trimming after adding assistant message
        if len(session) > MAX_HISTORY_TURNS * 2:
            chat_sessions[session_id] = session[-(MAX_HISTORY_TURNS * 2):]

        # Periodic save and cleanup
        if len(session) % 6 == 0:
            save_json_file(SESSIONS_FILE, chat_sessions)
            cleanup_old_sessions()

        logger.info(f"[{request_id}] Request completed successfully")
        
        return jsonify({
            "reply": bot_reply,
            "session_id": session_id,
            "status": "success" if api_success else "fallback",
            "request_id": request_id
        })
        
    except Exception as e:
        logger.exception(f"[{request_id}] Unhandled error in /ask: {e}")
        personal = portfolio_data.get("personal_info", {})
        name = personal.get("name", "Janagam Bharath")
        return jsonify({
            "reply": f"Hi! I'm {name}'s AI assistant. Something went wrong — please try again.",
            "status": "error",
            "error": str(e),
            "request_id": request_id
        }), 500

# ---- Main ----
if __name__ == "__main__":
    personal = portfolio_data.get("personal_info", {})
    logger.info("=" * 60)
    logger.info("Starting %s's AI Assistant", personal.get("name", "Janagam Bharath"))
    logger.info("Port: %s", PORT)
    logger.info("OpenRouter API configured: %s", bool(OPENROUTER_API_KEY))
    if OPENROUTER_API_KEY:
        logger.info("API Key length: %d characters", len(OPENROUTER_API_KEY))
    logger.info("Default Model: %s", DEFAULT_MODEL)
    logger.info("Max History Turns: %d (= %d messages)", MAX_HISTORY_TURNS, MAX_HISTORY_TURNS * 2)
    logger.info("=" * 60)
    
    app.run(
        host="0.0.0.0", 
        port=PORT, 
        debug=os.getenv("FLASK_ENV") == "development"
    )
