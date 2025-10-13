import os
import json
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask import send_from_directory

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

# Google verification route - FIXED filename
@app.route('/googlefa59b4f8aa3dd794.html')
def google_verify():
    return send_from_directory('static', 'googlefa59b4f8aa3dd794.html')

# Load portfolio from JSON file
def load_portfolio_data():
    """Load portfolio from portfolio.json file"""
    try:
        with open("portfolio.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            # Extract name from nested structure
            name = data.get('personal_info', {}).get('name', 'Bharath')
            print(f"✅ Loaded portfolio for: {name}")
            return data
    except FileNotFoundError:
        print("❌ portfolio.json not found - using default data")
        return {
            "personal_info": {
                "name": "Bharath",
                "role": "Aspiring AI Engineer",
                "location": "Hyderabad, India"
            },
            "skills": ["Python", "C", "Flask", "HTML", "CSS", "AI & Chatbots", "DSA"],
            "projects": [
                {"name": "Billing System", "description": "Function-based billing system"},
                {"name": "Portfolio Website", "description": "Personal website with chatbot"}
            ]
        }
    except Exception as e:
        print(f"❌ Error loading portfolio: {e}")
        return {"error": "Could not load portfolio"}

portfolio_data = load_portfolio_data()
chat_sessions = {}

def call_ai_api(messages):
    """Direct API call with increased token limit"""
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
        "max_tokens": 350,
        "temperature": 0.7
    }
    
    print(f"🔄 Calling API with {len(messages)} messages...")
    response = requests.post(url, headers=headers, json=data, timeout=30)
    
    if response.status_code == 200:
        reply = response.json()["choices"][0]["message"]["content"]
        print(f"✅ API Success: {reply[:50]}...")
        return reply
    else:
        print(f"❌ API Error: {response.status_code} - {response.text}")
        raise Exception(f"API Error: {response.status_code}")

def get_system_prompt():
    """Enhanced system prompt with correct data access"""
    # Extract data correctly from nested structure
    personal_info = portfolio_data.get('personal_info', {})
    name = personal_info.get('name', 'Bharath')
    role = personal_info.get('role', 'Aspiring AI Engineer')
    location = personal_info.get('location', 'Hyderabad, India')
    email = personal_info.get('email', '')
    linkedin = personal_info.get('linkedin', '')
    github = personal_info.get('github', '')
    
    skills = portfolio_data.get('skills', [])
    projects = portfolio_data.get('projects', [])
    education = portfolio_data.get('education', [])
    goals = portfolio_data.get('goals', [])
    
    return f"""You are {name}'s AI assistant. Keep responses conversational and informative (3-5 sentences, around 40-60 words).

Portfolio Information:
- Name: {name}
- Role: {role}
- Location: {location}
- Email: {email}
- LinkedIn: {linkedin}
- GitHub: {github}

Skills: {', '.join(skills)}

Projects:
{chr(10).join([f"- {p.get('name', 'Unknown')}: {p.get('description', 'No description')}" for p in projects])}

Education:
{chr(10).join([f"- {e.get('degree', 'Unknown')} at {e.get('institution', 'Unknown')} ({e.get('year', 'Unknown')})" for e in education])}

Goals: {', '.join(goals)}

Guidelines:
- Be friendly, helpful, and engaging
- Provide detailed but not overwhelming answers
- For portfolio questions, give comprehensive but concise info with context
- For general questions, provide useful explanations with examples when helpful
- Add personality and enthusiasm to make conversations more engaging
- Don't use markdown formatting or bullet points
- Keep it natural and conversational, like talking to a friend
- Share relevant details that show expertise without being verbose"""

def get_enhanced_fallback(user_input):
    """Enhanced fallback responses with correct data access"""
    user_lower = user_input.lower()
    
    # Extract data correctly
    personal_info = portfolio_data.get('personal_info', {})
    name = personal_info.get('name', 'Bharath')
    role = personal_info.get('role', 'Aspiring AI Engineer')
    location = personal_info.get('location', 'Hyderabad, India')
    skills = portfolio_data.get('skills', [])
    projects = portfolio_data.get('projects', [])
    
    if any(word in user_lower for word in ['portfolio', 'skills', 'experience', 'projects', 'about', 'who']):
        skills_str = ', '.join(skills[:5])
        return f"I'm {name}, an {role} based in {location}. I'm passionate about technology and have been building my skills in {skills_str}. My notable projects include a functional billing system built in C and this interactive portfolio website with Flask. I'm currently pursuing my B.Tech in CSE and love working on real-world applications. What specific aspect would you like to explore further?"
    
    elif any(word in user_lower for word in ['learn', 'study', 'how', 'advice']):
        return f"That's a great question! My learning journey has been quite hands-on and practical. I started with C programming fundamentals, which gave me a solid foundation in logic and problem-solving. Then I expanded to Python for its versatility and web development with Flask. I believe in learning by building - each project teaches you something new and helps you apply theoretical concepts. Online resources, documentation, and lots of experimentation have been my go-to approach. What technology or skill are you looking to dive into?"
    
    elif any(word in user_lower for word in ['code', 'programming', 'python', 'help', 'development']):
        return f"I'd be excited to help with programming! I work primarily with Python, C, Flask, and web technologies, plus I'm always exploring AI and chatbot development. Programming is like solving puzzles - each challenge teaches you new approaches and techniques. Whether it's debugging, algorithm design, or building user interfaces, I enjoy the problem-solving aspect. What specific coding challenge or concept are you working on? I'm here to share insights and help you work through it!"
    
    elif any(word in user_lower for word in ['project', 'build', 'create']):
        return f"Projects are the best way to learn and showcase your skills! My billing system in C was a great exercise in understanding data structures and user interaction, while this portfolio website taught me web development and API integration. I always try to build something that solves a real problem or demonstrates a concept I'm learning. The key is starting with a clear goal and breaking it down into manageable steps. What kind of project are you thinking about building?"
    
    elif any(word in user_lower for word in ['contact', 'email', 'reach']):
        email = personal_info.get('email', '')
        linkedin = personal_info.get('linkedin', '')
        github = personal_info.get('github', '')
        return f"I'd love to connect! You can reach me at {email}. I'm also active on LinkedIn ({linkedin}) and GitHub ({github}). Feel free to connect with me on any of these platforms. Whether it's for collaboration, questions, or just networking, I'm always happy to chat with fellow tech enthusiasts!"
    
    else:
        return f"Hello there! I'm {name}'s AI assistant, and I'm here to chat about my journey in tech, programming, projects, and anything else you're curious about. I love discussing technology, sharing learning experiences, and helping others navigate their own tech adventures. Whether you want to know about my portfolio, need programming advice, or just want to have an interesting conversation, I'm all ears! What's on your mind today?"

