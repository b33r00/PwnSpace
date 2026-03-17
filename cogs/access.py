import discord
from discord.ext import commands

import config
from services.log_service import log_action
from utils.helpers import get_role_by_name


class AccessCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.guild is None:
            return

        if not isinstance(message.author, discord.Member):
            return

        if not isinstance(message.channel, discord.TextChannel):
            return

        channel_name = message.channel.name.strip().lower()

        if channel_name == config.ACCESS_CHANNEL_NAME.lower():
            try:
                await message.author.ban(reason="Posted in access channel.")
                print(f"[BAN] {message.author}")
                await log_action(
                    message.guild,
                    f"[BAN] {message.author.mention} posted in #{config.ACCESS_CHANNEL_NAME}."
                )
            except discord.Forbidden:
                print("Missing permission to ban members.")
            return

        if channel_name == config.AUTH_CHANNEL_NAME.lower() and message.content.strip().lower() == config.AUTH_PHRASE.lower():
            verified_role = get_role_by_name(message.guild, config.VERIFIED_ROLE_NAME)
            unverified_role = get_role_by_name(message.guild, config.UNVERIFIED_ROLE_NAME)

            if verified_role is None:
                await message.channel.send(f"The `{config.VERIFIED_ROLE_NAME}` role was not found.")
            else:
                roles_to_add = []
                roles_to_remove = []

                if verified_role not in message.author.roles:
                    roles_to_add.append(verified_role)

                if unverified_role and unverified_role in message.author.roles:
                    roles_to_remove.append(unverified_role)

                if roles_to_add or roles_to_remove:
                    await message.author.edit(
                        roles=[r for r in message.author.roles if r not in roles_to_remove] + roles_to_add,
                        reason="Auth phrase matched"
                    )

                await message.channel.send(f"{message.author.mention} verified.")


async def setup(bot: commands.Bot):
    await bot.add_cog(AccessCog(bot))
