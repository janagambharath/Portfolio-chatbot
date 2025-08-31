import os
import logging
import json
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
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
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key-2024')
app.config['DEBUG'] = False

# Get configuration
API_KEY = os.getenv("OPENROUTER_API_KEY")
PORT = int(os.getenv("PORT", 10000))

# Portfolio data
portfolio_data = {
    "name": "AI Portfolio Assistant",
    "title": "Full Stack Developer & AI Specialist", 
    "skills": [
        "Python", "JavaScript", "React", "Flask", "Node.js",
        "Machine Learning", "AI Development", "MongoDB",
        "PostgreSQL", "Docker", "AWS", "Git", "REST APIs",
        "HTML/CSS", "Bootstrap", "jQuery", "Express.js"
    ],
    "experience": "5+ years of full-stack development experience",
    "projects": [
        {
            "name": "AI Chatbot Platform",
            "tech": "Python, OpenAI API, Flask, React, JavaScript",
            "description": "Intelligent conversational AI system with portfolio integration and real-time streaming responses"
        },
        {
            "name": "E-commerce Platform",
            "tech": "React, Node.js, MongoDB, Stripe API, Express",
            "description": "Full-stack shopping platform with payment processing, user authentication, and admin dashboard"
        },
        {
            "name": "Data Analytics Dashboard", 
            "tech": "Python, Pandas, Plotly, D3.js, PostgreSQL",
            "description": "Real-time data visualization tool with interactive charts, reporting, and data export features"
        },
        {
            "name": "Task Management System",
            "tech": "Flask, SQLAlchemy, Bootstrap, jQuery",
            "description": "Project management application with team collaboration, file uploads, and progress tracking"
        }
    ],
    "education": "Computer Science & Artificial Intelligence",
    "certifications": ["AWS Cloud Practitioner", "Google Analytics Certified", "Python Institute PCAP"],
    "location": "Available for remote work globally",
    "contact": "Connect through this chat interface"
}

# Chat sessions storage
chat_sessions = {}

# ==========================================
# DIRECT HTTP API CALL (REPLACES OPENAI LIB)
# ==========================================

