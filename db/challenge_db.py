import sqlite3
from typing import Optional

from utils.helpers import utcnow_iso


class ChallengeDB:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.init_db()

    def init_db(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            channel_id TEXT NOT NULL UNIQUE,
            role_id TEXT NOT NULL,
            creator_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL,
            closed_at TEXT,
            closed_by_id TEXT
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            challenge_id INTEGER NOT NULL,
            channel_id TEXT NOT NULL,
            claimant_id TEXT NOT NULL,
            claimed_by_display TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            note TEXT,
            thread_id TEXT,
            claimed_at TEXT NOT NULL,
            released_at TEXT,
            released_by_id TEXT,
            release_reason TEXT,
            transferred_from_claim_id INTEGER,
            github_issue_number INTEGER,
            github_issue_url TEXT,
            github_branch_name TEXT,
            FOREIGN KEY(challenge_id) REFERENCES challenges(id)
        )
        """)

        self.conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_challenges_guild_status_name
        ON challenges(guild_id, status, name)
        """)

        self.conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_claims_channel_status
        ON claims(channel_id, status)
        """)

        self.conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_claims_claimant_status
        ON claims(claimant_id, status)
        """)

        self.conn.commit()

    def insert_challenge(
        self,
        guild_id: int,
        name: str,
        category: str,
        difficulty: str,
        channel_id: int,
        role_id: int,
        creator_id: int
    ) -> int:
        cur = self.conn.execute("""
            INSERT INTO challenges (
                guild_id, name, category, difficulty,
                channel_id, role_id, creator_id, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?)
        """, (
            str(guild_id),
            name,
            category,
            difficulty,
            str(channel_id),
            str(role_id),
            str(creator_id),
            utcnow_iso()
        ))
        self.conn.commit()
        return cur.lastrowid

    def get_by_channel(self, channel_id: int) -> Optional[sqlite3.Row]:
        cur = self.conn.execute(
            "SELECT * FROM challenges WHERE channel_id = ?",
            (str(channel_id),)
        )
        return cur.fetchone()

    def get_by_id(self, challenge_id: int) -> Optional[sqlite3.Row]:
        cur = self.conn.execute(
            "SELECT * FROM challenges WHERE id = ?",
            (challenge_id,)
        )
        return cur.fetchone()

    def get_open_by_name(self, guild_id: int, name: str) -> Optional[sqlite3.Row]:
        cur = self.conn.execute("""
            SELECT * FROM challenges
            WHERE guild_id = ? AND name = ? AND status = 'open'
        """, (str(guild_id), name))
        return cur.fetchone()

    def close_challenge(self, channel_id: int, closed_by_id: int):
        self.conn.execute("""
            UPDATE challenges
            SET status = 'closed',
                closed_at = ?,
                closed_by_id = ?
            WHERE channel_id = ?
        """, (utcnow_iso(), str(closed_by_id), str(channel_id)))
        self.conn.commit()

    def get_active_claim_by_channel(self, channel_id: int) -> Optional[sqlite3.Row]:
        cur = self.conn.execute("""
            SELECT * FROM claims
            WHERE channel_id = ? AND status = 'active'
            ORDER BY id DESC
            LIMIT 1
        """, (str(channel_id),))
        return cur.fetchone()

    def get_active_claim_by_claimant(self, guild_id: int, claimant_id: int) -> list[sqlite3.Row]:
        cur = self.conn.execute("""
            SELECT c.*, ch.name AS challenge_name
            FROM claims c
            JOIN challenges ch ON ch.id = c.challenge_id
            WHERE c.guild_id = ? AND c.claimant_id = ? AND c.status = 'active'
            ORDER BY c.id DESC
        """, (str(guild_id), str(claimant_id)))
        return cur.fetchall()

    def create_claim(
        self,
        guild_id: int,
        challenge_id: int,
        channel_id: int,
        claimant_id: int,
        claimed_by_display: str,
        note: Optional[str],
        thread_id: Optional[int] = None,
        github_issue_number: Optional[int] = None,
        github_issue_url: Optional[str] = None,
        github_branch_name: Optional[str] = None,
        transferred_from_claim_id: Optional[int] = None
    ) -> int:
        cur = self.conn.execute("""
            INSERT INTO claims (
                guild_id, challenge_id, channel_id, claimant_id,
                claimed_by_display, status, note, thread_id, claimed_at,
                github_issue_number, github_issue_url, github_branch_name,
                transferred_from_claim_id
            ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(guild_id),
            challenge_id,
            str(channel_id),
            str(claimant_id),
            claimed_by_display,
            note,
            str(thread_id) if thread_id else None,
            utcnow_iso(),
            github_issue_number,
            github_issue_url,
            github_branch_name,
            transferred_from_claim_id
        ))
        self.conn.commit()
        return cur.lastrowid

    def get_claim_by_id(self, claim_id: int) -> Optional[sqlite3.Row]:
        cur = self.conn.execute("SELECT * FROM claims WHERE id = ?", (claim_id,))
        return cur.fetchone()

    def release_claim(self, claim_id: int, released_by_id: int, reason: Optional[str]):
        self.conn.execute("""
            UPDATE claims
            SET status = 'released',
                released_at = ?,
                released_by_id = ?,
                release_reason = ?
            WHERE id = ? AND status = 'active'
        """, (utcnow_iso(), str(released_by_id), reason, claim_id))
        self.conn.commit()

    def update_claim_thread_id(self, claim_id: int, thread_id: int):
        self.conn.execute("""
            UPDATE claims
            SET thread_id = ?
            WHERE id = ?
        """, (str(thread_id), claim_id))
        self.conn.commit()

    def attach_github_metadata(
        self,
        claim_id: int,
        github_issue_number: Optional[int] = None,
        github_issue_url: Optional[str] = None,
        github_branch_name: Optional[str] = None
    ):
        self.conn.execute("""
            UPDATE claims
            SET github_issue_number = COALESCE(?, github_issue_number),
                github_issue_url = COALESCE(?, github_issue_url),
                github_branch_name = COALESCE(?, github_branch_name)
            WHERE id = ?
        """, (github_issue_number, github_issue_url, github_branch_name, claim_id))
        self.conn.commit()
