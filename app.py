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

# Portfolio data
portfolio_data = {
    "name": "AI Portfolio Assistant",
    "title": "Full Stack Developer & AI Specialist",
    "skills": ["Python", "JavaScript", "React", "Flask", "Node.js", "Machine Learning", "AI Development", "MongoDB", "PostgreSQL", "Docker", "AWS"],
    "experience": "5+ years of development experience",
    "projects": [
        {
            "name": "AI Chatbot Platform",
            "tech": "Python, OpenAI, Flask, React",
            "description": "Intelligent conversational AI with portfolio integration"
        },
        {
            "name": "E-commerce Platform", 
            "tech": "React, Node.js, MongoDB, Stripe",
            "description": "Full-stack shopping platform with payment processing"
        },
        {
            "name": "Data Analytics Dashboard",
            "tech": "Python, Pandas, Plotly, D3.js",
            "description": "Real-time data visualization and reporting tool"
        }
    ],
    "education": "Computer Science & AI",
    "contact": "Available through this chat"
}

# Chat sessions
chat_sessions = {}

def call_ai_api(messages):
    """Direct API call to OpenRouter"""
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
        "max_tokens": 600,
        "temperature": 0.7
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=30)
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"API Error: {response.status_code}")

def get_system_prompt():
    """System prompt for AI"""
    portfolio_text = json.dumps(portfolio_data, indent=2)
    return f"You are an AI assistant. Help with any topic. When relevant, use portfolio info: {portfolio_text}"

def get_fallback_response(user_input):
    """Fallback when API unavailable"""
    user_lower = user_input.lower()
    
    if any(word in user_lower for word in ['portfolio', 'skills', 'experience', 'projects']):
        skills_text = ', '.join(portfolio_data['skills'])
        projects_text = '\n'.join([f"• {p['name']}: {p['description']}" for p in portfolio_data['projects']])
        
        return f"PORTFOLIO OVERVIEW\n\nSkills: {skills_text}\n\nExperience: {portfolio_data['experience']}\n\nProjects:\n{projects_text}\n\nEducation: {portfolio_data['education']}\n\nWhat would you like to know more about?"
    
    elif any(word in user_lower for word in ['code', 'programming', 'python', 'javascript', 'help']):
        return "PROGRAMMING HELP\n\nI can assist with:\n• Python (Flask, Django, data science)\n• JavaScript (React, Node.js, modern ES6+)\n• Web development (HTML, CSS, APIs)\n• Debugging and best practices\n• Project architecture and planning\n\nWhat specific programming challenge can I help you with?"
    
    else:
        return f"Hello! I'm an AI assistant that can help with:\n\n• Programming and web development\n• Portfolio and career questions\n• Technical problem-solving\n• Learning guidance and tutorials\n\nYou asked: '{user_input}'\n\nWhat specific topic can I help you with today?"

@app.route("/")
def index():
    """Main page"""
    try:
        return render_template("index.html")
    except:
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>AI Assistant</title></head>
        <body style="font-family:Arial; padding:40px; text-align:center; background:#f5f5f5;">
            <h1>🤖 AI Portfolio Assistant</h1>
            <p>Backend is running successfully!</p>
            <a href="/health" style="background:#007bff; color:white; padding:10px 20px; text-decoration:none; border-radius:5px;">Health Check</a>
        </body>
        </html>
        '''

@app.route("/ask", methods=["POST"])
def ask():
    """Handle chat messages"""
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
                ] + chat_sessions[session_id][-8:]
                
                bot_reply = call_ai_api(messages)
                api_success = True
                print("API call successful")
                
            except Exception as e:
                print(f"API Error: {e}")
                bot_reply = get_fallback_response(user_input)
        else:
            bot_reply = get_fallback_response(user_input)
        
        # Add bot response
        chat_sessions[session_id].append({"role": "assistant", "content": bot_reply})
        
        # Keep only recent messages
        if len(chat_sessions[session_id]) > 20:
            chat_sessions[session_id] = chat_sessions[session_id][-20:]
        
        return jsonify({
            "reply": bot_reply,
            "session_id": session_id,
            "status": "success" if api_success else "fallback"
        })
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            "reply": "I'm here to help! Ask me about programming, my portfolio, or any technical topics.",
            "status": "error"
        }), 200

@app.route("/health")
def health():
    """Health check"""
    api_status = "available" if API_KEY else "missing"
    
    return jsonify({
        "status": "healthy",
        "api_key": api_status,
        "portfolio_loaded": True,
        "sessions": len(chat_sessions),
        "timestamp": datetime.now().isoformat()
    })

@app.route("/portfolio")
def portfolio():
    """Portfolio data"""
    return jsonify(portfolio_data)

@app.route("/test")
def test_api():
    """Test API connection"""
    if not API_KEY:
        return jsonify({"status": "no_api_key", "message": "Set OPENROUTER_API_KEY in environment"})
    
    try:
        test_messages = [
            {"role": "user", "content": "Say hello"}
        ]
        result = call_ai_api(test_messages)
        return jsonify({"status": "success", "response": result})
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)})

if __name__ == "__main__":
    print("Starting AI Assistant...")
    print(f"API Key: {'Configured' if API_KEY else 'Missing'}")
    print(f"Port: {PORT}")
    app.run(host="0.0.0.0", port=PORT)
