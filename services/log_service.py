import discord

import config
from utils.helpers import get_text_channel_by_name


async def log_action(guild: discord.Guild, message: str):
    log_channel = get_text_channel_by_name(guild, config.LOG_CHANNEL_NAME)
    if log_channel:
        await log_channel.send(message)
