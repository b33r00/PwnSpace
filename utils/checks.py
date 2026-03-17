from typing import Optional

import discord
from discord import app_commands

import config
from utils.helpers import get_role_by_name


def parse_bot_owner_id() -> Optional[int]:
    if not config.BOT_OWNER_ID:
        return None
    try:
        return int(config.BOT_OWNER_ID)
    except ValueError:
        return None


def is_admin_member(member: discord.Member) -> bool:
    if member.guild.owner_id == member.id:
        return True

    owner_override = parse_bot_owner_id()
    if owner_override is not None and member.id == owner_override:
        return True

    if member.guild_permissions.administrator:
        return True

    staff_role = get_role_by_name(member.guild, config.STAFF_ROLE_NAME)
    if staff_role and staff_role in member.roles:
        return True

    return False


def is_verified_member(member: discord.Member) -> bool:
    if not config.ALLOW_ONLY_VERIFIED_FOR_CLAIM:
        return True

    verified_role = get_role_by_name(member.guild, config.VERIFIED_ROLE_NAME)
    if verified_role is None:
        return True

    return verified_role in member.roles


def admin_only_check():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            raise app_commands.CheckFailure("This command can only be used inside a server.")
        if not is_admin_member(interaction.user):
            raise app_commands.CheckFailure("You need admin permissions to use this command.")
        return True
    return app_commands.check(predicate)


def verified_only_check():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            raise app_commands.CheckFailure("This command can only be used inside a server.")
        if not is_verified_member(interaction.user):
            raise app_commands.CheckFailure("You must be verified to use this command.")
        return True
    return app_commands.check(predicate)


def challenge_channel_only_check():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None or interaction.channel is None:
            raise app_commands.CheckFailure("This command can only be used inside a challenge channel.")
        if not isinstance(interaction.channel, discord.TextChannel):
            raise app_commands.CheckFailure("This command can only be used inside a text channel.")

        db = getattr(interaction.client, "db", None)
        if db is None:
            raise app_commands.CheckFailure("Database is not initialized.")

        row = db.get_by_channel(interaction.channel.id)
        if not row:
            raise app_commands.CheckFailure("This channel is not registered as a challenge channel.")
        return True
    return app_commands.check(predicate)
