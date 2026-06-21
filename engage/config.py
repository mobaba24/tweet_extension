"""Settings for the engagement bots. Secrets come from the environment / .env
(never commit .env). See .env.example for the keys."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"


def _load_dotenv():
    """Tiny .env loader (no hard dependency on python-dotenv)."""
    p = ROOT / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

# ---- LLM (shared reply engine) ----------------------------------------------
# Default to Opus; switch to claude-sonnet-4-6 / claude-haiku-4-5 for high volume.
MODEL = os.environ.get("ENGAGE_MODEL", "claude-opus-4-8")
MAX_REPLY_TOKENS = int(os.environ.get("MAX_REPLY_TOKENS", "400"))
PERSONA = os.environ.get(
    "ENGAGE_PERSONA",
    "a friendly, respectful person who leaves short, genuine, on-topic comments",
)

# ---- Relevance gate ---------------------------------------------------------
# Only engage with content matching these (comma-separated in .env). Empty = all.
NICHE_KEYWORDS = [k.strip().lower() for k in os.environ.get("NICHE_KEYWORDS", "").split(",") if k.strip()]

# ---- Telegram --------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_REPLY_LANG = os.environ.get("TG_REPLY_LANG", "Persian")   # default caption language
TG_MIN_SECONDS_PER_USER = float(os.environ.get("TG_MIN_SECONDS_PER_USER", "8"))
TG_ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

# ---- X engagement (Phase 3) -------------------------------------------------
X_API_KEY = os.environ.get("X_API_KEY", "")
X_API_SECRET = os.environ.get("X_API_SECRET", "")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "")
X_ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET", "")
X_AUTONOMOUS = os.environ.get("X_AUTONOMOUS", "false").lower() == "true"  # default: review-first
MAX_REPLIES_PER_HOUR = int(os.environ.get("MAX_REPLIES_PER_HOUR", "8"))
MAX_REPLIES_PER_DAY = int(os.environ.get("MAX_REPLIES_PER_DAY", "40"))