def call_ai_api(messages):
    """
    Direct HTTP call to OpenRouter API
    This replaces the problematic OpenAI library
    """
    if not API_KEY or not API_KEY.strip():
        raise Exception("No API key available")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {API_KEY.strip()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://bharathai.onrender.com",
        "X-Title": "AI Portfolio Assistant"
    }
    
    payload = {
        "model": "deepseek/deepseek-chat-v3.1:free",
        "messages": messages,
        "max_tokens": 700,
        "temperature": 0.7,
        "top_p": 0.9,
        "frequency_penalty": 0.1,
        "presence_penalty": 0.1,
        "stream": False
    }
    
    try:
        response = requests.post(
            url, 
            headers=headers, 
            json=payload, 
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        elif response.status_code == 401:
            raise Exception("Invalid API key - check your OPENROUTER_API_KEY")
        elif response.status_code == 429:
            raise Exception("Rate limit exceeded - please wait a moment")
        elif response.status_code == 500:
            raise Exception("OpenRouter service temporarily unavailable")
        else:
            raise Exception(f"API Error {response.status_code}: {response.text}")
            
    except requests.exceptions.Timeout:
        raise Exception("API request timed out - please try again")
    except requests.exceptions.ConnectionError:
        raise Exception("Connection error - check internet connectivity")
    except Exception as e:
        raise Exception(f"API call failed: {str(e)}")

def create_system_prompt():
    """Create enhanced system prompt"""
    return f"""You are an advanced AI assistant with expertise across all domains. You can help with ANY topic:

🤖 GENERAL AI CAPABILITIES:
- Programming & Software Development (Python, JavaScript, React, Flask, Node.js, etc.)
- Data Science & Machine Learning (Pandas, NumPy, Scikit-learn, TensorFlow)
- Web Development (Frontend/Backend, APIs, Databases, Deployment)
- Problem-solving & Code Debugging
- Creative Writing & Content Creation
- Academic Research & Analysis
- Business Strategy & Career Advice
- Technology Trends & Best Practices
- Math, Science, Engineering
- General Knowledge & Current Events

💼 PORTFOLIO EXPERTISE (when relevant):
{json.dumps(portfolio_data, indent=2)}

🎯 INTERACTION STYLE:
- Be helpful, knowledgeable, and conversational
- Provide detailed explanations with practical examples
- Offer code snippets and step-by-step guidance
- Ask clarifying questions for complex topics
- Be encouraging and supportive
- Maintain professional yet friendly tone
- You can discuss ANY topic - not limited to portfolio only!

Remember: You're a full-featured AI assistant capable of helping with programming, creative projects, learning, problem-solving, and professional portfolio discussions!"""

def get_intelligent_fallback(user_input):
    """Enhanced fallback responses for when API is unavailable"""
    user_lower = user_input.lower()
    
    # Programming and technical questions
    if any(keyword in user_lower for keyword in [
        'code', 'programming', 'python', 'javascript', 'react', 'flask', 
        'html', 'css', 'debug', 'error', 'function', 'algorithm', 'api',
        'database', 'sql', 'git', 'deployment', 'help me', 'how to'
    ]):
        return """💻 **Programming & Technical Assistance**

I can help with programming concepts and provide guidance:

**🐍 Python Development**:
• Flask/Django web applications
• Data analysis with Pandas/NumPy  
• API development and integration
• Error handling and debugging
• Best practices and code structure

**⚛️ React & JavaScript**:
• Component-based architecture
• State management (useState, useEffect)
• Event handling and user interactions
• API integration and data fetching
• Modern ES6+ JavaScript features

**🌐 Web Development**:
• HTML5 semantic structure
• CSS3 animations and responsive design
• RESTful API design principles
• Database integration (SQL/NoSQL)
• Version control with Git

**🔧 Common Solutions**:
• **Debugging**: Use console.log, check browser dev tools, test incrementally
• **APIs**: Verify endpoints, handle errors, validate JSON data
• **React**: Check component props, state updates, and lifecycle methods
• **Python**: Use print statements, check indentation, handle exceptions

**Share your specific code challenge and I'll provide detailed guidance!** What are you working on?"""

    # Portfolio and professional questions
    elif any(keyword in user_lower for keyword in [
        'portfolio', 'skills', 'experience', 'projects', 'background', 'about you',
        'resume', 'cv', 'work', 'career', 'qualifications', 'education'
    ]):
        skills_formatted = ', '.join(portfolio_data['skills'])
        projects_formatted = '\n'.join([
            f"**{project['name']}**\n   {project['description']}\n   *Technologies: {project['tech']}*\n"
            for project in portfolio_data['projects']
        ])
        
        return f"""📋 **Professional Portfolio & Background**

**👨‍💻 {portfolio_data['title']}**
**📍 {portfolio_data['location']}**

**🛠 Technical Expertise**:
{skills_formatted}

**💼 Professional Experience**: 
{portfolio_data['experience']}

**🚀 Featured Projects**:
{projects_formatted}

**🎓 Education**: {portfolio_data['education']}

**📜 Certifications**: {', '.join(portfolio_data.get('certifications', []))}

**🌍 Languages**: {', '.join(portfolio_data.get('languages', ['English (Native)']))}

**💬 Let's Discuss**: I'd love to dive deeper into any of these projects, explain my technical approach, or discuss how my experience could benefit your needs. What interests you most?"""

    # Learning and educational questions
    elif any(keyword in user_lower for keyword in [
        'learn', 'tutorial', 'guide', 'explain', 'understand', 'beginner',
        'start', 'getting started', 'roadmap', 'study', 'course'
    ]):
        return f"""📚 **Learning & Educational Guidance**

Based on your question: *"{user_input}"*

**🎯 Learning Paths I Can Help With**:

**Programming Fundamentals**:
• Python basics → Flask/Django → Data Science
• JavaScript basics → React → Full-stack development
• HTML/CSS → Responsive design → Modern frameworks

**Specialized Tracks**:
• **Web Development**: Frontend (React) + Backend (Flask/Node.js) + Database
• **Data Science**: Python + Pandas + Machine Learning + Visualization
• **AI/ML**: Python + Scikit-learn + TensorFlow + OpenAI APIs
• **Full-Stack**: JavaScript ecosystem + Python backend + DevOps

**🛠 Based on My Experience**:
I've worked extensively with {', '.join(portfolio_data['skills'][:5])} and can provide practical guidance from real project experience.

**📈 Recommended Learning Approach**:
1. Start with fundamentals and build small projects
2. Practice with real-world scenarios
3. Build a portfolio of diverse projects
4. Learn version control (Git) and deployment
5. Stay updated with industry trends

**What specific technology or concept would you like to explore?** I can provide a detailed learning roadmap!"""

    # General assistance
    else:
        return f"""🤖 **AI Assistant Ready to Help!**

You asked: *"{user_input}"*

I'm here to assist with a wide range of topics:

**💻 Technical Support**:
• Programming languages and frameworks
• Code debugging and optimization
• System architecture and design patterns
• Best practices and modern development approaches

**📊 Data & Analytics**:
• Data analysis and visualization
• Database design and optimization
• Machine learning concepts and applications
• Statistical analysis and reporting

**🎯 Professional Guidance**:
• Career development in tech
• Portfolio optimization and presentation
• Industry trends and skill recommendations
• Project planning and execution strategies

**🧠 Problem Solving**:
• Breaking down complex challenges
• Algorithm design and optimization
• Troubleshooting and debugging strategies
• Performance improvement techniques

**Based on my background in {portfolio_data['title'].lower()}**, I can provide practical insights from real-world experience.

**What specific area can I help you with today?** Feel free to ask about coding challenges, career advice, project guidance, or anything else!"""

@app.route("/")
def index():
    """Serve main interface"""
    try:
        return render_template("index.html")
    except Exception as e:
        logger.error(f"Template error: {e}")
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI Portfolio Assistant</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { font-family: Arial, sans-serif; background: #f0f2f5; padding: 40px; text-align: center; }
                .container { max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
                .btn { background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 10px; display: inline-block; }
                .btn:hover { background: #0056b3; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 AI Portfolio Assistant</h1>
                <p>Backend is running successfully!</p>
                <p>The chat interface will be available once templates are configured.</p>
                <div>
                    <a href="/health" class="btn">System Health</a>
                    <a href="/portfolio" class="btn">Portfolio Data</a>
                    <a href="/test" class="btn">API Test</a>
                </div>
            </div>
        </body>
        </html>
        """

@app.route("/ask", methods=["POST"])
def ask():
    """Handle chat messages using direct HTTP calls"""
    try:
        # Get request data
        data = request.get_json() or {}
        user_input = data.get("message", "").strip()
        session_id = data.get("session_id", f"session_{int(datetime.now().timestamp())}")
        
        if not user_input:
            return jsonify({"error": "Message required"}), 400
        
        if len(user_input) > 2000:
            return jsonify({"error": "Message too long"}), 400
        
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
        
        # ==========================================
        # TRY DIRECT HTTP API CALL
        # ==========================================
        if API_KEY and API_KEY.strip():
            try:
                # Prepare messages
                messages = [
                    {"role": "system", "content": create_system_prompt()}
                ] + chat_sessions[session_id][-10:]  # Last 10 messages for context
                
                # DIRECT HTTP CALL TO OPENROUTER
                bot_reply = call_openrouter_direct(messages, API_KEY.strip())
                api_success = True
                logger.info("✅ Direct API call successful")
                
            except Exception as api_error:
                logger.error(f"❌ API Error: {str(api_error)}")
                bot_reply = get_intelligent_fallback(user_input)
                api_success = False
        else:
            logger.info("🔄 No API key - using intelligent fallback")
            bot_reply = get_intelligent_fallback(user_input)
        
        # Add bot response to history
        chat_sessions[session_id].append({
            "role": "assistant",
            "content": bot_reply,
            "timestamp": datetime.now().isoformat()
        })
        
        # Cleanup old messages
        if len(chat_sessions[session_id]) > 50:
            chat_sessions[session_id] = chat_sessions[session_id][-50:]
        
        return jsonify({
            "reply": bot_reply,
            "session_id": session_id,
            "status": "success" if api_success else "fallback",
            "api_available": api_success,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Ask endpoint error: {str(e)}")
        
        fallback_reply = """🤖 **AI Assistant Active**

I'm here to help with any questions! I can assist with:

**💻 Programming**: Python, JavaScript, React, Flask, debugging, best practices
**📊 Data Science**: Analysis, visualization, machine learning concepts  
**🌐 Web Development**: Frontend, backend, APIs, databases, deployment
**💼 Portfolio**: My skills, projects, experience, and technical background
**🎯 General Topics**: Learning guidance, career advice, problem-solving

What can I help you with today?"""
        
        return jsonify({
            "reply": fallback_reply,
            "status": "error_handled",
            "timestamp": datetime.now().isoformat()
        }), 200

# ==========================================
# DIRECT HTTP FUNCTION (CORE IMPLEMENTATION)
# ==========================================

def call_openrouter_direct(messages, api_key):
    """
    Direct HTTP call to OpenRouter API
    This completely bypasses the OpenAI library that's causing issues
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://bharathai.onrender.com",
        "X-Title": "AI Portfolio Assistant"
    }
    
    payload = {
        "model": "deepseek/deepseek-chat-v3.1:free",
        "messages": messages,
        "max_tokens": 700,
        "temperature": 0.7,
        "top_p": 0.9,
        "frequency_penalty": 0.1,
        "presence_penalty": 0.1
    }
    
    logger.info(f"🔄 Making API call to {url}")
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        logger.info(f"📡 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            logger.info("✅ API call successful")
            return content
        else:
            error_msg = f"API Error {response.status_code}: {response.text[:200]}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
    except requests.exceptions.Timeout:
        logger.error("❌ API timeout")
        raise Exception("Request timed out")
    except requests.exceptions.ConnectionError:
        logger.error("❌ Connection error")
        raise Exception("Connection failed")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        raise

def create_system_prompt():
    """System prompt for AI assistant"""
    return f"""You are an advanced AI assistant with broad expertise. You can help with ANY topic including:

🤖 FULL AI CAPABILITIES:
- Programming (Python, JavaScript, React, Flask, Node.js, etc.)
- Data Science & Machine Learning
- Web Development (Frontend/Backend)
- Problem-solving & Debugging
- Creative Writing & Content Creation
- Academic Research & Analysis
- Business & Career Advice
- Technology & Industry Trends
- Math, Science, Engineering
- General Knowledge & Current Events

💼 PORTFOLIO CONTEXT (use when relevant):
{json.dumps(portfolio_data, indent=2)}

🎯 GUIDELINES:
- Answer ANY question the user asks
- Provide detailed, helpful responses
- Use examples and code when relevant
- Be conversational and professional
- Offer step-by-step guidance
- You're a full AI assistant, not just a portfolio bot!"""

def get_intelligent_fallback(user_input):
    """Smart responses when API is unavailable"""
    user_lower = user_input.lower()
    
    # Programming help
    if any(word in user_lower for word in ['code', 'programming', 'python', 'javascript', 'react', 'debug', 'error', 'help']):
        return """💻 **Programming Assistant Ready!**

I can help with coding challenges based on my experience:

**🐍 Python Guidance**:
• Flask web applications and API development
• Data processing with Pandas and NumPy
• Error handling and debugging strategies
• Best practices for clean, maintainable code

**⚛️ React Development**:
• Component architecture and state management
• Event handling and user interactions
• API integration and data flow
• Modern hooks and functional components

**🔧 Debugging Strategies**:
1. **Check the Console** - Look for error messages and warnings
2. **Isolate the Problem** - Test components/functions individually  
3. **Verify Data
