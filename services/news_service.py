import json
import time
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Optional

import feedparser


class NewsService:
    def __init__(
        self,
        sources_path: str = "data/news_sources.json",
        state_path: str = "data/news_seen.json",
    ):
        self.sources_path = Path(sources_path)
        self.state_path = Path(state_path)

    def load_sources(self) -> list[dict]:
        if not self.sources_path.exists():
            print(f"[NEWS_SERVICE] sources file not found: {self.sources_path}")
            return []

        try:
            with self.sources_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[NEWS_SERVICE] failed to read sources: {e!r}")
            return []

        if not isinstance(data, list):
            print("[NEWS_SERVICE] sources json is not a list")
            return []

        valid_sources = []
        for item in data:
            if not isinstance(item, dict):
                continue

            name = item.get("name")
            url = item.get("url")
            category = item.get("category", "cyber")

            if not name or not url:
                continue

            valid_sources.append(
                {
                    "name": str(name),
                    "url": str(url),
                    "category": str(category),
                }
            )

        return valid_sources

    def load_seen(self) -> set[str]:
        if not self.state_path.exists():
            return set()

        try:
            with self.state_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                return set()

            return {str(x) for x in data if x}
        except Exception:
            return set()

    def save_seen(self, seen: set[str]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        trimmed = list(sorted(seen))[-5000:]

        with self.state_path.open("w", encoding="utf-8") as f:
            json.dump(trimmed, f, ensure_ascii=False, indent=2)

    def _entry_id(self, item: dict) -> Optional[str]:
        link = item.get("link")
        title = item.get("title")

        if link:
            return str(link).strip()
        if title:
            return str(title).strip()
        return None

    def _entry_timestamp(self, entry) -> float:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return time.mktime(entry.published_parsed)

        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            return time.mktime(entry.updated_parsed)

        published = getattr(entry, "published", None)
        if published:
            try:
                return parsedate_to_datetime(published).timestamp()
            except Exception:
                pass

        return 0.0

    def fetch_latest(
        self,
        limit: int = 10,
        category: Optional[str] = None,
        per_source_limit: int = 5,
    ) -> list[dict]:
        sources = self.load_sources()
        if category:
            sources = [s for s in sources if s["category"].lower() == category.lower()]

        items = []

        for source in sources:
            try:
                feed = feedparser.parse(source["url"])
            except Exception as e:
                print(f"[NEWS_SERVICE] parse error for {source['name']}: {e!r}")
                continue

            if getattr(feed, "bozo", 0):
                print(f"[NEWS_SERVICE] warning: bozo feed for {source['name']}")

            source_entries = getattr(feed, "entries", [])
            print(f"[NEWS_SERVICE] {source['name']} -> {len(source_entries)} entries")

            for entry in source_entries[:per_source_limit]:
                item = {
                    "source": source["name"],
                    "category": source["category"],
                    "title": getattr(entry, "title", "Untitled"),
                    "link": getattr(entry, "link", None),
                    "published": getattr(entry, "published", "Unknown"),
                    "summary": getattr(entry, "summary", ""),
                    "_ts": self._entry_timestamp(entry),
                }
                items.append(item)

        items.sort(key=lambda x: x.get("_ts", 0.0), reverse=True)
        return items[:limit]

    def fetch_new_items(
        self,
        limit: int = 10,
        category: Optional[str] = None,
        per_source_limit: int = 5,
    ) -> list[dict]:
        seen = self.load_seen()
        latest = self.fetch_latest(
            limit=100,
            category=category,
            per_source_limit=per_source_limit,
        )

        new_items = []
        for item in latest:
            item_id = self._entry_id(item)
            if not item_id:
                continue
            if item_id in seen:
                continue

            new_items.append(item)
            seen.add(item_id)

            if len(new_items) >= limit:
                break

        if new_items:
            self.save_seen(seen)

        return new_items
