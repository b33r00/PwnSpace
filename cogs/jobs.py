import discord
from discord.ext import commands, tasks

import config
from services.jobs_service import JobsService


def trim_text(text: str, max_len: int = 350) -> str:
    text = (text or "").strip()
    if not text:
        return "No description available."
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


class JobsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.service = JobsService(
            sources_path=config.JOBS_SOURCES_PATH,
            state_path=config.JOBS_STATE_PATH,
        )
        self.started = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self.started:
            return

        self.started = True
        print("[JOBS] ready")

        if not self.loop.is_running():
            self.loop.start()
            print("[JOBS] loop started")

    @tasks.loop(minutes=1)
    async def loop(self):
        print("[JOBS] tick")

        if not config.JOBS_CHANNEL_ID:
            print("[JOBS] JOBS_CHANNEL_ID missing")
            return

        interval = max(1, int(config.JOBS_POLL_MINUTES))
        current_minute = discord.utils.utcnow().minute

        if current_minute % interval != 0:
            return

        channel = self.bot.get_channel(config.JOBS_CHANNEL_ID)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(config.JOBS_CHANNEL_ID)
            except Exception as e:
                print(f"[JOBS] failed to fetch channel: {e!r}")
                return

        new_items = self.service.fetch_new_items(limit=5, per_source_limit=10)
        print(f"[JOBS] new items: {len(new_items)}")

        for item in reversed(new_items):
            embed = discord.Embed(
                title=item["title"],
                url=item.get("link") or None,
                description=trim_text(item.get("summary", ""), 350),
                color=0x000000,
            )
            embed.add_field(name="Source", value=item.get("source", "Unknown"), inline=True)
            embed.add_field(name="Published", value=item.get("published", "Unknown"), inline=False)

            try:
                await channel.send(content=item.get("link") or None, embed=embed)
                print(f"[JOBS] sent: {item['source']} -> {item['title']}")
            except Exception as e:
                print(f"[JOBS] failed to send item: {e!r}")

    @loop.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(JobsCog(bot))
