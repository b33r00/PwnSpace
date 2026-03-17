import discord
from discord import app_commands
from discord.ext import commands

from services.news_service import NewsService


def trim_text(text: str, max_len: int = 300) -> str:
    text = (text or "").strip()
    if not text:
        return "No summary available."
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


class NewsCog(commands.GroupCog, group_name="news", group_description="Cyber news commands"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.news_service = NewsService()
        super().__init__()

    @app_commands.command(name="sources", description="List configured news sources")
    async def sources(self, interaction: discord.Interaction):
        sources = self.news_service.list_sources()

        if not sources:
            await interaction.response.send_message("No news sources are configured.", ephemeral=True)
            return

        embed = discord.Embed(title="Configured news sources", color=0x000000)

        for source in sources[:25]:
            embed.add_field(
                name=source["name"],
                value=f"Category: {source['category']}\nFeed: {source['url']}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="latest", description="Show latest news entries")
    @app_commands.describe(
        limit="How many items to return (max 10)",
        category="Optional category filter"
    )
    async def latest(
        self,
        interaction: discord.Interaction,
        limit: app_commands.Range[int, 1, 10] = 5,
        category: str | None = None
    ):
        await interaction.response.defer(ephemeral=True)

        items = self.news_service.fetch_latest(limit=limit, category=category)

        if not items:
            await interaction.followup.send("No news items found.", ephemeral=True)
            return

        embed = discord.Embed(title="Latest news", color=0x000000)

        for item in items:
            summary = trim_text(item.get("summary", ""), 220)
            link = item.get("link") or "No link"
            published = item.get("published", "Unknown")

            embed.add_field(
                name=item["title"],
                value=(
                    f"Source: {item['source']}\n"
                    f"Published: {published}\n"
                    f"Link: {link}\n"
                    f"Summary: {summary}"
                ),
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="search", description="Search news entries by keyword")
    @app_commands.describe(
        query="Keyword or phrase to search for",
        limit="How many items to return (max 10)",
        category="Optional category filter"
    )
    async def search(
        self,
        interaction: discord.Interaction,
        query: str,
        limit: app_commands.Range[int, 1, 10] = 5,
        category: str | None = None
    ):
        await interaction.response.defer(ephemeral=True)

        items = self.news_service.search(query=query, limit=limit, category=category)

        if not items:
            await interaction.followup.send(f"No results found for `{query}`.", ephemeral=True)
            return

        embed = discord.Embed(title=f"News search: {query}", color=0x000000)

        for item in items:
            summary = trim_text(item.get("summary", ""), 220)
            link = item.get("link") or "No link"
            published = item.get("published", "Unknown")

            embed.add_field(
                name=item["title"],
                value=(
                    f"Source: {item['source']}\n"
                    f"Published: {published}\n"
                    f"Link: {link}\n"
                    f"Summary: {summary}"
                ),
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(NewsCog(bot))
