from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import config
from services.log_service import log_action
from utils.checks import (
    admin_only_check,
    challenge_channel_only_check,
    is_admin_member,
    is_verified_member,
    verified_only_check,
)


class ClaimCog(commands.GroupCog, group_name="claim", group_description="Challenge claim commands"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="take", description="Claim the current challenge for yourself")
    @app_commands.describe(note="Optional short note about your approach")
    @verified_only_check()
    @challenge_channel_only_check()
    async def take(self, interaction: discord.Interaction, note: Optional[str] = None):
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

        try:
            claim = await self.bot.claim_service.create_claim(
                guild=interaction.guild,
                channel=interaction.channel,
                claimant=interaction.user,
                note=note
            )
        except Exception as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return

        channel_row = self.bot.db.get_by_channel(interaction.channel.id)
        role = interaction.guild.get_role(int(channel_row["role_id"])) if channel_row else None

        public_msg = f"Claim active: {interaction.user.mention} is now working on this challenge."
        if role:
            public_msg = f"{role.mention} {public_msg}"

        await interaction.channel.send(public_msg)

        if claim["thread_id"]:
            await interaction.channel.send(f"Claim thread created: <#{claim['thread_id']}>")

        await log_action(
            interaction.guild,
            f"[CLAIM] {interaction.user.mention} claimed {interaction.channel.mention} | claim_id={claim['id']}"
        )

        await interaction.followup.send("Claim recorded.", ephemeral=True)

    @app_commands.command(name="release", description="Release your current claim")
    @app_commands.describe(reason="Optional reason")
    @verified_only_check()
    @challenge_channel_only_check()
    async def release(self, interaction: discord.Interaction, reason: Optional[str] = None):
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

        try:
            existing = self.bot.db.get_active_claim_by_channel(interaction.channel.id)
            if not existing:
                await interaction.followup.send("There is no active claim in this channel.", ephemeral=True)
                return

            claim = await self.bot.claim_service.release_claim(
                guild=interaction.guild,
                channel=interaction.channel,
                actor=interaction.user,
                reason=reason,
                force=is_admin_member(interaction.user)
            )
        except PermissionError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return

        await interaction.channel.send(f"Claim released by {interaction.user.mention}.")

        await log_action(
            interaction.guild,
            f"[CLAIM-RELEASE] {interaction.user.mention} released the claim in {interaction.channel.mention} | claim_id={claim['id']}"
        )

        await interaction.followup.send("Claim released.", ephemeral=True)

    @app_commands.command(name="status", description="Show current claim status for this challenge")
    @challenge_channel_only_check()
    async def status(self, interaction: discord.Interaction):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message("This command can only be used inside a challenge channel.", ephemeral=True)
            return

        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("This command can only be used inside a text channel.", ephemeral=True)
            return

        active_claim = self.bot.db.get_active_claim_by_channel(interaction.channel.id)

        embed = discord.Embed(title=f"Claim status: #{interaction.channel.name}", color=0x000000)
        if active_claim:
            claimer = interaction.guild.get_member(int(active_claim["claimant_id"]))
            embed.add_field(
                name="Claimant",
                value=claimer.mention if claimer else active_claim["claimant_id"],
                inline=False
            )
            embed.add_field(name="Claimed at", value=active_claim["claimed_at"], inline=False)
            embed.add_field(name="Note", value=active_claim["note"] or "none", inline=False)
            embed.add_field(
                name="Thread",
                value=f"<#{active_claim['thread_id']}>" if active_claim["thread_id"] else "none",
                inline=False
            )
            embed.add_field(
                name="GitHub issue",
                value=active_claim["github_issue_url"] or "none",
                inline=False
            )
            embed.add_field(
                name="GitHub branch",
                value=active_claim["github_branch_name"] or "none",
                inline=False
            )
        else:
            embed.description = "There is no active claim."

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="mine", description="List your active claims")
    @verified_only_check()
    async def mine(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used inside a server.", ephemeral=True)
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Invalid user context.", ephemeral=True)
            return

        rows = self.bot.db.get_active_claim_by_claimant(interaction.guild.id, interaction.user.id)
        if not rows:
            await interaction.response.send_message("You have no active claims.", ephemeral=True)
            return

        embed = discord.Embed(title=f"Active claims for {interaction.user}", color=0x000000)
        for row in rows[:20]:
            embed.add_field(
                name=row["challenge_name"],
                value=f"Channel: <#{row['channel_id']}>\nClaimed at: {row['claimed_at']}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="force-release", description="Admin: forcibly release the current claim")
    @app_commands.describe(reason="Reason for force release")
    @app_commands.default_permissions(administrator=True)
    @admin_only_check()
    @challenge_channel_only_check()
    async def force_release(self, interaction: discord.Interaction, reason: Optional[str] = None):
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

        try:
            claim = await self.bot.claim_service.release_claim(
                guild=interaction.guild,
                channel=interaction.channel,
                actor=interaction.user,
                reason=reason or "Force released by admin",
                force=True
            )
        except Exception as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return

        await interaction.channel.send(f"Claim forcibly released by admin {interaction.user.mention}.")

        await log_action(
            interaction.guild,
            f"[CLAIM-FORCE-RELEASE] {interaction.user.mention} force-released {interaction.channel.mention} | claim_id={claim['id']}"
        )

        await interaction.followup.send("Claim force-released.", ephemeral=True)

    @app_commands.command(name="transfer", description="Admin: transfer active claim to another member")
    @app_commands.describe(
        member="New claimant",
        note="Optional transfer note"
    )
    @app_commands.default_permissions(administrator=True)
    @admin_only_check()
    @challenge_channel_only_check()
    async def transfer(self, interaction: discord.Interaction, member: discord.Member, note: Optional[str] = None):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message("This command can only be used inside a challenge channel.", ephemeral=True)
            return

        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("This command can only be used inside a text channel.", ephemeral=True)
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Invalid user context.", ephemeral=True)
            return

        if config.ALLOW_ONLY_VERIFIED_FOR_CLAIM and not is_verified_member(member):
            await interaction.response.send_message("The target member is not verified.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            new_claim = await self.bot.claim_service.transfer_claim(
                guild=interaction.guild,
                channel=interaction.channel,
                actor=interaction.user,
                new_claimant=member,
                note=note
            )
        except Exception as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return

        await interaction.channel.send(
            f"Claim transferred by admin {interaction.user.mention} to {member.mention}."
        )

        if new_claim["thread_id"]:
            await interaction.channel.send(f"New claim thread: <#{new_claim['thread_id']}>")

        await log_action(
            interaction.guild,
            f"[CLAIM-TRANSFER] {interaction.user.mention} transferred the claim to {member.mention} in {interaction.channel.mention} | new_claim_id={new_claim['id']}"
        )

        await interaction.followup.send("Claim transferred.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ClaimCog(bot))
