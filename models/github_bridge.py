from dataclasses import dataclass
from typing import Optional


@dataclass
class ClaimGitSyncPayload:
    guild_id: int
    challenge_id: int
    challenge_name: str
    channel_id: int
    claimant_id: int
    claimant_name: str
    claim_note: Optional[str]
    claim_thread_id: Optional[int]
    event: str
    old_claimant_id: Optional[int] = None
    old_claimant_name: Optional[str] = None
    github_issue_number: Optional[int] = None
    github_issue_url: Optional[str] = None
    github_branch_name: Optional[str] = None


class GitHubClaimBridge:
    async def on_claim_created(self, payload: ClaimGitSyncPayload):
        return None

    async def on_claim_released(self, payload: ClaimGitSyncPayload):
        return None

    async def on_claim_transferred(self, payload: ClaimGitSyncPayload):
        return None
