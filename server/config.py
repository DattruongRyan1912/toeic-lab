"""Runtime configuration. Values come from environment variables (and the repo-root .env)."""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

# The test-suite sets TOEIC_SKIP_DOTENV=1 so a developer's real .env (API keys) never leaks into tests.
if os.getenv("TOEIC_SKIP_DOTENV") != "1":
    load_dotenv(ROOT_DIR / ".env")


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _list(name: str, default: str) -> list:
    return [item.strip().rstrip("/") for item in os.getenv(name, default).split(",") if item.strip()]


APP_VERSION = "2.2.0"

# --- Database ---
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_SQLITE_PATH = DATA_DIR / "toeic_lab.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")

# --- Server ---
PORT = _int("PORT", 8000)
DEBUG = _bool("DEBUG", False)
# Browser origins allowed to call the API directly. The Next.js app calls through its
# server-side BFF proxy, so only the legacy UI / local tools need to be listed here.
CORS_ORIGINS = _list(
    "CORS_ORIGINS",
    "http://localhost:3005,http://127.0.0.1:3005,http://localhost:3000,http://127.0.0.1:3000,"
    "http://localhost:8000,http://127.0.0.1:8000",
)
WEB_APP_URL = os.getenv("WEB_APP_URL", "http://localhost:3005")
LEGACY_UI_ENABLED = _bool("LEGACY_UI_ENABLED", True)
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Ho_Chi_Minh")
DEFAULT_USER_ID = 1  # single-learner mode until real authentication exists

# --- Authentication ---
def _secret_key() -> str:
    """SECRET_KEY from the environment, else a random key persisted next to the database (never a shared default)."""
    value = os.getenv("SECRET_KEY", "").strip()
    if value:
        return value
    key_file = DATA_DIR / ".jwt_secret"
    if key_file.exists() and key_file.read_text().strip():
        return key_file.read_text().strip()
    value = secrets.token_urlsafe(48)
    key_file.write_text(value)
    key_file.chmod(0o600)
    return value


SECRET_KEY = _secret_key()
ACCESS_TOKEN_EXPIRE_DAYS = _int("ACCESS_TOKEN_EXPIRE_DAYS", 30)

# --- Learning rules ---
SRS_NEW_CARDS_PER_DAY = max(0, _int("SRS_NEW_CARDS_PER_DAY", 15))

# --- AI providers ("auto" = first configured of gemini, deepseek, openai) ---
AI_PROVIDER = os.getenv("AI_PROVIDER", "auto").strip().lower()
_raw_gemini_keys = os.getenv("GEMINI_API_KEYS", "") or os.getenv("GEMINI_API_KEY", "")
GEMINI_API_KEYS = [k.strip() for k in _raw_gemini_keys.split(",") if k.strip()]
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
# "deepseek-chat" was retired by DeepSeek; "deepseek-flash" is the current general model id.
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
AI_TIMEOUT_SECONDS = _float("AI_TIMEOUT_SECONDS", 45.0)
AI_HISTORY_TURNS = max(0, _int("AI_HISTORY_TURNS", 8))

# --- Notifications (optional) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
REMINDER_DISPATCH_ENABLED = _bool("REMINDER_DISPATCH_ENABLED", True)

# --- Rate limits (in-memory, per process): "<max requests>/<window seconds>" ---
RATE_LIMIT_LOGIN = os.getenv("RATE_LIMIT_LOGIN", "10/900")  # per username/email
RATE_LIMIT_REGISTER = os.getenv("RATE_LIMIT_REGISTER", "5/3600")  # per client IP
RATE_LIMIT_AI = os.getenv("RATE_LIMIT_AI", "30/600")  # per user (or IP for guests), LLM-backed endpoints
# Reverse proxies in front of the web app that append the client IP to X-Forwarded-For (Caddy/nginx = 1).
# 0 = never read the header. Only honoured for requests reaching the API from an internal address.
TRUSTED_PROXY_HOPS = max(0, _int("TRUSTED_PROXY_HOPS", 1))

# --- AI allowance (admins and accounts an admin marked unlimited are exempt) ---
AI_DAILY_QUOTA = max(0, _int("AI_DAILY_QUOTA", 40))  # successful AI requests per learner per local day
AI_GUEST_DAILY_QUOTA = max(0, _int("AI_GUEST_DAILY_QUOTA", 10))  # per guest IP, rolling 24 hours
AI_KEY_COOLDOWN_SECONDS = max(0, _int("AI_KEY_COOLDOWN_SECONDS", 60))  # skip a key after a 429/403 for this long
AI_USAGE_RETENTION_DAYS = max(7, _int("AI_USAGE_RETENTION_DAYS", 90))
