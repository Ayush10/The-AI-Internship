import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
DEFAULT_PROVIDER = os.environ.get("DEFAULT_PROVIDER", "gemini")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

ADMIN_NAME = os.environ.get("ADMIN_NAME", "Ayush Ojha")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "ayushozha@outlook.com")
MESSAGE_LIMIT = int(os.environ.get("MESSAGE_LIMIT", "5"))
