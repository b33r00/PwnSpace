import json
import time
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Optional

import feedparser
import requests
from bs4 import BeautifulSoup


class JobsService:
    def __init__(
        self,
        sources_path: str = "data/job_sources.json",
        state_path: str = "data/jobs_seen.json",
    ):
        self.sources_path = Path(sources_path)
        self.state_path = Path(state_path)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0 Safari/537.36 PwnSpaceBot/1.0"
                )
            }
        )

    def load_sources(self) -> list[dict]:
        if not self.sources_path.exists():
            print(f"[JOBS_SERVICE] sources file not found: {self.sources_path}")
            return []

        try:
            with self.sources_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[JOBS_SERVICE] failed to read sources: {e!r}")
            return []

        if not isinstance(data, list):
            print("[JOBS_SERVICE] sources json is not a list")
            return []

        valid_sources = []
        for item in data:
            if not isinstance(item, dict):
                continue

            name = item.get("name")
            url = item.get("url")
            category = item.get("category", "jobs")
            source_type = item.get("type", "rss")

            if not name or not url:
                continue

            valid_sources.append(
                {
                    "name": str(name),
                    "url": str(url),
                    "category": str(category),
                    "type": str(source_type).lower(),
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

    def _parse_date_to_ts(self, raw: str | None) -> float:
        if not raw:
            return 0.0
        try:
            return parsedate_to_datetime(raw).timestamp()
        except Exception:
            return 0.0

    def _entry_timestamp_from_feed(self, entry) -> float:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return time.mktime(entry.published_parsed)

        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            return time.mktime(entry.updated_parsed)

        published = getattr(entry, "published", None)
        if published:
            return self._parse_date_to_ts(published)

        return 0.0

    def _clean_text(self, text: str) -> str:
        return " ".join((text or "").split())

    def _matches_keywords(self, title: str, summary: str) -> bool:
        blob = f"{title}\n{summary}".lower()

        positive = [
            "security",
            "cyber",
            "cybersecurity",
            "pentest",
            "penetration",
            "appsec",
            "application security",
            "red team",
            "blue team",
            "soc",
            "incident response",
            "threat",
            "malware",
            "reverse engineer",
            "reversing",
            "offensive security",
            "vulnerability",
            "security engineer",
            "security analyst",
            "security researcher",
            "security consultant",
            "devsecops",
            "cloud security",
        ]

        negative = [
            "sales",
            "marketing",
            "hr",
            "recruiter",
            "seo",
            "content writer",
            "support",
            "customer success",
            "account executive",
            "business development",
        ]

        if not any(k in blob for k in positive):
            return False

        if any(k in blob for k in negative):
            return False

        return True

    def _fetch_rss_source(self, source: dict, per_source_limit: int = 10) -> list[dict]:
        items = []

        try:
            feed = feedparser.parse(source["url"])
        except Exception as e:
            print(f"[JOBS_SERVICE] parse error for {source['name']}: {e!r}")
            return items

        if getattr(feed, "bozo", 0):
            print(f"[JOBS_SERVICE] warning: bozo feed for {source['name']}")

        entries = getattr(feed, "entries", [])
        print(f"[JOBS_SERVICE] {source['name']} [rss] -> {len(entries)} entries")

        for entry in entries[:per_source_limit]:
            title = self._clean_text(str(getattr(entry, "title", "Untitled")))
            summary = self._clean_text(str(getattr(entry, "summary", "")))
            link = getattr(entry, "link", None)
            published = getattr(entry, "published", "Unknown")

            if not self._matches_keywords(title, summary):
                continue

            items.append(
                {
                    "source": source["name"],
                    "category": source["category"],
                    "title": title,
                    "link": link,
                    "published": published,
                    "summary": summary,
                    "_ts": self._entry_timestamp_from_feed(entry),
                }
            )

        return items

    def _fetch_infosec_jobs(self, source: dict, limit: int = 10) -> list[dict]:
        items = []

        try:
            response = self.session.get(source["url"], timeout=15)
            response.raise_for_status()
        except Exception as e:
            print(f"[JOBS_SERVICE] scrape error for {source['name']}: {e!r}")
            return items

        soup = BeautifulSoup(response.text, "html.parser")

        cards = soup.select("a[href*='/job/'], a[href*='/jobs/']")
        print(f"[JOBS_SERVICE] {source['name']} [scrape] -> {len(cards)} candidate links")

        seen_links = set()

        for link_tag in cards:
            href = link_tag.get("href")
            if not href:
                continue

            if href.startswith("/"):
                href = source["url"].rstrip("/") + href

            if href in seen_links:
                continue
            seen_links.add(href)

            text = self._clean_text(link_tag.get_text(" ", strip=True))
            if len(text) < 8:
                continue

            title = text
            summary = text

            if not self._matches_keywords(title, summary):
                continue

            items.append(
                {
                    "source": source["name"],
                    "category": source["category"],
                    "title": title[:200],
                    "link": href,
                    "published": "Unknown",
                    "summary": summary[:500],
                    "_ts": time.time(),
                }
            )

            if len(items) >= limit:
                break

        return items

    def _fetch_scrape_source(self, source: dict, per_source_limit: int = 10) -> list[dict]:
        name = source["name"].lower()

        if "infosec jobs" in name:
            return self._fetch_infosec_jobs(source, limit=per_source_limit)

        print(f"[JOBS_SERVICE] no scraper implemented for {source['name']}")
        return []

    def fetch_latest(
        self,
        limit: int = 10,
        per_source_limit: int = 10,
    ) -> list[dict]:
        sources = self.load_sources()
        items = []

        for source in sources:
            source_type = source.get("type", "rss")

            if source_type == "rss":
                source_items = self._fetch_rss_source(source, per_source_limit=per_source_limit)
            elif source_type == "scrape":
                source_items = self._fetch_scrape_source(source, per_source_limit=per_source_limit)
            else:
                print(f"[JOBS_SERVICE] unknown source type for {source['name']}: {source_type}")
                source_items = []

            items.extend(source_items)

        unique = {}
        for item in items:
            item_id = self._entry_id(item)
            if not item_id:
                continue

            existing = unique.get(item_id)
            if existing is None or item.get("_ts", 0.0) > existing.get("_ts", 0.0):
                unique[item_id] = item

        deduped = list(unique.values())
        deduped.sort(key=lambda x: x.get("_ts", 0.0), reverse=True)

        return deduped[:limit]

    def fetch_new_items(
        self,
        limit: int = 10,
        per_source_limit: int = 10,
    ) -> list[dict]:
        seen = self.load_seen()
        latest = self.fetch_latest(limit=100, per_source_limit=per_source_limit)

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
