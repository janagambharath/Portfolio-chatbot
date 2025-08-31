wfrom flask import Flask, render_template, request, jsonify, Response
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
import time
import re
from datetime import datetime

app = Flask(__name__)

# Load .env file
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

# Load portfolio info
try:
    with open("portfolio.json", "r") as f:
        portfolio_data = json.load(f)
except FileNotFoundError:
    # Fallback portfolio data if file doesn't exist
    portfolio_data = {
        "name": "AI Portfolio Assistant",
        "title": "Full Stack Developer & AI Specialist",
        "skills": ["Python", "JavaScript", "React", "Flask", "Machine Learning", "AI Development"],
        "experience": "5+ years of development experience",
        "projects": [
            {"name": "AI Chatbot Platform", "tech": "Python, OpenAI, Flask", "description": "Intelligent conversational AI system"},
            {"name": "E-commerce Platform", "tech": "React, Node.js, MongoDB", "description": "Full-stack shopping platform"},
            {"name": "Data Analytics Dashboard", "tech": "Python, Pandas, Plotly", "description": "Real-time data visualization"}
        ],
        "education": "Computer Science & AI",
        "contact": "Available via this chat interface"
    }

# OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY
)

# Chat history storage (in production, use a database)
chat_sessions = {}

def get_enhanced_system_prompt():
    """Generate an enhanced system prompt for general AI assistance"""
    return f"""
    You are an advanced AI assistant with expertise in technology, programming, data science, and general knowledge. You have dual capabilities:

    1. GENERAL AI ASSISTANT: You can help with a wide range of topics including:
       - Programming and software development
       - Data science and machine learning
       - Technology explanations and tutorials
       - Problem-solving and debugging
       - Creative writing and content creation
       - Academic and research questions
       - General knowledge and current events
       - Math, science, and engineering
       - Business and career advice
       - Any other topics users might ask about

    2. PORTFOLIO SPECIALIST: When users ask about portfolio-related topics, use this information:
    {json.dumps(portfolio_data, indent=2)}

    INTERACTION GUIDELINES:
    - Be helpful, knowledgeable, and conversational
    - Provide detailed explanations when requested
    - Offer code examples, tutorials, and practical advice
    - Ask clarifying questions when needed
    - Be honest about limitations and uncertainties
    - Maintain a professional yet friendly tone
    - For portfolio questions, reference the provided data
    - For general questions, use your full knowledge base
    - Provide step-by-step guidance for complex topics
    - Suggest best practices and modern approaches

    RESPONSE STYLE:
    - Keep responses informative but not overly long (unless specifically requested)
    - Use examples and analogies when helpful
    - Structure responses clearly with bullet points or sections when appropriate
    - Be encouraging and supportive
    - Provide actionable advice when possible

    Remember: You're not limited to portfolio topics - you're a full-featured AI assistant!
    """

