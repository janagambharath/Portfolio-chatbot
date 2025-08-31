import os
import json
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')

# Configuration
API_KEY = os.getenv("OPENROUTER_API_KEY")
PORT = int(os.getenv("PORT", 10000))

# Load portfolio from JSON file
def load_portfolio_data():
    """Load portfolio from portfolio.json file"""
    try:
        with open("portfolio.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"✅ Loaded portfolio for: {data.get('name', 'Unknown')}")
            return data
    except FileNotFoundError:
        print("❌ portfolio.json not found - using default data")
        return {
            "name": "Bharath",
            "title": "Aspiring AI Engineer",
            "skills": ["Python", "C", "Flask", "HTML", "CSS", "AI & Chatbots", "DSA"],
            "projects": [
                {"name": "Billing System", "tech": "C", "description": "Function-based billing system"},
                {"name": "Portfolio Website", "tech": "Flask, HTML, CSS", "description": "Personal website with chatbot"}
            ],
            "education": "Diploma in ECE, B.Tech CSE (planned)",
            "location": "Hyderabad, India"
        }
    except Exception as e:
        print(f"❌ Error loading portfolio: {e}")
        return {"error": "Could not load portfolio"}

portfolio_data = load_portfolio_data()
chat_sessions = {}

def call_ai_api(messages):
    """Direct API call"""
    if not API_KEY:
        raise Exception("No API key")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek/deepseek-chat-v3.1:free",
        "messages": messages,
        "max_tokens": 200,  # SHORTER RESPONSES
        "temperature": 0.7
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=30)
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"API Error: {response.status_code}")

def get_system_prompt():
    """CONCISE system prompt"""
    return f"""You are Bharath's AI assistant. Keep responses SHORT and conversational (2-3 sentences max).

Portfolio data: {json.dumps(portfolio_data)}

Guidelines:
- Be friendly and concise
- Answer directly without long explanations
- For portfolio questions, give brief, relevant info
- For general questions, provide helpful but short answers
- Don't use markdown formatting or bullet points
- Keep it conversational and natural"""

def get_short_fallback(user_input):
    """Short fallback responses"""
    user_lower = user_input.lower()
    
    if any(word in user_lower for word in ['portfolio', 'skills', 'experience', 'projects', 'about', 'who']):
        skills = ', '.join(portfolio_data.get('skills', [])[:5])
        return f"I'm {portfolio_data.get('name', 'Bharath')}, an {portfolio_data.get('title', 'aspiring AI engineer')} from {portfolio_data.get('location', 'Hyderabad')}. My main skills are {skills}. I've built projects like a billing system in C and this portfolio website. What would you like to know more about?"
    
    elif any(word in user_lower for word in ['learn', 'study', 'how']):
        return f"Great question! I learned through online tutorials, hands-on projects, and lots of practice. Started with C programming, then moved to Python and web development. Building real projects like my billing system really helped solidify the concepts. What are you interested in learning?"
    
    elif any(word in user_lower for word in ['code', 'programming', 'python', 'help']):
        return f"I'd be happy to help with programming! I work with Python, C, Flask, and web development. What specific coding challenge are you working on?"
    
    else:
        return f"Hi! I'm Bharath's AI assistant. I can help with questions about my portfolio, programming, or general topics. What would you like to know?"

@app.route("/")
def index():
    """Main page"""
    try:
        return render_template("index.html")
    except:
        return f'''
        <!DOCTYPE html>
        <html>
        <head><title>{portfolio_data.get('name', 'Bharath')}'s AI Assistant</title></head>
        <body style="font-family:Arial; padding:40px; text-align:center; background:#f5f5f5;">
            <h1>🤖 {portfolio_data.get('name', 'Bharath')}'s AI Assistant</h1>
            <p>{portfolio_data.get('title', 'Aspiring AI Engineer')}</p>
            <p>Skills: {', '.join(portfolio_data.get('skills', [])[:5])}</p>
            <a href="/health" style="background:#007bff; color:white; padding:10px 20px; text-decoration:none; border-radius:5px;">Health Check</a>
        </body>
        </html>
        '''

@app.route("/ask", methods=["POST"])
def ask():
    """Handle chat with SHORT responses"""
    try:
        data = request.get_json() or {}
        user_input = data.get("message", "").strip()
        session_id = data.get("session_id", f"session_{int(datetime.now().timestamp())}")
        
        if not user_input:
            return jsonify({"error": "Message required"}), 400
        
        # Initialize session
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        
        # Add user message
        chat_sessions[session_id].append({"role": "user", "content": user_input})
        
        # Try API call
        bot_reply = ""
        api_success = False
        
        if API_KEY:
            try:
                messages = [
                    {"role": "system", "content": get_system_prompt()}
                ] + chat_sessions[session_id][-6:]  # LESS CONTEXT = SHORTER RESPONSES
                
                bot_reply = call_ai_api(messages)
                api_success = True
                
            except Exception as e:
                print(f"API Error: {e}")
                bot_reply = get_short_fallback(user_input)
        else:
            bot_reply = get_short_fallback(user_input)
        
        # Add bot response
        chat_sessions[session_id].append({"role": "assistant", "content": bot_reply})
        
        # Keep sessions small
        if len(chat_sessions[session_id]) > 12:
            chat_sessions[session_id] = chat_sessions[session_id][-12:]
        
        return jsonify({
            "reply": bot_reply,
            "session_id": session_id,
            "status": "success" if api_success else "fallback"
        })
        
    except Exception as e:
        return jsonify({
            "reply": f"Hi! I'm {portfolio_data.get('name', 'Bharath')}'s AI assistant. What would you like to know?",
            "status": "error"
        }), 200

@app.route("/health")
def health():
    """Simple health check"""
    return jsonify({
        "status": "healthy",
        "api_configured": bool(API_KEY),
        "portfolio_name": portfolio_data.get('name', 'Default'),
        "projects": len(portfolio_data.get('projects', [])),
        "skills": len(portfolio_data.get('skills', []))
    })

@app.route("/portfolio")
def portfolio():
    """Portfolio data"""
    return jsonify(portfolio_data)

if __name__ == "__main__":
    print(f"🚀 Starting {portfolio_data.get('name', 'Bharath')}'s AI Assistant")
    print(f"📊 {len(portfolio_data.get('projects', []))} projects loaded")
    app.run(host="0.0.0.0", port=PORT)
