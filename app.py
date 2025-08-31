import os
import logging
from flask import Flask, render_template, request, jsonify
import json
from datetime import datetime

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.info("python-dotenv not available, using system environment variables")

# Initialize Flask app
app = Flask(__name__)

# Production configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-fallback-secret-key-2024')
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
app.config['ENV'] = os.getenv('FLASK_ENV', 'production')

# Get environment variables
API_KEY = os.getenv("OPENROUTER_API_KEY")
PORT = int(os.getenv("PORT", 10000))
HOST = os.getenv("HOST", "0.0.0.0")

# Initialize OpenAI client with proper error handling
client = None
try:
    if API_KEY:
        from openai import OpenAI
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=API_KEY
        )
        logger.info("✅ OpenRouter client initialized successfully")
    else:
        logger.warning("⚠️ No API key found - running in fallback mode")
except ImportError as e:
    logger.error(f"❌ OpenAI library not available: {e}")
    client = None
except Exception as e:
    logger.error(f"❌ Error initializing OpenAI client: {e}")
    client = None

# Default portfolio data
DEFAULT_PORTFOLIO = {
    "name": "AI Portfolio Assistant",
    "title": "Full Stack Developer & AI Specialist",
    "skills": [
        "Python", "JavaScript", "React", "Flask", "FastAPI",
        "Machine Learning", "AI Development", "Node.js", 
        "MongoDB", "PostgreSQL", "Docker", "AWS", "Git",
        "HTML/CSS", "REST APIs", "Microservices"
    ],
    "experience": "5+ years of development experience",
    "projects": [
        {
            "name": "AI Chatbot Platform",
            "tech": "Python, OpenAI, Flask, React",
            "description": "Intelligent conversational AI system with portfolio integration and real-time chat capabilities"
        },
        {
            "name": "E-commerce Platform",
            "tech": "React, Node.js, MongoDB, Stripe",
            "description": "Full-stack shopping platform with payment integration, user authentication, and admin dashboard"
        },
        {
            "name": "Data Analytics Dashboard",
            "tech": "Python, Pandas, Plotly, D3.js",
            "description": "Real-time data visualization and analytics tool with interactive charts and reporting features"
        },
        {
            "name": "Task Management System",
            "tech": "Flask, SQLAlchemy, Bootstrap, jQuery",
            "description": "Project management tool with team collaboration, file sharing, and progress tracking"
        },
        {
            "name": "Weather Prediction API",
            "tech": "Python, Scikit-learn, FastAPI",
            "description": "Machine learning API for weather forecasting using historical data and neural networks"
        }
    ],
    "education": "Computer Science & AI/ML",
    "location": "Available for remote work worldwide",
    "contact": "Available through this chat interface",
    "certifications": ["AWS Cloud Practitioner", "Google Analytics", "Python Institute PCAP"],
    "languages": ["English (Native)", "Spanish (Conversational)"]
}