def detect_portfolio_keywords(message):
    """Detect if the message is asking about portfolio-related topics"""
    portfolio_keywords = [
        'portfolio', 'skills', 'experience', 'projects', 'background', 'education',
        'resume', 'cv', 'work', 'job', 'career', 'about you', 'who are you',
        'qualifications', 'expertise', 'programming', 'development', 'tech stack'
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in portfolio_keywords)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    try:
        user_input = request.json.get("message")
        session_id = request.json.get("session_id", "default")
        
        if not user_input or not user_input.strip():
            return jsonify({"error": "Message is required"}), 400
        
        # Initialize session if not exists
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        
        # Add user message to history
        chat_sessions[session_id].append({"role": "user", "content": user_input})
        
        # Check if question is portfolio-related for context enhancement
        is_portfolio_query = detect_portfolio_keywords(user_input)
        
        # Prepare messages for API call
        messages = [
            {"role": "system", "content": get_enhanced_system_prompt()}
        ] + chat_sessions[session_id][-15:]  # Keep more context for better conversations
        
        # Enhanced model parameters for better responses
        response = client.chat.completions.create(
            model="deepseek/deepseek-chat-v3.1:free",  # You can also try other models
            messages=messages,
            max_tokens=800,  # Increased for more detailed responses
            temperature=0.7,  # Balanced creativity
            top_p=0.9,
            frequency_penalty=0.1,  # Reduce repetition
            presence_penalty=0.1,   # Encourage diverse topics
            stream=False
        )
        
        bot_reply = response.choices[0].message.content
        
        # Add bot response to history
        chat_sessions[session_id].append({"role": "assistant", "content": bot_reply})
        
        # Clean up old sessions (keep last 30 messages per session)
        if len(chat_sessions[session_id]) > 30:
            chat_sessions[session_id] = chat_sessions[session_id][-30:]
        
        return jsonify({
            "reply": bot_reply,
            "session_id": session_id,
            "status": "success",
            "is_portfolio_related": is_portfolio_query,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error in /ask endpoint: {str(e)}")
        return jsonify({
            "error": "I'm having trouble processing your request. Please try again.",
            "status": "error"
        }), 500

@app.route("/ask_stream", methods=["POST"])
def ask_stream():
    """Streaming endpoint for real-time word-by-word responses"""
    try:
        user_input = request.json.get("message")
        session_id = request.json.get("session_id", "default")
        
        def generate_stream():
            try:
                # Initialize session if not exists
                if session_id not in chat_sessions:
                    chat_sessions[session_id] = []
                
                # Add user message to history
                chat_sessions[session_id].append({"role": "user", "content": user_input})
                
                # Prepare messages for API call
                messages = [
                    {"role": "system", "content": get_enhanced_system_prompt()}
                ] + chat_sessions[session_id][-15:]
                
                # Call OpenRouter API with streaming
                response = client.chat.completions.create(
                    model="deepseek/deepseek-chat-v3.1:free",
                    messages=messages,
                    max_tokens=800,
                    temperature=0.7,
                    top_p=0.9,
                    frequency_penalty=0.1,
                    presence_penalty=0.1,
                    stream=True
                )
                
                full_response = ""
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                
                # Add complete response to history
                chat_sessions[session_id].append({"role": "assistant", "content": full_response})
                
                # Send completion signal
                yield f"data: {json.dumps({'content': '', 'done': True, 'full_response': full_response})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
        
        return Response(generate_stream(), mimetype='text/event-stream')
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/chat_modes", methods=["GET"])
def get_chat_modes():
    """Get available chat modes"""
    return jsonify({
        "modes": [
            {
                "id": "general",
                "name": "General AI Assistant",
                "description": "Ask me anything - programming, science, creative writing, problem-solving, and more!"
            },
            {
                "id": "portfolio",
                "name": "Portfolio Focus",
                "description": "Learn about my skills, projects, and professional experience"
            },
            {
                "id": "technical",
                "name": "Technical Expert",
                "description": "Deep dive into programming, algorithms, and technical concepts"
            }
        ]
    })

@app.route("/clear_chat", methods=["POST"])
def clear_chat():
    """Clear chat history for a session"""
    session_id = request.json.get("session_id", "default")
    if session_id in chat_sessions:
        chat_sessions[session_id] = []
    return jsonify({"status": "Chat cleared successfully"})

@app.route("/chat_history", methods=["GET"])
def get_chat_history():
    """Get chat history for a session"""
    session_id = request.args.get("session_id", "default")
    history = chat_sessions.get(session_id, [])
    return jsonify({
        "history": history,
        "session_id": session_id,
        "message_count": len(history)
    })

@app.route("/health")
def health_check():
    """Enhanced health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "portfolio_loaded": bool(portfolio_data),
        "api_configured": bool(API_KEY),
        "active_sessions": len(chat_sessions),
        "features": {
            "general_ai": True,
            "portfolio_info": True,
            "streaming": True,
            "session_management": True
        }
    })

@app.route("/portfolio")
def get_portfolio():
    """Endpoint to get portfolio data directly"""
    return jsonify({
        "portfolio": portfolio_data,
        "last_updated": datetime.now().isoformat()
    })

@app.route("/models", methods=["GET"])
def get_available_models():
    """Get list of available AI models"""
    available_models = [
        "deepseek/deepseek-chat-v3.1:free",
        "meta-llama/llama-3.1-8b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "google/gemma-2-9b-it:free"
    ]
    return jsonify({"models": available_models})

@app.route("/switch_model", methods=["POST"])
def switch_model():
    """Switch AI model (for future enhancement)"""
    model = request.json.get("model")
    # This is a placeholder for model switching functionality
    return jsonify({"status": f"Model switched to {model}"})

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": ["/", "/ask", "/ask_stream", "/health", "/portfolio"]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error",
        "message": "Please try again or contact support"
    }), 500

@app.errorhandler(429)
def rate_limit_error(error):
    return jsonify({
        "error": "Rate limit exceeded",
        "message": "Please wait a moment before sending another message"
    }), 429

# Middleware for request logging
@app.before_request
def log_request():
    if request.endpoint and request.endpoint != 'static':
        print(f"[{datetime.now()}] {request.method} {request.path}")

if __name__ == "__main__":
    # Ensure required directories exist
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static/css", exist_ok=True)
    
    print("Starting Enhanced AI Portfolio Assistant...")
    print(f"Portfolio data loaded: {bool(portfolio_data)}")
    print(f" OpenRouter API configured: {bool(API_KEY)}")
    print(f"Features: General AI + Portfolio + Streaming")
    print(f" Server starting on http://localhost:5000")
    
    app.run(host="0.0.0.0", port=5000, debug=True)
