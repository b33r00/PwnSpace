import json
from pathlib import Path
from typing import Optional

import feedparser


class NewsService:
    def __init__(self, sources_path: str = "data/news_sources.json"):
        self.sources_path = Path(sources_path)

    def load_sources(self) -> list[dict]:
        if not self.sources_path.exists():
            return []

        with self.sources_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return []

        valid_sources = []
        for item in data:
            if not isinstance(item, dict):
                continue

            name = item.get("name")
            url = item.get("url")
            category = item.get("category", "general")

            if not name or not url:
                continue

            valid_sources.append({
                "name": str(name),
                "url": str(url),
                "category": str(category)
            })

        return valid_sources

    def list_sources(self) -> list[dict]:
        return self.load_sources()

    def fetch_latest(
        self,
        limit: int = 5,
        category: Optional[str] = None
    ) -> list[dict]:
        sources = self.load_sources()
        if category:
            sources = [s for s in sources if s["category"].lower() == category.lower()]

        entries = []

        for source in sources:
            try:
                feed = feedparser.parse(source["url"])
            except Exception:
                continue

            for entry in feed.entries[:10]:
                entries.append({
                    "source": source["name"],
                    "category": source["category"],
                    "title": getattr(entry, "title", "Untitled"),
                    "link": getattr(entry, "link", None),
                    "published": getattr(entry, "published", "Unknown"),
                    "summary": getattr(entry, "summary", "")
                })

        def sort_key(item: dict):
            published = item.get("published", "")
            return published or ""

        entries.sort(key=sort_key, reverse=True)
        return entries[:limit]

    def search(
        self,
        query: str,
        limit: int = 5,
        category: Optional[str] = None
    ) -> list[dict]:
        query_l = query.strip().lower()
        if not query_l:
            return []

        sources = self.load_sources()
        if category:
            sources = [s for s in sources if s["category"].lower() == category.lower()]

        matches = []

        for source in sources:
            try:
                feed = feedparser.parse(source["url"])
            except Exception:
                continue

            for entry in feed.entries[:20]:
                title = str(getattr(entry, "title", ""))
                summary = str(getattr(entry, "summary", ""))
                blob = f"{title}\n{summary}".lower()

                if query_l in blob:
                    matches.append({
                        "source": source["name"],
                        "category": source["category"],
                        "title": title or "Untitled",
                        "link": getattr(entry, "link", None),
                        "published": getattr(entry, "published", "Unknown"),
                        "summary": summary
                    })

        matches.sort(key=lambda x: x.get("published", ""), reverse=True)
        return matches[:limit]
