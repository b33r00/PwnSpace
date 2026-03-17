import re
from datetime import datetime, timezone
from typing import Optional

import discord


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value[:90]


def safe_trim(value: Optional[str], max_len: int) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return value[:max_len]


def get_role_by_name(guild: discord.Guild, name: str) -> Optional[discord.Role]:
    return discord.utils.get(guild.roles, name=name)


def get_text_channel_by_name(guild: discord.Guild, name: str) -> Optional[discord.TextChannel]:
    return discord.utils.get(guild.text_channels, name=name)


async def get_or_create_category(guild: discord.Guild, name: str) -> discord.CategoryChannel:
    category = discord.utils.get(guild.categories, name=name)
    if category:
        return category
    return await guild.create_category(name)
