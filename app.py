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
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "6"))  # Reduced from 8
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
CORS(app)

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

# ---- ✅ FIXED: Concise System Prompt (under 500 tokens) ----
def get_system_prompt():
    """
    ✅ FIX: Dramatically shortened system prompt to prevent repetition
    Focus on personality, tone, and essential facts only
    """
    p = portfolio_data.get("personal_info", {})
    name = p.get("name", "Janagam Bharath")
    role = p.get("role", "AI / LLM Engineer")
    
    # Get top 5 skills
    skills_data = portfolio_data.get("skills", {})
    if isinstance(skills_data, dict):
        skills = skills_data.get("all_skills", [])[:5]
    else:
        skills = skills_data[:5] if isinstance(skills_data, list) else []
    skills_str = ", ".join(skills) if skills else "AI/ML, NLP, Flask, RAG"
    
    # Get top 2 projects
    projects = portfolio_data.get("projects", [])[:2]
    proj_str = ""
    if projects:
        proj_names = [p.get("name", "") for p in projects]
        proj_str = f"Key projects: {', '.join(proj_names)}"
    
    # ✅ CRITICAL: Keep system prompt SHORT and CLEAR
    prompt = f"""You are {name}'s AI assistant. You're friendly, helpful, and enthusiastic!

ABOUT {name}:
- Role: {role} from Hyderabad, India
- Top Skills: {skills_str}
- {proj_str}
- Built 3 live AI apps before turning 18
- Runs 'Bharath AI' YouTube channel teaching AI/LLM concepts
- Email: {p.get("email", "janagambharath1107@gmail.com")}

RESPONSE STYLE:
- Be conversational and natural (2-4 sentences usually)
- Vary your responses - don't repeat the same phrases
- Be specific when asked about projects/skills
- Show enthusiasm about AI and learning
- If asked about something not in your knowledge, suggest checking the portfolio website or contacting directly

IMPORTANT: Give DIFFERENT answers each time, even for similar questions. Be creative and natural!"""
    
    return prompt

# ---- ✅ FIXED: Improved Fallback with Better Context Awareness ----
def get_enhanced_fallback(user_input, conversation_history=None):
    """
    ✅ FIX: Better fallback responses with context awareness
    """
    personal = portfolio_data.get("personal_info", {})
    name = personal.get("name", "Janagam Bharath")
    role = personal.get("role", "AI / LLM Engineer")
    
    text = (user_input or "").lower()
    
    # ✅ Check conversation history to avoid repetition
    if conversation_history:
        recent_responses = [msg.get("content", "") for msg in conversation_history[-4:] if msg.get("role") == "assistant"]
        recent_text = " ".join(recent_responses).lower()
    else:
        recent_text = ""
    
    # Portfolio/About queries - with variations
    if any(k in text for k in ["portfolio", "about", "who are you", "who is", "introduce"]):
        responses = [
            f"Hey! I'm {name}, an {role} based in Hyderabad. I'm passionate about building real AI applications - I've already deployed 3 live AI apps! I specialize in NLP, RAG systems, and Flask development. What would you like to know more about?",
            f"Hi there! I'm {name}. I work on AI/ML projects, focusing on NLP and chatbot development. I've built cool projects like Rythu AI (crop disease detection) and a Memory-to-Lyrics Generator. Ask me about any specific project!",
            f"I'm {name}, a young AI developer from Hyderabad! I love creating practical AI solutions. My background includes working with Hugging Face, Flask, and RAG systems. I also run a YouTube channel teaching AI concepts. What interests you?"
        ]
        # Pick response that hasn't been used recently
        for resp in responses:
            if resp[:50].lower() not in recent_text:
                return resp
        return responses[0]
    
    # Skills queries - with variations
    if any(k in text for k in ["skill", "technology", "tech stack", "what do you know", "what can you"]):
        responses = [
            "My core skills include Python, Flask, Hugging Face, NLP, RAG systems, and Vector Databases. I'm experienced in deploying AI apps on Render and Hugging Face Spaces. What specific technology are you interested in?",
            "I work with a variety of AI/ML tools! Python is my main language, and I use Flask for backend development. I'm skilled in NLP concepts like embeddings, TF-IDF, and RAG architectures. Want to dive deeper into any of these?",
            "I specialize in AI development - from building models with Hugging Face to creating complete Flask applications. My expertise includes NLP, chatbot development, and deploying production-ready AI systems. Which area interests you most?"
        ]
        for resp in responses:
            if resp[:50].lower() not in recent_text:
                return resp
        return responses[0]
    
    # Projects queries - with variations
    if any(k in text for k in ["project", "built", "created", "work", "app"]):
        responses = [
            "I've built several cool AI projects! My favorites are Rythu AI (helps farmers detect crop diseases), Memory to Lyrics Generator (creates songs from memories in multiple languages), and this portfolio chatbot. Which one would you like to know more about?",
            "My main projects include: 1) Rythu AI - a smart crop disease detection system using deep learning, 2) A multilingual lyrics generator powered by NLP, and 3) This AI chatbot you're talking to! They're all live and deployed. Want details on any?",
            "I've deployed 3 live AI applications! There's Rythu AI for farmers, a creative lyrics generator, and this interactive portfolio bot. Each one taught me different aspects of AI development and deployment. Which catches your interest?"
        ]
        for resp in responses:
            if resp[:50].lower() not in recent_text:
                return resp
        return responses[0]
    
    # Contact queries
    if any(k in text for k in ["contact", "email", "reach", "hire", "connect"]):
        email = personal.get("email", "janagambharath1107@gmail.com")
        linkedin = personal.get("linkedin", "")
        return f"I'd love to connect! Reach me at {email} or on LinkedIn: {linkedin}. I'm always open to discussing AI projects, collaborations, or learning opportunities!"
    
    # YouTube queries
    if any(k in text for k in ["youtube", "channel", "videos", "tutorial", "teach"]):
        return "I run 'Bharath AI' on YouTube where I teach AI and LLM concepts through practical projects. My goal is to help people become LLM Engineers in 180 days using simple, hands-on learning. Check it out if you're interested in AI development!"
    
    # Learning/Advice queries
    if any(k in text for k in ["learn", "how to", "advice", "tips", "start", "begin"]):
        return "My learning approach? Build, build, build! Start with the basics, create small projects, then scale up. That's how I learned NLP, RAG, and LLM development. Focus on practical implementation rather than just theory. Want specific learning resources for AI/ML?"
    
    # Goals queries
    if any(k in text for k in ["goal", "future", "plan", "aspiration", "want to"]):
        return "My goal is to become a top AI/LLM Engineer! I want to build production-ready RAG systems, master fine-tuning techniques, and create AI products that solve real problems. I'm also passionate about teaching AI through my YouTube channel. The journey is exciting!"
    
    # Technical queries
    if any(k in text for k in ["rag", "vector", "embedding", "nlp", "llm", "model", "fine-tun"]):
        return "I love working with RAG systems and NLP! I have hands-on experience with vector databases, embeddings, and building retrieval pipelines. I use Hugging Face for model deployment and I'm currently learning fine-tuning techniques for LLMs. What specific technical aspect interests you?"
    
    # Default - encourage specific questions
    return f"I'm {name}'s AI assistant! I can tell you about my AI/ML projects, technical skills, experience with NLP and RAG systems, or my journey as a young developer. I've built 3 live AI applications and love teaching on YouTube. What specific area would you like to explore?"

