from flask import Flask, render_template, request, jsonify
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

# Default portfolio data
DEFAULT_PORTFOLIO = {
    "name": "AI Assistant",
    "title": "Full Stack Developer & AI Specialist",
    "skills": [
        "Python", "JavaScript", "React", "Flask", 
        "Machine Learning", "AI Development", "Node.js", 
        "MongoDB", "PostgreSQL", "Docker"
    ],
    "experience": "5+ years of development experience",
    "projects": [
        {
            "name": "AI Chatbot Platform",
            "tech": "Python, OpenAI, Flask",
            "description": "Intelligent conversational AI system with portfolio integration"
        },
        {
            "name": "E-commerce Platform",
            "tech": "React, Node.js, MongoDB",
            "description": "Full-stack shopping platform with payment integration"
        },
        {
            "name": "Data Analytics Dashboard",
            "tech": "Python, Pandas, Plotly",
            "description": "Real-time data visualization and analytics tool"
        }
    ],
    "education": "Computer Science & AI",
    "contact": "Available through this chat interface"
}

# Load portfolio data
def load_portfolio():
    try:
        if os.path.exists("portfolio.json"):
            with open("portfolio.json", "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            return DEFAULT_PORTFOLIO
    except Exception as e:
        print(f"Error loading portfolio: {e}")
        return DEFAULT_PORTFOLIO

portfolio_data = load_portfolio()

# Initialize OpenAI client
def get_openai_client():
    if not API_KEY:
        print("Warning: OPENROUTER_API_KEY not found in environment variables")
        return None
    
    try:
        return OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=API_KEY
        )
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        return None

client = get_openai_client()

# Chat sessions storage
chat_sessions = {}

def create_system_prompt():
    """Create enhanced system prompt for AI assistant"""
    return f"""You are an advanced AI assistant with dual capabilities:

1. GENERAL AI ASSISTANT: Help with any topic including:
   - Programming and software development
   - Data science and machine learning  
   - Technology explanations and tutorials
   - Problem-solving and debugging
   - Creative writing and content
   - Academic and research questions
   - General knowledge and current events
   - Math, science, and engineering
   - Business and career advice
   - Any other questions users might have

2. PORTFOLIO INFORMATION: When asked about portfolio, skills, or experience, use:
{json.dumps(portfolio_data, indent=2)}

GUIDELINES:
- Be helpful, knowledgeable, and conversational
- Provide detailed explanations when requested
- Offer practical examples and code when relevant
- Ask clarifying questions when needed
- Be honest about limitations
- Maintain a professional yet friendly tone
- You can discuss any topic - you're not limited to portfolio only

Remember: You're a full-featured AI assistant that can help with anything!"""

@app.route("/")
def index():
    """Serve the main chat interface"""
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    """Handle chat messages"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        user_input = data.get("message", "").strip()
        session_id = data.get("session_id", "default")
        
        if not user_input:
            return jsonify({"error": "Message cannot be empty"}), 400
        
        if not client:
            return jsonify({
                "error": "AI service not available. Please check API configuration.",
                "reply": "I apologize, but I'm currently unable to process your request. Please check that your OpenRouter API key is properly configured."
            }), 503
        
        # Initialize session
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        
        # Add user message to history
        chat_sessions[session_id].append({
            "role": "user", 
            "content": user_input
        })
        
        # Prepare messages for API
        messages = [
            {"role": "system", "content": create_system_prompt()}
        ]
        
        # Add recent conversation history (last 10 messages)
        recent_messages = chat_sessions[session_id][-10:]
        messages.extend(recent_messages)
        
        # Call OpenAI API
        try:
            response = client.chat.completions.create(
                model="deepseek/deepseek-chat-v3.1:free",
                messages=messages,
                max_tokens=800,
                temperature=0.7,
                top_p=0.9,
                frequency_penalty=0.1,
                presence_penalty=0.1
            )
            
            bot_reply = response.choices[0].message.content.strip()
            
        except Exception as api_error:
            print(f"OpenAI API Error: {api_error}")
            bot_reply = f"I apologize, but I encountered an issue processing your request. Please try again. If the problem persists, check your API configuration."
        
        # Add bot response to history
        chat_sessions[session_id].append({
            "role": "assistant", 
            "content": bot_reply
        })
        
        # Limit session history to prevent memory issues
        if len(chat_sessions[session_id]) > 50:
            chat_sessions[session_id] = chat_sessions[session_id][-50:]
        
        return jsonify({
            "reply": bot_reply,
            "session_id": session_id,
            "status": "success",
            "timestamp": datetime.now().isoformat()
        })
        
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format"}), 400
    except Exception as e:
        print(f"Error in /ask endpoint: {e}")
        return jsonify({
            "error": "An unexpected error occurred. Please try again.",
            "reply": "I apologize for the inconvenience. There was a technical issue processing your request."
        }), 500

@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "portfolio_loaded": bool(portfolio_data),
        "api_configured": bool(API_KEY and client),
        "active_sessions": len(chat_sessions)
    })

@app.route("/portfolio")
def portfolio():
    """Get portfolio data"""
    return jsonify({
        "portfolio": portfolio_data,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/clear", methods=["POST"])
def clear_session():
    """Clear chat session"""
    try:
        data = request.get_json() or {}
        session_id = data.get("session_id", "default")
        
        if session_id in chat_sessions:
            chat_sessions[session_id] = []
            
        return jsonify({
            "status": "success",
            "message": "Chat history cleared"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Page not found",
        "available_routes": ["/", "/ask", "/health", "/portfolio"]
    }), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({
        "error": "Internal server error",
        "message": "Please try again later"
    }), 500

if __name__ == "__main__":
    # Create required directories
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    os.makedirs("static/css", exist_ok=True)
    
    # Print startup info
    print("=" * 50)
    print("🤖 AI Assistant & Portfolio Chatbot")
    print("=" * 50)
    print(f"📊 Portfolio loaded: {'✅' if portfolio_data else '❌'}")
    print(f"🔑 API configured: {'✅' if API_KEY else '❌'}")
    print(f"🌐 Starting server on http://localhost:5000")
    print(f"📁 Make sure templates/index.html exists")
    print("=" * 50)
    
    # Run the app
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=True
        )