@app.route("/")
def index():
    """Main page"""
    try:
        return render_template("index.html")
    except Exception as e:
        print(f"Template error: {e}")
        personal_info = portfolio_data.get('personal_info', {})
        name = personal_info.get('name', 'Bharath')
        role = personal_info.get('role', 'Aspiring AI Engineer')
        skills = portfolio_data.get('skills', [])
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head><title>{name}'s AI Assistant</title></head>
        <body style="font-family:Arial; padding:40px; text-align:center; background:#f5f5f5;">
            <h1>🤖 {name}'s AI Assistant</h1>
            <p>{role}</p>
            <p>Skills: {', '.join(skills[:5])}</p>
            <a href="/health" style="background:#007bff; color:white; padding:10px 20px; text-decoration:none; border-radius:5px;">Health Check</a>
        </body>
        </html>
        '''

@app.route('/home')
def home():
    return "Hello, world!"

@app.route("/ask", methods=["POST"])
def ask():
    """Handle chat with medium-length responses"""
    try:
        data = request.get_json() or {}
        user_input = data.get("message", "").strip()
        session_id = data.get("session_id", f"session_{int(datetime.now().timestamp())}")
        
        print(f"📨 Received message: {user_input}")
        
        if not user_input:
            return jsonify({"error": "Message required"}), 400
        
        # Initialize session
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
            print(f"🆕 New session created: {session_id}")
        
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
                
                print(f"🤖 Calling AI API...")
                bot_reply = call_ai_api(messages)
                api_success = True
                print(f"✅ AI response received")
                
            except Exception as e:
                print(f"❌ API Error: {e}")
                bot_reply = get_enhanced_fallback(user_input)
                print(f"🔄 Using fallback response")
        else:
            print("⚠️ No API key - using fallback")
            bot_reply = get_enhanced_fallback(user_input)
        
        # Add bot response
        chat_sessions[session_id].append({"role": "assistant", "content": bot_reply})
        
        # Keep sessions manageable
        if len(chat_sessions[session_id]) > 16:
            chat_sessions[session_id] = chat_sessions[session_id][-16:]
        
        return jsonify({
            "reply": bot_reply,
            "session_id": session_id,
            "status": "success" if api_success else "fallback"
        })
        
    except Exception as e:
        print(f"❌ Error in /ask: {e}")
        personal_info = portfolio_data.get('personal_info', {})
        name = personal_info.get('name', 'Bharath')
        
        return jsonify({
            "reply": f"Hi there! I'm {name}'s AI assistant. I'm here to chat about my tech journey, projects, skills, and help with any questions you might have. What would you like to know or discuss today?",
            "status": "error"
        }), 200

@app.route("/health")
def health():
    """Simple health check"""
    personal_info = portfolio_data.get('personal_info', {})
    name = personal_info.get('name', 'Default')
    projects = portfolio_data.get('projects', [])
    skills = portfolio_data.get('skills', [])
    
    return jsonify({
        "status": "healthy",
        "api_configured": bool(API_KEY),
        "portfolio_name": name,
        "projects": len(projects),
        "skills": len(skills)
    })

@app.route("/portfolio")
def portfolio():
    """Portfolio data"""
    return jsonify(portfolio_data)

if __name__ == "__main__":
    personal_info = portfolio_data.get('personal_info', {})
    name = personal_info.get('name', 'Bharath')
    projects = portfolio_data.get('projects', [])
    
    print(f"🚀 Starting {name}'s AI Assistant")
    print(f"📊 {len(projects)} projects loaded")
    print(f"🔑 API Key configured: {bool(API_KEY)}")
    app.run(host="0.0.0.0", port=PORT, debug=True)
