# 🤖 Bharath AI - Portfolio Chatbot

An intelligent AI-powered chatbot that serves as an interactive portfolio, showcasing skills, projects, and experience. Built with Flask and powered by OpenRouter API.

---

## 🌟 Features

- **🎯 Interactive Portfolio** - Chat interface to explore skills, projects, and experience
- **🧠 AI-Powered Responses** - Natural language understanding using LLM
- **🎨 Beautiful UI** - Modern, responsive design with dark mode support
- **💬 Context-Aware** - Remembers conversation history for natural dialogue
- **🎤 Voice Input** - Speak your questions using speech recognition
- **🌈 Theme Switcher** - Multiple color themes (Purple, Blue, Green, Orange)
- **📱 Mobile Responsive** - Optimized for all screen sizes
- **⚡ Fast & Efficient** - Rate limiting and session management
- **🔒 Secure** - Environment variable configuration for sensitive data

---

## 📋 Table of Contents

- [Demo](#-demo)
- [Tech Stack](#-tech-stack)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [API Endpoints](#-api-endpoints)
- [Features Deep Dive](#-features-deep-dive)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🚀 Demo

**Live Demo**: [https://bharath-portfolio-lvea.onrender.com/](https://bharath-portfolio-lvea.onrender.com/)

### Screenshots

```
+----------------------------------+
|  🤖 Bharath's AI                 |
|  Ask me anything about my        |
|  skills, experience, projects!   |
+----------------------------------+
| [Resume] [GitHub] [LinkedIn] [YT]|
+----------------------------------+
| [Skills] [Projects] [Education]  |
+----------------------------------+
|                                  |
|  💬 Chat Messages Here           |
|                                  |
+----------------------------------+
| 🎤 | Type your message... | Send |
+----------------------------------+
```

---

## 🛠️ Tech Stack

### Backend
- **Flask** - Python web framework
- **OpenRouter API** - LLM inference (Llama 3.2 3B)
- **Requests** - HTTP library for API calls
- **Flask-CORS** - Cross-origin resource sharing

### Frontend
- **HTML5/CSS3** - Modern web standards
- **JavaScript** - Interactive functionality
- **Font Awesome** - Beautiful icons
- **Web Speech API** - Voice recognition

### Deployment
- **Render** - Cloud platform hosting
- **Gunicorn** - WSGI HTTP server

---

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- OpenRouter API key ([Get one here](https://openrouter.ai/))
- Git (optional)

### Step 1: Clone the Repository

```bash
git clone https://github.com/janagambharath/bharath-portfolio.git
cd bharath-portfolio
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# Required
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Optional
PORT=10000
OPENROUTER_MODEL=meta-llama/llama-3.2-3b-instruct:free
SITE_URL=http://localhost:10000/
SITE_NAME=Bharath's AI Portfolio
MAX_HISTORY_TURNS=6
RATE_LIMIT_MAX=30
```

### Step 5: Run the Application

```bash
python app.py
```

Visit `http://localhost:10000` in your browser!

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENROUTER_API_KEY` | API key from OpenRouter | - | ✅ Yes |
| `PORT` | Server port | 10000 | ❌ No |
| `OPENROUTER_MODEL` | LLM model to use | llama-3.2-3b-instruct:free | ❌ No |
| `SITE_URL` | Your website URL | localhost | ❌ No |
| `SITE_NAME` | Site name for API | Bharath's AI Portfolio | ❌ No |
| `PORTFOLIO_FILE` | Portfolio data file | portfolio.json | ❌ No |
| `MAX_HISTORY_TURNS` | Conversation history limit | 6 | ❌ No |
| `RATE_LIMIT_MAX` | Max requests per minute | 30 | ❌ No |

### Portfolio Configuration

Edit `portfolio.json` to customize your information:

```json
{
  "personal_info": {
    "name": "Your Name",
    "role": "Your Role",
    "email": "your@email.com",
    "linkedin": "https://linkedin.com/in/yourprofile",
    "github": "https://github.com/yourusername"
  },
  "skills": {
    "all_skills": ["Python", "Flask", "AI", "NLP"]
  },
  "projects": [
    {
      "name": "Project Name",
      "description": "Project description",
      "technologies": ["Tech1", "Tech2"],
      "live_demo": "https://project-url.com"
    }
  ]
}
```

---

## 💻 Usage

### Basic Chat

```javascript
// Send a message
fetch('/ask', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        message: "What are your skills?",
        session_id: "optional-session-id"
    })
})
.then(res => res.json())
.then(data => console.log(data.reply));
```

### Quick Reply Buttons

Pre-configured questions users can click:
- **Skills** - "Tell me about your skills"
- **Projects** - "What projects have you built?"
- **Education** - "Tell me about your education"
- **Goals** - "What are your goals?"
- **YouTube** - "Tell me about your YouTube channel"

### Voice Input

Click the microphone button and speak your question. The app uses the Web Speech API to transcribe your speech.

### Theme Switching

- **Light/Dark Mode**: Toggle between light and dark themes
- **Color Themes**: Switch between Purple, Blue, Green, and Orange

---

## 🔌 API Endpoints

### `GET /`
Homepage with chat interface

**Response**: HTML page

---

### `GET /health`
Health check endpoint

**Response**:
```json
{
  "status": "healthy",
  "api_configured": true,
  "model": "meta-llama/llama-3.2-3b-instruct:free",
  "portfolio_name": "Janagam Bharath",
  "projects_count": 4,
  "skills_count": 15,
  "active_sessions": 42,
  "uptime_seconds": 3600
}
```

---

### `GET /portfolio`
Get complete portfolio data

**Response**:
```json
{
  "personal_info": {...},
  "skills": {...},
  "projects": [...],
  "education": [...],
  "achievements": [...]
}
```

---

### `GET /sessions`
View active chat sessions

**Response**:
```json
{
  "session_count": 42,
  "sessions": {
    "session_abc123": 8,
    "session_def456": 12
  }
}
```

---

### `POST /ask`
Send a chat message

**Request**:
```json
{
  "message": "What are your skills?",
  "session_id": "optional-session-id"
}
```

**Response**:
```json
{
  "reply": "My core skills include Python, Flask, Hugging Face...",
  "session_id": "session_abc123",
  "status": "success",
  "request_id": "req_xyz789"
}
```

**Rate Limit**: 30 requests per minute per IP

---

## 🎯 Features Deep Dive

### 1. Conversation Memory

The chatbot maintains context across multiple messages:

```python
# Remembers last 6 turns (12 messages)
MAX_HISTORY_TURNS = 6

# Session stored in memory
chat_sessions = {
    "session_id": [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello! How can I help?"}
    ]
}
```

### 2. Anti-Repetition System

Multiple mechanisms prevent repetitive responses:

- **Short System Prompt** (300 tokens vs 1500)
- **High Temperature** (0.85 for creativity)
- **Penalties**: presence_penalty=0.6, frequency_penalty=0.7
- **Response Variations**: 3+ variations per topic
- **Context Awareness**: Checks recent responses

### 3. Fallback Intelligence

If API fails, uses smart fallback responses:

```python
# Keyword detection
if "skills" in message:
    # Returns one of 3 varied responses
    # Checks conversation to avoid repeats
```

### 4. Rate Limiting

Protects against abuse:

```python
# 30 requests per 60 seconds per IP
RATE_LIMIT_MAX = 30
RATE_LIMIT_WINDOW = 60
```

### 5. Session Persistence

Sessions saved to disk:

```python
# Saved on exit
chat_sessions.json

# Restored on startup
# Maximum 1000 sessions kept
```

---

## 🚀 Deployment

### Deploy to Render

1. **Create Account**: Sign up at [render.com](https://render.com)

2. **New Web Service**: 
   - Connect your GitHub repository
   - Select Python environment

3. **Configure**:
   ```
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn app:app
   ```

4. **Environment Variables**:
   Add your `OPENROUTER_API_KEY`

5. **Deploy**: Click "Create Web Service"

### Deploy to Heroku

```bash
# Install Heroku CLI
heroku login

# Create app
heroku create your-app-name

# Set environment variables
heroku config:set OPENROUTER_API_KEY=your_key

# Deploy
git push heroku main
```

### Deploy to Railway

1. Click "New Project"
2. Select "Deploy from GitHub"
3. Add `OPENROUTER_API_KEY` environment variable
4. Deploy!

---

## 🐛 Troubleshooting

### Issue: Repetitive Responses

**Solution**: Already fixed in `app_fixed.py`! Key changes:
- Shortened system prompt (300 tokens)
- Increased temperature (0.85)
- Added penalties (presence: 0.6, frequency: 0.7)

### Issue: API Not Working

**Check**:
```bash
# Visit health endpoint
curl http://localhost:10000/health

# Should show: "api_configured": true
```

**Fix**:
- Verify `OPENROUTER_API_KEY` is set correctly
- Check API key hasn't expired
- Visit OpenRouter dashboard for issues

### Issue: Slow Responses

**Possible Causes**:
- Model overloaded (try different model)
- Network issues
- API rate limiting

**Solutions**:
```python
# Try faster model
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free

# Or reduce timeout
timeout=15  # Instead of 30
```

### Issue: Session Lost

**Solution**: Sessions stored in memory by default. For persistence:
```python
# Sessions auto-saved to chat_sessions.json
# Restored on server restart
```

### Issue: CORS Errors

**Solution**: Already enabled!
```python
from flask_cors import CORS
CORS(app)
```

---

## 📊 Performance Tips

### 1. Optimize Response Time

```python
# Use smaller models for faster responses
DEFAULT_MODEL = "meta-llama/llama-3.2-3b-instruct:free"  # Fast

# Or larger for better quality
DEFAULT_MODEL = "meta-llama/llama-3.1-8b-instruct:free"  # Better
```

### 2. Reduce Token Usage

```python
# Shorten max_tokens for faster responses
max_tokens = 600  # Instead of 800
```

### 3. Cache Common Responses

```python
# Add response caching for FAQ
response_cache = {
    "what are your skills": "cached_response_here"
}
```

---

## 🧪 Testing

### Manual Testing

```bash
# Test health endpoint
curl http://localhost:10000/health

# Test chat endpoint
curl -X POST http://localhost:10000/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "What are your skills?"}'
```

### Test Variations

```python
# Ask same question 3 times
questions = [
    "What are your skills?",
    "What are your skills?",
    "What are your skills?"
]

# Should get 3 DIFFERENT responses
```

---

## 🔐 Security

### Best Practices

1. **Never commit API keys**
   ```bash
   # Use .env file (already in .gitignore)
   OPENROUTER_API_KEY=your_key
   ```

2. **Use environment variables**
   ```python
   # ✅ Good
   api_key = os.getenv("OPENROUTER_API_KEY")
   
   # ❌ Bad
   api_key = "sk-or-v1-abc123..."
   ```

3. **Enable rate limiting**
   ```python
   # Already implemented!
   @rate_limit()
   def ask():
       ...
   ```

4. **Validate input**
   ```python
   # Already implemented!
   if not user_input:
       return error
   ```

---

## 📈 Roadmap

### Planned Features

- [ ] Response analytics dashboard
- [ ] Multi-language support
- [ ] Custom skill training
- [ ] Export conversation history
- [ ] Integration with portfolio website
- [ ] User feedback collection
- [ ] A/B testing for prompts
- [ ] Advanced sentiment analysis

---

## 🤝 Contributing

Contributions are welcome! Here's how:

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Commit your changes**
   ```bash
   git commit -m "Add amazing feature"
   ```
4. **Push to the branch**
   ```bash
   git push origin feature/amazing-feature
   ```
5. **Open a Pull Request**

### Development Guidelines

- Follow PEP 8 style guide
- Add comments for complex logic
- Test thoroughly before submitting
- Update documentation for new features

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2025 Janagam Bharath

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

---

## 👤 Author

**Janagam Bharath**
- Portfolio: [bharath-portfolio-lvea.onrender.com](https://bharath-portfolio-lvea.onrender.com/)
- GitHub: [@janagambharath](https://github.com/janagambharath)
- LinkedIn: [Janagam Bharath](https://www.linkedin.com/in/janagam-bharath-9ab1b235b/)
- Email: janagambharath1107@gmail.com
- YouTube: [Bharath AI](https://www.youtube.com/@Bharath-ai)

---

## 🙏 Acknowledgments

- **OpenRouter** - For providing free LLM API access
- **Render** - For free hosting platform
- **Anthropic/Meta** - For amazing language models
- **Flask Community** - For excellent documentation
- **Font Awesome** - For beautiful icons

---

## 📞 Support

Need help? Here's how to get support:

1. **Check Documentation**: Read this README and other docs
2. **Search Issues**: Look for similar problems in GitHub Issues
3. **Create Issue**: Open a new issue with details
4. **Contact**: Email janagambharath1107@gmail.com

---

## ⭐ Show Your Support

If this project helped you, please give it a ⭐ star!

```
┌─────────────────────────────────────┐
│  ⭐ Star this repo to show support! │
│  🍴 Fork to customize for yourself! │
│  🐛 Report bugs to help improve!    │
│  💡 Suggest features you'd like!    │
└─────────────────────────────────────┘
```

---

## 📚 Additional Resources

- [OpenRouter Documentation](https://openrouter.ai/docs)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Render Deployment Guide](https://render.com/docs)
- [Python dotenv Tutorial](https://pypi.org/project/python-dotenv/)

---

<div align="center">

**Built with ❤️ by Janagam Bharath**

[Portfolio](https://bharath-portfolio-lvea.onrender.com/) • [GitHub](https://github.com/janagambharath) • [LinkedIn](https://www.linkedin.com/in/janagam-bharath-9ab1b235b/) • [YouTube](https://www.youtube.com/@Bharath-ai)

</div>
