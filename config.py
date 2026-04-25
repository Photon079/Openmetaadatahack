import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def _api_url(raw: str) -> str:
    """Ensure the URL has an /api/v1 suffix."""
    if not raw.endswith("/api/v1"):
        raw = raw.rstrip("/") + "/api/v1"
    return raw


# ── OpenMetadata ──────────────────────────────────────────────────────────────
OM_BASE_URL = _api_url(os.getenv("OM_BASE_URL", "http://localhost:8585"))
OM_HOST = os.getenv("OM_BASE_URL", "http://localhost:8585").rstrip("/")
OM_USERNAME = os.getenv("OM_USERNAME", "admin")
OM_PASSWORD = os.getenv("OM_PASSWORD", "admin")

# ── Google Sheets ─────────────────────────────────────────────────────────────
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "./gcp-sa.json")
SHEET_ID = os.getenv("SHEET_ID", "")

# ── Slack ─────────────────────────────────────────────────────────────────────
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "#data-quality")

# ── AI Summarization ──────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ── Jira (optional) ───────────────────────────────────────────────────────────
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
JIRA_TOKEN = os.getenv("JIRA_TOKEN", "")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "DQ")

