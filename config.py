import os

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

ACCESS_CHANNEL_NAME = os.getenv("ACCESS_CHANNEL_NAME", "access")
AUTH_CHANNEL_NAME = os.getenv("AUTH_CHANNEL_NAME", "auth")
VERIFIED_ROLE_NAME = os.getenv("VERIFIED_ROLE_NAME", "verified")
UNVERIFIED_ROLE_NAME = os.getenv("UNVERIFIED_ROLE_NAME", "unverified")
AUTH_PHRASE = os.getenv("AUTH_PHRASE", "let me in")

ANNOUNCEMENT_ROLE_NAME = os.getenv("ANNOUNCEMENT_ROLE_NAME", "announcement")

STAFF_ROLE_NAME = os.getenv("STAFF_ROLE_NAME", "admin")
BOT_OWNER_ID = os.getenv("BOT_OWNER_ID")

CHALLENGE_CATEGORY_NAME = os.getenv("CHALLENGE_CATEGORY_NAME", "Challenges")
CHALLENGE_ARCHIVE_CATEGORY_NAME = os.getenv("CHALLENGE_ARCHIVE_CATEGORY_NAME", "Challenges-Archive")
LOG_CHANNEL_NAME = os.getenv("LOG_CHANNEL_NAME", "journalctl")
DB_PATH = os.getenv("DB_PATH", "challenges.db")

CLAIM_THREAD_PREFIX = os.getenv("CLAIM_THREAD_PREFIX", "claim")
CLAIM_MAX_NOTE_LENGTH = int(os.getenv("CLAIM_MAX_NOTE_LENGTH", "300"))
ALLOW_ONLY_VERIFIED_FOR_CLAIM = os.getenv("ALLOW_ONLY_VERIFIED_FOR_CLAIM", "true").lower() == "true"
