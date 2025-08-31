import os
import logging
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("✅ Environment variables loaded")
except ImportError:
    logger.info("ℹ️ Using system environment variables")

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key')
app.config['DEBUG'] = False  # Force production mode

# Get environment variables
API_KEY = os.getenv("OPENROUTER_API_KEY")
PORT = int(os.getenv("PORT", 10000))

# Initialize OpenAI client with fixed initialization
client = None
try:
    if API_KEY and API_KEY.strip():
        from openai import OpenAI
        
        # Fixed initialization - no extra parameters
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=API_KEY.strip()
        )
        logger.info("✅ OpenRouter client initialized")
    else:
        logger.warning("⚠️ No API key - running in fallback mode")
except Exception as e:
    logger.error(f"❌ OpenAI client error: {str(e)}")
    client = None

# Portfolio data
portfolio_data = {
    "name": "AI Portfolio Assistant",
    "title": "Full Stack Developer & AI Specialist",
    "skills": [
        "Python", "JavaScript", "React", "Flask", "Node.js",
        "Machine Learning", "AI Development", "MongoDB", 
        "PostgreSQL", "Docker", "AWS", "Git", "REST APIs"
    ],
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
    "education": "Computer Science & AI/ML",
    "contact": "Available through this chat"
}

# Chat sessions
chat_sessions = {}

def create_ai_prompt():
    return f"""You are an advanced AI assistant. You can help with ANY topic including:

🤖 GENERAL ASSISTANCE:
- Programming (Python, JavaScript, React, Flask, etc.)
- Data science and machine learning
- Web development and system design
- Problem-solving and debugging
- Creative writing and content
- Academic research and analysis  
- Business and career advice
- General knowledge and current events

💼 PORTFOLIO INFO (when relevant):
{json.dumps(portfolio_data, indent=2)}

Be helpful, knowledgeable, and conversational. Provide detailed explanations with examples when needed. You're a full-featured AI assistant!"""

def get_smart_response(user_input):
    """Smart fallback responses"""
    user_lower = user_input.lower()
    
    # Portfolio questions
    if any(word in user_lower for word in ['portfolio', 'skills', 'experience', 'projects', 'about', 'resume']):
        return f"""📋 **My Portfolio Overview**

**🛠 Skills**: {', '.join(portfolio_data['skills'])}

**💼 Experience**: {portfolio_data['experience']}

**🚀 Key Projects**:
{chr(10).join([f"• **{p['name']}**: {p['description']} ({p['tech']})" for p in portfolio_data['projects']])}

**🎓 Education**: {portfolio_data['education']}

What specific aspect would you like to know more about?"""

    # Programming questions
    if any(word in user_lower for word in ['code', 'programming', 'python', 'javascript', 'react', 'help', 'debug']):
        return """💻 **Programming Help**

I can assist with:

**🐍 Python**: Web development (Flask/Django), data science, automation, APIs
**⚛️ React**: Frontend development, components, state management, hooks
**🌐 JavaScript**: Modern ES6+, async programming, DOM manipulation
**🔧 Flask**: Web applications, RESTful APIs, database integration

**Common Solutions**:
• **Debugging**: Check console errors, verify syntax, test step-by-step
• **APIs**: Use proper HTTP methods, handle errors, validate data
• **React**: Use hooks correctly, manage state, handle events properly
• **Python**: Follow PEP 8, use virtual environments, handle exceptions

Share your specific coding challenge and I'll provide detailed guidance!"""

    # General response
    return f"""👋 **Hello!** 

I'm an AI assistant that can help with:

**💻 Technical Topics**: Programming, web development, data science, debugging
**📚 Learning**: Tutorials, explanations, best practices, career advice  
**💼 Portfolio**: My skills, projects, and professional experience
**🎯 Problem Solving**: Code reviews, architecture advice, troubleshooting

**Your Question**: "{user_input}"

I'm ready to dive deep into any topic! What specific area can I help you with today?"""

@app.route("/")
def index():
    try:
        return render_template("index.html")
    except:
        return """
        <html>
        <head><title>AI Assistant</title></head>
        <body style="font-family:Arial;padding:40px;text-align:center;background:#f0f0f0;">
            <h1>🤖 AI Portfolio Assistant</h1>
            <p>Backend is running successfully!</p>
            <div style="margin:20px;">
                <a href="/health" style="background:#007bff;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">Health Check</a>
                <a href="/portfolio" style="background:#28a745;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;margin-left:10px;">Portfolio Data</a>
            </div>
        </body>
        </html>
        """

@app.route("/ask", methods=["POST"])
def ask():
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
        chat_sessions[session_id].append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        # Try API call
        bot_reply = ""
        api_success = False
        
        if client:
            try:
                messages = [
                    {"role": "system", "content": create_ai_prompt()}
                ] + chat_sessions[session_id][-10:]
                
                response = client.chat.completions.create(
                    model="deepseek/deepseek-chat-v3.1:free",
                    messages=messages,
                    max_tokens=600,
                    temperature=0.7
                )
                
                bot_reply = response.choices[0].message.content.strip()
                api_success = True
                logger.info("✅ API call successful")
                
            except Exception as e:
                logger.error(f"API Error: {e}")
                bot_reply = get_smart_response(user_input)
        else:
            bot_reply = get_smart_response(user_input)
        
        # Add bot response
        chat_sessions[session_id].append({
            "role": "assistant",
            "content": bot_reply,
            "timestamp": datetime.now().isoformat()
        })
        
        return jsonify({
            "reply": bot_reply,
            "session_id": session_id,
            "status": "success" if api_success else "fallback",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Ask endpoint error: {e}")
        return jsonify({
            "reply": "I'm here to help! Ask me about programming, my portfolio, or any topic you're curious about.",
            "status": "error_handled"
        }), 200

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "api_configured": bool(API_KEY),
        "api_working": bool(client),
        "portfolio_loaded": bool(portfolio_data),
        "active_sessions": len(chat_sessions),
        "environment": "production",
        "port": PORT
    })

@app.route("/portfolio") 
def portfolio():
    return jsonify(portfolio_data)

if __name__ == "__main__":
    logger.info(f"🚀 Starting on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
else:
    logger.info("🌐 Deployed on Render")
