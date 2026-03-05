import os
from dotenv import load_dotenv

load_dotenv()

# Google AI
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")

# Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_PROJECT_REF = os.environ.get("SUPABASE_PROJECT_REF", "")
SUPABASE_ACCESS_TOKEN = os.environ.get("SUPABASE_ACCESS_TOKEN", "")
SUPABASE_MCP_URL = os.environ.get("SUPABASE_MCP_URL", "https://mcp.supabase.com/mcp")

# Returns A2A
RETURNS_A2A_URL = os.environ.get("RETURNS_A2A_URL", "http://localhost:8001")

# App
BASE_PATH = os.environ.get("BASE_PATH", "")