# ---- OpenRouter API call ----
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def call_openrouter_api(messages, model=None, max_tokens=800, temperature=0.85, timeout=30):
    """
    ✅ FIXED: Increased temperature to 0.85 for more varied responses
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

    # ✅ FIX: Added presence_penalty and frequency_penalty to reduce repetition
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "presence_penalty": 0.6,  # Penalize repeating topics
        "frequency_penalty": 0.7,  # Penalize repeating tokens
        "top_p": 0.9
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
    global chat_sessions
    if len(chat_sessions) > MAX_SESSIONS:
        logger.info("Cleaning up old sessions (current: %d, max: %d)", len(chat_sessions), MAX_SESSIONS)
        sorted_sessions = sorted(
            chat_sessions.items(), 
            key=lambda x: x[1][-1].get('ts', '') if x[1] else '', 
            reverse=True
        )
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
        return f"""
        <!doctype html><html><head><meta charset='utf-8'><title>{name} Chatbot</title></head><body style='font-family:Arial;padding:40px;text-align:center;'>
        <h1>🤖 {name}'s AI Assistant</h1><p>{role}</p><a href='/health'>Health</a></body></html>
        """

@app.route("/health")
def health():
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
    - Better conversation history management
    - Improved system prompt
    - Better fallback with context awareness
    - Added anti-repetition measures
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] New chat request")
    
    try:
        try:
            data = request.get_json(force=True)
            if not data:
                logger.warning(f"[{request_id}] Empty JSON body")
                return jsonify({"error": "invalid_json", "message": "Request body must be valid JSON"}), 400
        except Exception as e:
            logger.error(f"[{request_id}] JSON parse error: {e}")
            return jsonify({"error": "invalid_json", "message": str(e)}), 400
        
        user_input = (data.get("message") or "").strip()
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
        
        # ✅ FIX: Trim session to prevent context overflow (6 turns = 12 messages)
        if len(session) > MAX_HISTORY_TURNS * 2:
            session = session[-(MAX_HISTORY_TURNS * 2):]
            chat_sessions[session_id] = session
            logger.debug(f"[{request_id}] Trimmed session to {len(session)} messages")

        bot_reply = ""
        api_success = False

        if OPENROUTER_API_KEY:
            try:
                # ✅ FIX: Improved system prompt (short and clear)
                system_msg = {"role": "system", "content": get_system_prompt()}
                
                # ✅ FIX: Build clean conversation history
                recent = [
                    {"role": m.get("role"), "content": m.get("content")} 
                    for m in session[-(MAX_HISTORY_TURNS * 2):]
                ]
                
                # ✅ FIX: Add instruction to prevent repetition
                if len(recent) > 2:
                    system_msg["content"] += "\n\nREMINDER: Review the conversation history and give a FRESH, DIFFERENT response. Don't repeat what you've already said!"
                
                messages = [system_msg] + recent
                
                logger.info(f"[{request_id}] Calling OpenRouter with {len(messages)} messages")
                bot_reply = call_openrouter_api(messages)
                api_success = True
                logger.info(f"[{request_id}] OpenRouter replied ({len(bot_reply)} chars)")
                
            except Exception as e:
                logger.exception(f"[{request_id}] OpenRouter API failed: {e}")
                bot_reply = get_enhanced_fallback(user_input, session)
                api_success = False
                logger.info(f"[{request_id}] Using fallback response")
        else:
            logger.warning(f"[{request_id}] No OPENROUTER_API_KEY - using fallback")
            bot_reply = get_enhanced_fallback(user_input, session)
            api_success = False

        # Add assistant response
        session.append({
            "role": "assistant", 
            "content": bot_reply, 
            "ts": datetime.utcnow().isoformat()
        })
        
        # Trim again after adding assistant message
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
    logger.info("Temperature: 0.85 (higher = more varied responses)")
    logger.info("=" * 60)
    
    app.run(
        host="0.0.0.0", 
        port=PORT, 
        debug=os.getenv("FLASK_ENV") == "development"
    )
