import discord
from discord import app_commands
from discord.ext import commands

import config
from db.challenge_db import ChallengeDB
from models.github_bridge import GitHubClaimBridge
from services.claim_service import ClaimService


class PwnSpaceBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True

        super().__init__(command_prefix="!", intents=intents)

        self.db = ChallengeDB(config.DB_PATH)
        self.github_bridge = GitHubClaimBridge()
        self.claim_service = ClaimService(self.db, self.github_bridge)

    async def setup_hook(self):
        extensions = [
            "cogs.access",
            "cogs.announcements",
            "cogs.challenge",
            "cogs.claim",
            "cogs.news",
        ]

        for extension in extensions:
       	 print(f"[LOADING] {extension}")
   	 await self.load_extension(extension)
         print(f"[OK] {extension}")

    print("[TREE COMMANDS BEFORE SYNC]")
    for cmd in self.tree.get_commands():
        print(f" - {cmd.name} ({type(cmd).__name__})")

    if config.GUILD_ID:
        guild_obj = discord.Object(id=int(config.GUILD_ID))

        self.tree.clear_commands(guild=guild_obj)
        self.tree.copy_global_to(guild=guild_obj)

        synced = await self.tree.sync(guild=guild_obj)
        print(f"Synced {len(synced)} guild commands to {config.GUILD_ID}")
        print("[SYNCED COMMANDS]")
        for cmd in synced:
            print(f" - {cmd.name} ({type(cmd).__name__})")
    else:
        synced = await self.tree.sync()
        print(f"Globally synced {len(synced)} commands")
        print("[SYNCED COMMANDS]")
        for cmd in synced:
            print(f" - {cmd.name} ({type(cmd).__name__})")
            

    async def on_ready(self):
        print(f"Logged in as: {self.user} (ID: {self.user.id})")

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        message = "An unexpected error occurred."

        if isinstance(error, app_commands.CheckFailure):
            message = str(error)
        elif isinstance(error, app_commands.CommandInvokeError):
            original = error.original
            if isinstance(original, PermissionError):
                message = str(original)
            elif isinstance(original, ValueError):
                message = str(original)
            elif isinstance(original, RuntimeError):
                message = str(original)
            else:
                print(f"[COMMAND ERROR] {repr(original)}")
                message = "Command execution failed."
        else:
            print(f"[APP COMMAND ERROR] {repr(error)}")

        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except Exception:
            pass


if config.TOKEN is None:
    raise RuntimeError("DISCORD_BOT_TOKEN is not set.")

bot = PwnSpaceBot()
bot.run(config.TOKEN)
