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

# LOAD PORTFOLIO FROM JSON FILE
def load_portfolio_from_file():
    """Load portfolio data from portfolio.json file"""
    
    # Default fallback data
    default_portfolio = {
        "name": "AI Portfolio Assistant",
        "title": "Full Stack Developer & AI Specialist",
        "skills": ["Python", "JavaScript", "React", "Flask", "Node.js", "Machine Learning"],
        "experience": "5+ years of development experience",
        "projects": [
            {
                "name": "AI Chatbot Platform",
                "tech": "Python, OpenAI, Flask, React",
                "description": "Intelligent conversational AI with portfolio integration"
            }
        ],
        "education": "Computer Science & AI",
        "contact": "Available through this chat"
    }
    
    # Try to load from different possible locations
    possible_paths = [
        "portfolio.json",           # Same directory as app.py
        "./portfolio.json",         # Explicit current directory
        "data/portfolio.json",      # In data folder
        "static/portfolio.json",    # In static folder
        os.path.join(os.getcwd(), "portfolio.json")  # Full path
    ]
    
    for path in possible_paths:
        try:
            if os.path.exists(path):
                print(f"✅ Found portfolio.json at: {path}")
                with open(path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    print(f"✅ Loaded portfolio data: {len(data.get('projects', []))} projects")
                    return data
        except Exception as e:
            print(f"❌ Error reading {path}: {e}")
            continue
    
    # List all files in current directory for debugging
    print("📁 Files in current directory:")
    try:
        current_files = os.listdir(".")
        for file in current_files:
            print(f"   - {file}")
    except:
        print("   Could not list files")
    
    print("⚠️ Using default portfolio data")
    return default_portfolio

# Load portfolio data on startup
print("🔍 Loading portfolio data...")
portfolio_data = load_portfolio_from_file()

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
    """System prompt with actual portfolio data"""
    portfolio_text = json.dumps(portfolio_data, indent=2)
    return f"""You are an advanced AI assistant. You can help with ANY topic including:

- Programming and software development
- Data science and machine learning
- Web development and system design
- Creative writing and problem-solving
- General knowledge and current events
- Academic and research questions
- Career and business advice

When relevant, use this portfolio information:
{portfolio_text}

Be helpful, knowledgeable, and conversational. Provide detailed responses with examples when appropriate."""

def get_smart_fallback(user_input):
    """Smart fallback responses using actual portfolio data"""
    user_lower = user_input.lower()
    
    # Portfolio questions
    if any(word in user_lower for word in ['portfolio', 'skills', 'experience', 'projects', 'about', 'background', 'resume', 'cv']):
        
        # Format skills
        skills_text = ', '.join(portfolio_data.get('skills', []))
        
        # Format projects
        projects_list = []
        for project in portfolio_data.get('projects', []):
            projects_list.append(f"• **{project.get('name', 'Project')}**: {project.get('description', 'No description')} (Tech: {project.get('tech', 'Various')})")
        projects_text = '\n'.join(projects_list)
        
        return f"""📋 **MY PORTFOLIO OVERVIEW**

**👨‍💻 Role**: {portfolio_data.get('title', 'Developer')}

**🛠 Technical Skills**: 
{skills_text}

**💼 Experience**: {portfolio_data.get('experience', 'Professional experience in software development')}

**🚀 Featured Projects**:
{projects_text}

**🎓 Education**: {portfolio_data.get('education', 'Computer Science background')}

**📞 Contact**: {portfolio_data.get('contact', 'Available through this interface')}

What specific aspect of my portfolio would you like to discuss in detail?"""
    
    # Programming questions  
    elif any(word in user_lower for word in ['code', 'programming', 'python', 'javascript', 'react', 'flask', 'help', 'debug', 'error']):
        
        # Get programming skills from portfolio
        prog_skills = [skill for skill in portfolio_data.get('skills', []) if any(tech in skill.lower() for tech in ['python', 'javascript', 'react', 'flask', 'node', 'html', 'css'])]
        
        return f"""💻 **PROGRAMMING ASSISTANCE**

Based on my expertise in: {', '.join(prog_skills)}

**🐍 Python Help**:
• Flask/Django web applications
• Data science and automation
• API development and integration
• Debugging and best practices

**⚛️ JavaScript & React**:
• Modern ES6+ JavaScript
• React components and hooks
• State management and events
• Frontend development patterns

**🌐 Web Development**:
• Full-stack architecture
• Database integration
• REST API design
• Responsive design with HTML/CSS

**🔧 From My Project Experience**:
I've built: {', '.join([p.get('name', 'Project') for p in portfolio_data.get('projects', [])])}

**What specific coding challenge can I help you solve?** Share your code or describe the problem!"""
    
    # General response
    else:
        project_count = len(portfolio_data.get('projects', []))
        skills_count = len(portfolio_data.get('skills', []))
        
        return f"""🤖 **AI ASSISTANT READY!**

You asked: *"{user_input}"*

I'm here to help with any topic! My background includes:

**💻 Technical Expertise**: {skills_count} different technologies and frameworks
**🚀 Project Experience**: {project_count} major projects completed
**🎯 Full-Stack Knowledge**: From frontend to backend to deployment

**I can assist with**:
• Programming and code debugging
• Technical architecture and best practices
• Portfolio questions and career advice
• Learning guidance and tutorials
• Creative problem-solving
• General knowledge and research

**What would you like to explore today?** Whether it's technical challenges, portfolio discussion, or any other topic!"""

@app.route("/")
def index():
    """Main page"""
    try:
        return render_template("index.html")
    except:
        # Show portfolio info even without template
        skills_preview = ', '.join(portfolio_data.get('skills', [])[:5])
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI Portfolio Assistant</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; padding: 40px; background: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
                .btn {{ background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 {portfolio_data.get('title', 'AI Assistant')}</h1>
                <p><strong>Skills:</strong> {skills_preview}...</p>
                <p><strong>Experience:</strong> {portfolio_data.get('experience', 'Professional developer')}</p>
                <p><strong>Projects:</strong> {len(portfolio_data.get('projects', []))} completed</p>
                <br>
                <a href="/health" class="btn">System Health</a>
                <a href="/portfolio" class="btn">Full Portfolio</a>
                <a href="/test" class="btn">API Test</a>
            </div>
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
                print("✅ API call successful")
                
            except Exception as e:
                print(f"❌ API Error: {e}")
                bot_reply = get_smart_fallback(user_input)
        else:
            print("🔄 Using fallback (no API key)")
            bot_reply = get_smart_fallback(user_input)
        
        # Add bot response
        chat_sessions[session_id].append({"role": "assistant", "content": bot_reply})
        
        # Keep only recent messages
        if len(chat_sessions[session_id]) > 20:
            chat_sessions[session_id] = chat_sessions[session_id][-20:]
        
        return jsonify({
            "reply": bot_reply,
            "session_id": session_id,
            "status": "success" if api_success else "fallback",
            "portfolio_loaded": bool(portfolio_data),
            "projects_count": len(portfolio_data.get('projects', []))
        })
        
    except Exception as e:
        print(f"❌ Error in ask endpoint: {e}")
        return jsonify({
            "reply": f"I'm here to help! I have {len(portfolio_data.get('projects', []))} projects in my portfolio. Ask me about programming, my experience, or any technical topics!",
            "status": "error"
        }), 200

@app.route("/health")
def health():
    """Health check with portfolio info"""
    return jsonify({
        "status": "healthy",
        "api_key_configured": bool(API_KEY),
        "portfolio_loaded": bool(portfolio_data),
        "portfolio_source": "portfolio.json file" if portfolio_data.get('name') != "AI Portfolio Assistant" else "default data",
        "projects_count": len(portfolio_data.get('projects', [])),
        "skills_count": len(portfolio_data.get('skills', [])),
        "sessions": len(chat_sessions),
        "timestamp": datetime.now().isoformat()
    })

@app.route("/portfolio")
def portfolio():
    """Full portfolio data"""
    return jsonify({
        "portfolio": portfolio_data,
        "source": "Loaded from portfolio.json" if portfolio_data.get('name') != "AI Portfolio Assistant" else "Using default data",
        "timestamp": datetime.now().isoformat()
    })

@app.route("/reload_portfolio")
def reload_portfolio():
    """Reload portfolio.json file"""
    global portfolio_data
    print("🔄 Reloading portfolio data...")
    portfolio_data = load_portfolio_from_file()
    return jsonify({
        "status": "reloaded",
        "projects_count": len(portfolio_data.get('projects', [])),
        "skills_count": len(portfolio_data.get('skills', []))
    })

@app.route("/debug")
def debug():
    """Debug endpoint to see file structure"""
    debug_info = {
        "current_directory": os.getcwd(),
        "files_in_directory": [],
        "portfolio_data_preview": {
            "name": portfolio_data.get('name'),
            "projects_count": len(portfolio_data.get('projects', [])),
            "skills_count": len(portfolio_data.get('skills', []))
        }
    }
    
    try:
        debug_info["files_in_directory"] = os.listdir(".")
    except:
        debug_info["files_in_directory"] = ["Could not list files"]
    
    return jsonify(debug_info)

if __name__ == "__main__":
    print("🚀 Starting AI Portfolio Assistant...")
    print(f"🔑 API Key: {'✅ Configured' if API_KEY else '❌ Missing'}")
    print(f"📊 Portfolio: {len(portfolio_data.get('projects', []))} projects loaded")
    print(f"🌐 Port: {PORT}")
    app.run(host="0.0.0.0", port=PORT)
