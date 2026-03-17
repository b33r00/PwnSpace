from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

import config
from services.log_service import log_action
from utils.checks import admin_only_check, challenge_channel_only_check
from utils.helpers import get_or_create_category, get_role_by_name, slugify


class ChallengeCog(commands.GroupCog, group_name="challenge", group_description="Challenge workflow commands"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="create", description="Create a dedicated challenge channel and role")
    @app_commands.describe(
        name="Challenge name, e.g. web-sqli",
        category="Category, e.g. web/pwn/rev/crypto",
        difficulty="Difficulty, e.g. easy/medium/hard"
    )
    @app_commands.default_permissions(administrator=True)
    @admin_only_check()
    async def create(self, interaction: discord.Interaction, name: str, category: str, difficulty: str):
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used inside a server.", ephemeral=True)
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Invalid user context.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        challenge_name = slugify(name)
        category_slug = slugify(category)
        difficulty_slug = slugify(difficulty)

        existing = self.bot.db.get_open_by_name(interaction.guild.id, challenge_name)
        if existing:
            await interaction.followup.send(
                f"An open challenge already exists: <#{existing['channel_id']}>",
                ephemeral=True
            )
            return

        challenge_category = await get_or_create_category(interaction.guild, config.CHALLENGE_CATEGORY_NAME)

        role_name = f"chall-{challenge_name}"
        challenge_role = get_role_by_name(interaction.guild, role_name)
        if challenge_role is None:
            challenge_role = await interaction.guild.create_role(
                name=role_name,
                reason=f"Challenge role created by {interaction.user}"
            )

        me = interaction.guild.me
        staff_role = get_role_by_name(interaction.guild, config.STAFF_ROLE_NAME)

        overwrites: dict[Any, discord.PermissionOverwrite] = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            challenge_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
                create_public_threads=True,
                send_messages_in_threads=True
            )
        }

        if me:
            overwrites[me] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_permissions=True,
                manage_threads=True,
                read_message_history=True
            )

        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_messages=True,
                manage_threads=True,
                read_message_history=True
            )

        channel = await interaction.guild.create_text_channel(
            name=challenge_name,
            category=challenge_category,
            overwrites=overwrites,
            topic=f"Challenge: {challenge_name} | Category: {category_slug} | Difficulty: {difficulty_slug}"
        )

        await interaction.user.add_roles(challenge_role, reason="Challenge creator auto-added")

        challenge_id = self.bot.db.insert_challenge(
            guild_id=interaction.guild.id,
            name=challenge_name,
            category=category_slug,
            difficulty=difficulty_slug,
            channel_id=channel.id,
            role_id=challenge_role.id,
            creator_id=interaction.user.id
        )

        embed = discord.Embed(title="Challenge created", color=0x000000)
        embed.add_field(name="Name", value=challenge_name, inline=True)
        embed.add_field(name="Category", value=category_slug, inline=True)
        embed.add_field(name="Difficulty", value=difficulty_slug, inline=True)
        embed.add_field(name="Channel", value=channel.mention, inline=False)
        embed.add_field(name="Role", value=challenge_role.mention, inline=False)
        embed.add_field(name="DB ID", value=str(challenge_id), inline=False)
        embed.set_footer(text=f"Created by {interaction.user}")

        await channel.send(
            f"{challenge_role.mention} challenge workspace is live.\n"
            f"Creator: {interaction.user.mention}\n"
            f"Claim: use `/claim take` if someone starts working on it."
        )
        await channel.send(embed=embed)

        await log_action(
            interaction.guild,
            f"[CREATE] {interaction.user.mention} created {channel.mention} | role: {challenge_role.mention} | challenge_id={challenge_id}"
        )

        await interaction.followup.send(f"Challenge created: {channel.mention}", ephemeral=True)

    @app_commands.command(name="close", description="Close the current challenge channel")
    @app_commands.default_permissions(administrator=True)
    @admin_only_check()
    @challenge_channel_only_check()
    async def close(self, interaction: discord.Interaction):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message("This command can only be used inside a challenge channel.", ephemeral=True)
            return

        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("This command can only be used inside a text channel.", ephemeral=True)
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Invalid user context.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        row = self.bot.db.get_by_channel(interaction.channel.id)
        if not row:
            await interaction.followup.send("This channel is not registered as a challenge channel.", ephemeral=True)
            return

        active_claim = self.bot.db.get_active_claim_by_channel(interaction.channel.id)
        if active_claim:
            try:
                await self.bot.claim_service.release_claim(
                    guild=interaction.guild,
                    channel=interaction.channel,
                    actor=interaction.user,
                    reason="Challenge closed by admin",
                    force=True
                )
            except Exception:
                pass

        role = interaction.guild.get_role(int(row["role_id"]))
        archive_category = await get_or_create_category(interaction.guild, config.CHALLENGE_ARCHIVE_CATEGORY_NAME)

        if role:
            overwrite = interaction.channel.overwrites_for(role)
            overwrite.send_messages = False
            overwrite.view_channel = True
            overwrite.send_messages_in_threads = False
            await interaction.channel.set_permissions(role, overwrite=overwrite)

        self.bot.db.close_challenge(interaction.channel.id, interaction.user.id)

        new_name = interaction.channel.name
        if not new_name.startswith("closed-"):
            new_name = f"closed-{new_name}"

        await interaction.channel.edit(name=new_name, category=archive_category)
        await interaction.channel.send("Challenge closed. This channel is now archived / read-only.")

        await log_action(
            interaction.guild,
            f"[CLOSE] {interaction.user.mention} closed {interaction.channel.mention}"
        )

        await interaction.followup.send("Challenge closed.", ephemeral=True)

    @app_commands.command(name="adduser", description="Add a user to the current challenge")
    @app_commands.describe(member="Member to add")
    @app_commands.default_permissions(administrator=True)
    @admin_only_check()
    @challenge_channel_only_check()
    async def adduser(self, interaction: discord.Interaction, member: discord.Member):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message("This command can only be used inside a challenge channel.", ephemeral=True)
            return

        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("This command can only be used inside a text channel.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        row = self.bot.db.get_by_channel(interaction.channel.id)
        if not row:
            await interaction.followup.send("This is not a challenge channel.", ephemeral=True)
            return

        role = interaction.guild.get_role(int(row["role_id"]))
        if role is None:
            await interaction.followup.send("Challenge role not found.", ephemeral=True)
            return

        await member.add_roles(role, reason=f"Added to challenge by {interaction.user}")
        await interaction.followup.send(f"{member.mention} added.", ephemeral=True)

        await log_action(
            interaction.guild,
            f"[ADDUSER] {interaction.user.mention} added {member.mention} to <#{row['channel_id']}>"
        )

    @app_commands.command(name="removeuser", description="Remove a user from the current challenge")
    @app_commands.describe(member="Member to remove")
    @app_commands.default_permissions(administrator=True)
    @admin_only_check()
    @challenge_channel_only_check()
    async def removeuser(self, interaction: discord.Interaction, member: discord.Member):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message("This command can only be used inside a challenge channel.", ephemeral=True)
            return

        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("This command can only be used inside a text channel.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        row = self.bot.db.get_by_channel(interaction.channel.id)
        if not row:
            await interaction.followup.send("This is not a challenge channel.", ephemeral=True)
            return

        role = interaction.guild.get_role(int(row["role_id"]))
        if role is None:
            await interaction.followup.send("Challenge role not found.", ephemeral=True)
            return

        await member.remove_roles(role, reason=f"Removed from challenge by {interaction.user}")
        await interaction.followup.send(f"{member.mention} removed.", ephemeral=True)

        await log_action(
            interaction.guild,
            f"[REMOVEUSER] {interaction.user.mention} removed {member.mention} from <#{row['channel_id']}>"
        )

    @app_commands.command(name="info", description="Show metadata for the current challenge")
    @challenge_channel_only_check()
    async def info(self, interaction: discord.Interaction):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message("This command can only be used inside a challenge channel.", ephemeral=True)
            return

        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("This command can only be used inside a text channel.", ephemeral=True)
            return

        row = self.bot.db.get_by_channel(interaction.channel.id)
        if not row:
            await interaction.response.send_message("This is not a challenge channel.", ephemeral=True)
            return

        role = interaction.guild.get_role(int(row["role_id"]))
        creator = interaction.guild.get_member(int(row["creator_id"]))
        active_claim = self.bot.db.get_active_claim_by_channel(interaction.channel.id)

        embed = discord.Embed(title=f"Challenge info: {row['name']}", color=0x000000)
        embed.add_field(name="Category", value=row["category"], inline=True)
        embed.add_field(name="Difficulty", value=row["difficulty"], inline=True)
        embed.add_field(name="Status", value=row["status"], inline=True)
        embed.add_field(name="Role", value=role.mention if role else row["role_id"], inline=False)
        embed.add_field(name="Creator", value=creator.mention if creator else row["creator_id"], inline=False)
        embed.add_field(name="Created", value=row["created_at"], inline=False)

        if active_claim:
            claimer = interaction.guild.get_member(int(active_claim["claimant_id"]))
            embed.add_field(
                name="Active claim",
                value=claimer.mention if claimer else active_claim["claimant_id"],
                inline=False
            )
            embed.add_field(name="Claimed at", value=active_claim["claimed_at"], inline=False)

            if active_claim["note"]:
                embed.add_field(name="Claim note", value=active_claim["note"], inline=False)

            if active_claim["thread_id"]:
                embed.add_field(name="Claim thread", value=f"<#{active_claim['thread_id']}>", inline=False)
        else:
            embed.add_field(name="Active claim", value="none", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ChallengeCog(bot))
