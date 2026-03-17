import os


def _get_int(name: str, default: int | None = None) -> int | None:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _get_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")


# ========================
# CORE
# ========================

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = _get_int("GUILD_ID")

# ========================
# ACCESS / AUTH
# ========================

ACCESS_CHANNEL_NAME = os.getenv("ACCESS_CHANNEL_NAME", "access")
AUTH_CHANNEL_NAME = os.getenv("AUTH_CHANNEL_NAME", "auth")

VERIFIED_ROLE_NAME = os.getenv("VERIFIED_ROLE_NAME", "verified")
UNVERIFIED_ROLE_NAME = os.getenv("UNVERIFIED_ROLE_NAME", "unverified")

AUTH_PHRASE = os.getenv("AUTH_PHRASE", "let me in")

# ========================
# ROLES / STAFF
# ========================

ANNOUNCEMENT_ROLE_NAME = os.getenv("ANNOUNCEMENT_ROLE_NAME", "announcement")
STAFF_ROLE_NAME = os.getenv("STAFF_ROLE_NAME", "admin")

BOT_OWNER_ID = _get_int("BOT_OWNER_ID")

# ========================
# CHALLENGES
# ========================

CHALLENGE_CATEGORY_NAME = os.getenv("CHALLENGE_CATEGORY_NAME", "Challenges")
CHALLENGE_ARCHIVE_CATEGORY_NAME = os.getenv("CHALLENGE_ARCHIVE_CATEGORY_NAME", "Challenges-Archive")

LOG_CHANNEL_NAME = os.getenv("LOG_CHANNEL_NAME", "journalctl")
DB_PATH = os.getenv("DB_PATH", "challenges.db")

# ========================
# CLAIM
# ========================

CLAIM_THREAD_PREFIX = os.getenv("CLAIM_THREAD_PREFIX", "claim")
CLAIM_MAX_NOTE_LENGTH = _get_int("CLAIM_MAX_NOTE_LENGTH", 300)
ALLOW_ONLY_VERIFIED_FOR_CLAIM = _get_bool("ALLOW_ONLY_VERIFIED_FOR_CLAIM", True)

# ========================
# NEWS SYSTEM
# ========================

NEWS_CHANNEL_ID = _get_int("NEWS_CHANNEL_ID")
NEWS_POLL_MINUTES = _get_int("NEWS_POLL_MINUTES", 15)
NEWS_STATE_PATH = os.getenv("NEWS_STATE_PATH", "data/news_seen.json")

# ========================
# JOBS SYSTEM
# ========================

JOBS_CHANNEL_ID = _get_int("JOBS_CHANNEL_ID")
JOBS_POLL_MINUTES = _get_int("JOBS_POLL_MINUTES", 30)
JOBS_STATE_PATH = os.getenv("JOBS_STATE_PATH", "data/jobs_seen.json")
JOBS_SOURCES_PATH = os.getenv("JOBS_SOURCES_PATH", "data/job_sources.json")
