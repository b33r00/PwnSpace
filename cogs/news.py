import discord
from discord.ext import commands, tasks

import config
from services.news_service import NewsService


def trim_text(text: str, max_len: int = 350) -> str:
    text = (text or "").strip()
    if not text:
        return "No summary available."
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


class NewsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.service = NewsService(
            sources_path="data/news_sources.json",
            state_path=config.NEWS_STATE_PATH,
        )
        self.started = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self.started:
            return

        self.started = True
        print("[NEWS] ready")

        await self.send_startup_news()

        if not self.loop.is_running():
            self.loop.start()
            print("[NEWS] loop started")

    async def send_startup_news(self):
        if not config.NEWS_CHANNEL_ID:
            print("[NEWS] NEWS_CHANNEL_ID not set")
            return

        channel = self.bot.get_channel(config.NEWS_CHANNEL_ID)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(config.NEWS_CHANNEL_ID)
            except Exception as e:
                print(f"[NEWS] failed to fetch channel: {e!r}")
                return

        items = self.service.fetch_latest(limit=5, per_source_limit=3)
        print(f"[NEWS] startup fetched {len(items)} items")

        if not items:
            return

        seen = self.service.load_seen()
        sent = 0

        for item in reversed(items):
            item_id = self.service._entry_id(item)
            if not item_id or item_id in seen:
                continue

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
                seen.add(item_id)
                sent += 1
            except Exception as e:
                print(f"[NEWS] failed to send startup item: {e!r}")

        self.service.save_seen(seen)
        print(f"[NEWS] startup sent {sent} items")

    @tasks.loop(minutes=1)
    async def loop(self):
        print("[NEWS] tick")

        if not config.NEWS_CHANNEL_ID:
            print("[NEWS] NEWS_CHANNEL_ID missing")
            return

        interval = max(1, int(config.NEWS_POLL_MINUTES))
        current_minute = discord.utils.utcnow().minute

        if current_minute % interval != 0:
            return

        channel = self.bot.get_channel(config.NEWS_CHANNEL_ID)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(config.NEWS_CHANNEL_ID)
            except Exception as e:
                print(f"[NEWS] failed to fetch channel: {e!r}")
                return

        new_items = self.service.fetch_new_items(limit=5, per_source_limit=3)
        print(f"[NEWS] new items: {len(new_items)}")

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
                print(f"[NEWS] sent: {item['source']} -> {item['title']}")
            except Exception as e:
                print(f"[NEWS] failed to send item: {e!r}")

    @loop.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(NewsCog(bot))
