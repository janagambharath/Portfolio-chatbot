import os
import logging
import json
from flask import Flask, render_template, request, jsonify

# ----------------------------
# Logging Configuration
# ----------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)
logger = logging.getLogger(__name__)

# ----------------------------
# Load Environment Variables
# ----------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.info("python-dotenv not installed, using system environment variables")

# ----------------------------
# Flask App Initialization
# ----------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key-2025')
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
app.config['ENV'] = os.getenv('FLASK_ENV', 'production')

# ----------------------------
# Environment Variables
# ----------------------------
API_KEY = os.getenv("OPENROUTER_API_KEY")
PORT = int(os.getenv("PORT", 10000))
HOST = os.getenv("HOST", "0.0.0.0")

# ----------------------------
# Initialize OpenRouter/OpenAI Client
# ----------------------------
client = None
try:
    if API_KEY:
        from openai import OpenAI
        client = OpenAI(api_key=API_KEY, base_url="https://openrouter.ai/api/v1")
        logger.info("✅ OpenRouter client initialized successfully")
    else:
        logger.warning("⚠️ No API key found - running in fallback mode")
except ImportError as e:
    logger.error(f"❌ OpenAI library not installed: {e}")
except Exception as e:
    logger.error(f"❌ Error initializing OpenAI client: {e}")

# ----------------------------
# Load Portfolio JSON
# ----------------------------
PORTFOLIO_FILE = "portfolio.json"
try:
    with open(PORTFOLIO_FILE, "r") as f:
        portfolio_data = json.load(f)
    logger.info("✅ Portfolio JSON loaded successfully")
except Exception as e:
    logger.error(f"❌ Could not load portfolio.json: {e}")
    portfolio_data = {}

# ----------------------------
# Routes
# ----------------------------
@app.route('/')
def home():
    return render_template('index.html', portfolio=portfolio_data)

@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.json.get('message', '')
    response_text = "AI service not available."

    if client:
        try:
            resp = client.chat.completions.create(
                model="deepsake",
                messages=[{"role": "user", "content": user_input}],
                temperature=0.7
            )
            response_text = resp.choices[0].message.content
        except Exception as e:
            logger.error(f"❌ Error in OpenRouter API call: {e}")
            response_text = "Error contacting AI service."

    return jsonify({"reply": response_text})

# ----------------------------
# Run Flask App
# ----------------------------
if __name__ == "__main__":
    logger.info(f"🚀 Starting Flask app on {HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=app.config['DEBUG'])
