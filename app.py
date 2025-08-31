from flask import Flask, render_template, request, jsonify, Response
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
import time
import re

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
        "name": "Bharath",
        "title": "Aspiring LLM engineer",
        "skills": ["Python", "C", "React", "Flask", "Machine Learning"],
        "experience": "5+ years of development experience",
        "projects": [
            {"name": "AI Chatbot", "tech": "Python, OpenAI"},
            {"name": "Clock", "tech": "C, Html"},
            {"name": "Portfolio Website ", "tech": "Python, Flask, HTML"}
        ]
    }

# OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY
)

# Chat history storage (in production, use a database)
chat_sessions = {}

def get_system_prompt():
    """Generate a comprehensive system prompt with portfolio context"""
    return f"""
    You are a professional AI assistant representing a portfolio. Your role is to help visitors learn about the portfolio owner's skills, experience, and projects.
    
    Portfolio Information:
    {json.dumps(portfolio_data, indent=2)}
    
    Guidelines:
    - Be professional, friendly, and informative
    - Answer questions about skills, experience, projects, and background
    - If asked about something not in the portfolio, politely redirect to available information
    - Keep responses concise but informative (2-4 sentences typically)
    - Use a conversational tone while maintaining professionalism
    - Highlight key achievements and technical expertise when relevant
    - If asked about contact information, suggest they use the contact form on the website
    """

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
        
        # Prepare messages for API call
        messages = [
            {"role": "system", "content": get_system_prompt()}
        ] + chat_sessions[session_id][-10:]  # Keep last 10 messages for context
        
        # Call OpenRouter API
        response = client.chat.completions.create(
            model="deepseek/deepseek-chat-v3.1:free",
            messages=messages,
            max_tokens=500,  # Limit response length
            temperature=0.7,
            stream=False
        )
        
        bot_reply = response.choices[0].message.content
        
        # Add bot response to history
        chat_sessions[session_id].append({"role": "assistant", "content": bot_reply})
        
        # Clean up old sessions (keep last 50 messages per session)
        if len(chat_sessions[session_id]) > 50:
            chat_sessions[session_id] = chat_sessions[session_id][-50:]
        
        return jsonify({
            "reply": bot_reply,
            "session_id": session_id,
            "status": "success"
        })
        
    except Exception as e:
        print(f"Error in /ask endpoint: {str(e)}")
        return jsonify({
            "error": "I'm having trouble processing your request. Please try again.",
            "status": "error"
        }), 500

@app.route("/stream", methods=["POST"])
def stream_response():
    """Alternative streaming endpoint for real-time responses"""
    try:
        user_input = request.json.get("message")
        session_id = request.json.get("session_id", "default")
        
        def generate():
            try:
                # Initialize session if not exists
                if session_id not in chat_sessions:
                    chat_sessions[session_id] = []
                
                # Add user message to history
                chat_sessions[session_id].append({"role": "user", "content": user_input})
                
                # Prepare messages for API call
                messages = [
                    {"role": "system", "content": get_system_prompt()}
                ] + chat_sessions[session_id][-10:]
                
                # Call OpenRouter API with streaming
                response = client.chat.completions.create(
                    model="deepseek/deepseek-chat-v3.1:free",
                    messages=messages,
                    max_tokens=500,
                    temperature=0.7,
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
                yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
        
        return Response(generate(), mimetype='text/plain')
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health")
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "portfolio_loaded": bool(portfolio_data),
        "api_configured": bool(API_KEY)
    })

@app.route("/portfolio")
def get_portfolio():
    """Endpoint to get portfolio data directly"""
    return jsonify(portfolio_data)

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    # Ensure templates directory exists
    if not os.path.exists("templates"):
        os.makedirs("templates")
    
    print("Starting AI Portfolio Assistant...")
    print(f"Portfolio data loaded: {bool(portfolio_data)}")
    print(f"OpenRouter API configured: {bool(API_KEY)}")
    
    app.run(host="0.0.0.0", port=5000, debug=True)