# Load portfolio data
def load_portfolio():
    try:
        if os.path.exists("portfolio.json"):
            with open("portfolio.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info("📊 Portfolio data loaded from file")
                return data
        else:
            logger.info("📊 Using default portfolio data")
            return DEFAULT_PORTFOLIO
    except Exception as e:
        logger.error(f"Error loading portfolio: {e}")
        return DEFAULT_PORTFOLIO

portfolio_data = load_portfolio()

# In-memory session storage
chat_sessions = {}
MAX_SESSIONS = int(os.getenv('MAX_SESSIONS', '500'))

def cleanup_old_sessions():
    """Remove old sessions to prevent memory issues"""
    if len(chat_sessions) > MAX_SESSIONS:
        keep_count = int(MAX_SESSIONS * 0.8)
        sessions_to_keep = dict(list(chat_sessions.items())[-keep_count:])
        chat_sessions.clear()
        chat_sessions.update(sessions_to_keep)
        logger.info(f"🧹 Cleaned up sessions, keeping {len(chat_sessions)} sessions")

def create_system_prompt():
    """Create enhanced system prompt for AI assistant"""
    return f"""You are an advanced AI assistant with expertise across multiple domains. You can help with ANY topic and are not limited to portfolio questions.

🤖 CAPABILITIES:
- Programming & Software Development (All languages and frameworks)
- Data Science & Machine Learning
- Web Development & System Architecture  
- Problem-solving & Code Debugging
- Creative Writing & Content Creation
- Academic Research & Analysis
- Business Strategy & Career Advice
- Technology Trends & Best Practices
- General Knowledge & Current Events
- Math, Science, Engineering
- Personal Productivity & Life Advice

💼 PORTFOLIO INFORMATION (use when relevant):
{json.dumps(portfolio_data, indent=2)}

🎯 GUIDELINES:
- Help with ANY topic the user asks about
- Provide detailed, actionable responses
- Use examples and code snippets when helpful
- Ask clarifying questions for complex requests
- Be conversational but professional
- Offer step-by-step guidance
- Be honest about limitations
- You're a full-featured AI assistant, not just a portfolio bot!

Remember: Answer ANY question - programming, life advice, creative projects, technical problems, learning guidance, or portfolio information!"""

def get_smart_fallback_response(user_input):
    """Generate intelligent responses even without API"""
    user_lower = user_input.lower()
    
    # Programming help
    programming_keywords = ['code', 'programming', 'python', 'javascript', 'react', 'flask', 'html', 'css', 'debug', 'function', 'algorithm', 'error', 'help me code']
    if any(keyword in user_lower for keyword in programming_keywords):
        return """💻 **Programming Help Available!**

I can help with programming concepts even in offline mode:

**🐍 Python**: 
• Flask/Django web development
• Data science with Pandas/NumPy
• Machine learning basics
• API development
• Automation scripts

**⚛️ React/JavaScript**:
• Component architecture
• State management
• Event handling
• API integration
• Modern ES6+ features

**🌐 Web Development**:
• HTML/CSS best practices
• Responsive design
• REST API design
• Database integration
• Deployment strategies

**Common Debugging Steps**:
1. Check console for error messages
2. Verify variable names and syntax
3. Test with smaller code pieces
4. Use print/console.log statements
5. Check API endpoints and data flow

What specific programming challenge can I help you with? Share your code and I'll provide guidance!"""

    # Portfolio questions
    portfolio_keywords = ['portfolio', 'skills', 'experience', 'projects', 'background', 'about you', 'resume', 'cv', 'work', 'qualifications']
    if any(keyword in user_lower for keyword in portfolio_keywords):
        skills_text = ', '.join(portfolio_data['skills'])
        projects_text = '\n'.join([
            f"**{p['name']}**: {p['description']}\n   *Tech: {p['tech']}*"
            for p in portfolio_data['projects']
        ])
        
        return f"""📋 **Professional Portfolio**

**👨‍💻 {portfolio_data['title']}**
**📍 {portfolio_data['location']}**

**🛠 Technical Skills**: 
{skills_text}

**💼 Experience**: {portfolio_data['experience']}

**🚀 Key Projects**:
{projects_text}

**🎓 Education**: {portfolio_data['education']}

**📜 Certifications**: {', '.join(portfolio_data.get('certifications', ['Various technical certifications']))}

**🌍 Languages**: {', '.join(portfolio_data.get('languages', ['English']))}

I'd love to discuss any of these projects in detail, explain my technical approach, or answer questions about my experience with specific technologies!

What aspect of my background interests you most?"""

    # General AI assistance  
    if any(word in user_lower for word in ['how', 'what', 'why', 'explain', 'help', 'advice', 'recommend', 'suggest']):
        return f"""🤔 **Great Question!** You asked: *"{user_input}"*

While I'm currently in offline mode, I can still provide valuable insights:

**💡 Available Assistance**:
• **Technical Guidance** - Programming concepts, best practices, debugging strategies
• **Career Advice** - Based on my experience in tech industry
• **Learning Paths** - Roadmaps for different technologies and skills
• **Project Planning** - Architecture recommendations and tech stack selection
• **Portfolio Discussion** - Detailed breakdown of my projects and experience

**🔧 For Advanced AI Features** (detailed code generation, complex analysis, real-time debugging):
- Full API integration enables comprehensive assistance
- Can provide detailed code examples and solutions
- Real-time problem-solving capabilities

**What specific area would you like me to focus on?** I'm here to help whether it's technical questions, career guidance, or learning about my portfolio!"""

    # Default response
    return f"""👋 **Hello!** Thanks for your message: *"{user_input}"*

I'm an AI assistant that can help with:

**🤖 Technical Topics**:
• Programming (Python, JavaScript, React, Flask, etc.)
• Web development and system design
• Data science and machine learning
• Code debugging and optimization

**💼 Portfolio Information**:
• My skills and technical expertise
• Detailed project breakdowns
• Professional experience and background
• Technology recommendations based on my work

**🎯 General Assistance**:
• Learning guidance and career advice
• Best practices and industry insights
• Project planning and architecture
• Problem-solving approaches

**What would you like to explore?** Feel free to ask about programming, my portfolio, or any topic you're curious about!

*Currently running in offline mode - full AI capabilities available once API is configured.*"""

@app.route("/")
def index():
    """Serve the main chat interface"""
    try:
        return render_template("index.html")
    except Exception as e:
        logger.error(f"Error serving index page: {e}")
        return """
        <html>
        <head><title>AI Portfolio Assistant</title></head>
        <body style="font-family: Arial; padding: 40px; text-align: center;">
            <h1>🤖 AI Portfolio Assistant</h1>
            <p>Template file not found. The API is working!</p>
            <p><a href="/health">Check System Health</a></p>
        </body>
        </html>
        """

@app.route("/ask", methods=["POST"])
def ask():
    """Handle chat messages with robust error handling"""
    try:
        # Cleanup sessions periodically
        if len(chat_sessions) > 100:
            cleanup_old_sessions()
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        user_input = data.get("message", "").strip()
        session_id = data.get("session_id", f"session_{int(datetime.now().timestamp())}")
        
        if not user_input:
            return jsonify({"error": "Message cannot be empty"}), 400
        
        if len(user_input) > 2000:
            return jsonify({"error": "Message too long. Please keep it under 2000 characters."}), 400
        
        # Initialize session
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        
        # Add user message to history
        chat_sessions[session_id].append({
            "role": "user", 
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        bot_reply = ""
        api_success = False
        
        # Try API call if client is available
        if client:
            try:
                # Prepare messages for API
                messages = [
                    {"role": "system", "content": create_system_prompt()}
                ]
                
                # Add recent conversation history
                recent_messages = chat_sessions[session_id][-10:]
                for msg in recent_messages:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                
                # Call API with error handling
                response = client.chat.completions.create(
                    model="deepseek/deepseek-chat-v3.1:free",
                    messages=messages,
                    max_tokens=600,
                    temperature=0.7
                )
                
                bot_reply = response.choices[0].message.content.strip()
                api_success = True
                logger.info(f"✅ Successful API call for session {session_id}")
                
            except Exception as api_error:
                logger.error(f"❌ API Error: {api_error}")
                bot_reply = get_smart_fallback_response(user_input)
                api_success = False
        else:
            logger.info("🔄 Using intelligent fallback response")
            bot_reply = get_smart_fallback_response(user_input)
        
        # Add bot response to history
        chat_sessions[session_id].append({
            "role": "assistant", 
            "content": bot_reply,
            "timestamp": datetime.now().isoformat()
        })
        
        # Limit session history
        if len(chat_sessions[session_id]) > 50:
            chat_sessions[session_id] = chat_sessions[session_id][-50:]
        
        return jsonify({
            "reply": bot_reply,
            "session_id": session_id,
            "status": "success" if api_success else "fallback",
            "api_available": api_success,
            "message_count": len(chat_sessions[session_id]),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error in /ask endpoint: {e}")
        
        # Provide helpful error response
        error_reply = """🔧 **Technical Assistant Available**

I'm here to help! Even with technical limitations, I can assist with:

**💻 Programming Support**:
• Code structure and best practices
• Debugging strategies and common solutions  
• Framework guidance (React, Flask, Node.js)
• Learning resources and career paths

**📋 Portfolio Information**:
• Technical skills and expertise
• Project details and technology choices
• Professional experience and background
• Development approach and methodologies

**What specific topic can I help you with?** I'm ready to provide guidance on programming, portfolio questions, or tech career advice!"""
        
        return jsonify({
            "reply": error_reply,
            "status": "error_handled",
            "timestamp": datetime.now().isoformat()
        }), 200

@app.route("/health")
def health():
    """Comprehensive health check for monitoring"""
    try:
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "environment": app.config.get('ENV', 'unknown'),
            "debug_mode": app.config.get('DEBUG', False),
            "api_key_configured": bool(API_KEY),
            "openai_client_available": bool(client),
            "portfolio_loaded": bool(portfolio_data),
            "active_sessions": len(chat_sessions),
            "total_projects": len(portfolio_data.get('projects', [])),
            "skills_count": len(portfolio_data.get('skills', [])),
            "fallback_mode": not bool(client),
            "port": PORT,
            "host": HOST,
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/portfolio")
def portfolio():
    """Get portfolio data"""
    return jsonify({
        "portfolio": portfolio_data,
        "timestamp": datetime.now().isoformat(),
        "skills_count": len(portfolio_data.get('skills', [])),
        "projects_count": len(portfolio_data.get('projects', [])),
        "status": "loaded"
    })

@app.route("/test")
def test():
    """Simple test endpoint"""
    return jsonify({
        "message": "AI Portfolio Assistant is running!",
        "timestamp": datetime.now().isoformat(),
        "environment": "Render Production",
        "api_status": "available" if client else "fallback_mode"
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": ["/", "/ask", "/health", "/portfolio", "/test"],
        "timestamp": datetime.now().isoformat()
    }), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    return jsonify({
        "error": "Internal server error",
        "message": "The service encountered an issue but is still running",
        "timestamp": datetime.now().isoformat()
    }), 500

if __name__ == "__main__":
    # Startup logging
    logger.info("🚀 Starting AI Portfolio Assistant")
    logger.info(f"🌍 Environment: {app.config['ENV']}")
    logger.info(f"🔧 Debug mode: {app.config['DEBUG']}")
    logger.info(f"📊 Portfolio loaded: {bool(portfolio_data)}")
    logger.info(f"🔑 API configured: {bool(API_KEY)}")
    logger.info(f"🤖 OpenAI client: {'✅ Ready' if client else '❌ Fallback Mode'}")
    logger.info(f"🌐 Starting server on {HOST}:{PORT}")
    
    if not API_KEY:
        logger.warning("⚠️ No OpenRouter API key found!")
        logger.warning("   Add OPENROUTER_API_KEY to environment variables")
        logger.warning("   Get key from: https://openrouter.ai/keys")
    
    app.run(
        host=HOST,
        port=PORT,
        debug=app.config['DEBUG']
    )
else:
    # This runs when deployed (gunicorn)
    logger.info("🌐 AI Portfolio Assistant deployed on Render")
    logger.info(f"🤖 API Status: {'Available' if client else 'Fallback Mode'}")
    logger.info(f"📊 Portfolio: {len(portfolio_data.get('projects', []))} projects loaded")
