import discord
from discord import app_commands
from discord.ext import commands

import config
from services.log_service import log_action
from utils.checks import admin_only_check
from utils.helpers import get_role_by_name


class AnnouncementsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="send", description="Send an embed announcement")
    @app_commands.describe(
        name="Embed title",
        body="Embed message",
        ping="Ping the announcement role?"
    )
    @app_commands.default_permissions(administrator=True)
    @admin_only_check()
    async def send_embed(
        self,
        interaction: discord.Interaction,
        name: str,
        body: str,
        ping: bool = False
    ):
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used inside a server.", ephemeral=True)
            return

        embed = discord.Embed(
            title=name,
            description=body,
            color=0x000000
        )

        content = None
        if ping:
            role = get_role_by_name(interaction.guild, config.ANNOUNCEMENT_ROLE_NAME)
            if role:
                content = role.mention

        await interaction.response.send_message(
            content=content,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(
                roles=True,
                users=False,
                everyone=False
            )
        )

        await log_action(
            interaction.guild,
            f"[SEND] {interaction.user.mention} sent an announcement embed in {interaction.channel.mention if interaction.channel else 'unknown'}"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(AnnouncementsCog(bot))
