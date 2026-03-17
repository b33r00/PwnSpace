from typing import Optional

import discord
import sqlite3

import config
from models.github_bridge import ClaimGitSyncPayload
from utils.helpers import safe_trim, slugify
from utils.checks import is_admin_member


async def maybe_create_claim_thread(
    channel: discord.TextChannel,
    claimant: discord.Member,
    challenge_name: str
) -> Optional[discord.Thread]:
    base_name = slugify(f"{config.CLAIM_THREAD_PREFIX}-{claimant.display_name}-{challenge_name}")[:95]
    try:
        thread = await channel.create_thread(
            name=base_name,
            type=discord.ChannelType.public_thread,
            auto_archive_duration=1440,
            reason=f"Claim thread for {claimant}"
        )
        return thread
    except (discord.Forbidden, discord.HTTPException):
        return None


async def maybe_archive_claim_thread(
    guild: discord.Guild,
    thread_id: Optional[str]
):
    if not thread_id:
        return

    try:
        thread = guild.get_thread(int(thread_id))
        if thread is None:
            channel = await guild.fetch_channel(int(thread_id))
            if isinstance(channel, discord.Thread):
                thread = channel
        if isinstance(thread, discord.Thread):
            await thread.edit(archived=True, locked=True, reason="Claim released")
    except Exception:
        return


class ClaimService:
    def __init__(self, database, github_adapter):
        self.db = database
        self.github = github_adapter

    async def create_claim(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        claimant: discord.Member,
        note: Optional[str]
    ) -> sqlite3.Row:
        challenge = self.db.get_by_channel(channel.id)
        if not challenge:
            raise ValueError("This channel is not a challenge channel.")

        if challenge["status"] != "open":
            raise ValueError("You cannot claim a closed challenge.")

        existing = self.db.get_active_claim_by_channel(channel.id)
        if existing:
            raise ValueError("This challenge already has an active claim.")

        note = safe_trim(note, config.CLAIM_MAX_NOTE_LENGTH)
        thread = await maybe_create_claim_thread(channel, claimant, challenge["name"])

        claim_id = self.db.create_claim(
            guild_id=guild.id,
            challenge_id=int(challenge["id"]),
            channel_id=channel.id,
            claimant_id=claimant.id,
            claimed_by_display=str(claimant),
            note=note,
            thread_id=thread.id if thread else None
        )

        claim = self.db.get_claim_by_id(claim_id)
        if claim is None:
            raise RuntimeError("Failed to save the claim.")

        payload = ClaimGitSyncPayload(
            guild_id=guild.id,
            challenge_id=int(challenge["id"]),
            challenge_name=challenge["name"],
            channel_id=channel.id,
            claimant_id=claimant.id,
            claimant_name=str(claimant),
            claim_note=note,
            claim_thread_id=thread.id if thread else None,
            event="claim_created"
        )
        await self.github.on_claim_created(payload)

        return claim

    async def release_claim(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        actor: discord.Member,
        reason: Optional[str] = None,
        force: bool = False
    ) -> sqlite3.Row:
        challenge = self.db.get_by_channel(channel.id)
        if not challenge:
            raise ValueError("This channel is not a challenge channel.")

        existing = self.db.get_active_claim_by_channel(channel.id)
        if not existing:
            raise ValueError("There is no active claim in this channel.")

        if not force and str(actor.id) != existing["claimant_id"]:
            raise PermissionError("Only the current claimant or an admin can release this claim.")

        self.db.release_claim(
            claim_id=int(existing["id"]),
            released_by_id=actor.id,
            reason=safe_trim(reason, config.CLAIM_MAX_NOTE_LENGTH)
        )

        await maybe_archive_claim_thread(guild, existing["thread_id"])

        updated = self.db.get_claim_by_id(int(existing["id"]))
        if updated is None:
            raise RuntimeError("Claim record could not be found after release.")

        payload = ClaimGitSyncPayload(
            guild_id=guild.id,
            challenge_id=int(challenge["id"]),
            challenge_name=challenge["name"],
            channel_id=channel.id,
            claimant_id=int(existing["claimant_id"]),
            claimant_name=existing["claimed_by_display"] or existing["claimant_id"],
            claim_note=existing["note"],
            claim_thread_id=int(existing["thread_id"]) if existing["thread_id"] else None,
            event="claim_released",
            github_issue_number=existing["github_issue_number"],
            github_issue_url=existing["github_issue_url"],
            github_branch_name=existing["github_branch_name"]
        )
        await self.github.on_claim_released(payload)

        return updated

    async def transfer_claim(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        actor: discord.Member,
        new_claimant: discord.Member,
        note: Optional[str] = None
    ) -> sqlite3.Row:
        challenge = self.db.get_by_channel(channel.id)
        if not challenge:
            raise ValueError("This channel is not a challenge channel.")

        existing = self.db.get_active_claim_by_channel(channel.id)
        if not existing:
            raise ValueError("There is no active claim in this channel.")

        if not is_admin_member(actor):
            raise PermissionError("Only an admin can transfer a claim.")

        clean_note = safe_trim(note, config.CLAIM_MAX_NOTE_LENGTH)

        self.db.release_claim(
            claim_id=int(existing["id"]),
            released_by_id=actor.id,
            reason=f"Transferred to {new_claimant} | {clean_note or 'no note'}"
        )

        await maybe_archive_claim_thread(guild, existing["thread_id"])

        new_thread = await maybe_create_claim_thread(channel, new_claimant, challenge["name"])

        new_claim_id = self.db.create_claim(
            guild_id=guild.id,
            challenge_id=int(challenge["id"]),
            channel_id=channel.id,
            claimant_id=new_claimant.id,
            claimed_by_display=str(new_claimant),
            note=clean_note,
            thread_id=new_thread.id if new_thread else None,
            github_issue_number=existing["github_issue_number"],
            github_issue_url=existing["github_issue_url"],
            github_branch_name=existing["github_branch_name"],
            transferred_from_claim_id=int(existing["id"])
        )

        new_claim = self.db.get_claim_by_id(new_claim_id)
        if new_claim is None:
            raise RuntimeError("The new claim could not be found after transfer.")

        payload = ClaimGitSyncPayload(
            guild_id=guild.id,
            challenge_id=int(challenge["id"]),
            challenge_name=challenge["name"],
            channel_id=channel.id,
            claimant_id=new_claimant.id,
            claimant_name=str(new_claimant),
            claim_note=clean_note,
            claim_thread_id=new_thread.id if new_thread else None,
            event="claim_transferred",
            old_claimant_id=int(existing["claimant_id"]),
            old_claimant_name=existing["claimed_by_display"] or existing["claimant_id"],
            github_issue_number=existing["github_issue_number"],
            github_issue_url=existing["github_issue_url"],
            github_branch_name=existing["github_branch_name"]
        )
        await self.github.on_claim_transferred(payload)

        return new_claim
