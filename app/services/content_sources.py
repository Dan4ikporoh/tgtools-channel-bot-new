from __future__ import annotations

import random
from datetime import datetime
from typing import Any

import feedparser
import httpx
import yaml
from bs4 import BeautifulSoup

from app.utils.text import normalize_text, safe_caption


class ContentProvider:
    def __init__(self, sources_path: str, default_language: str = "ru") -> None:
        self.sources_path = sources_path
        self.default_language = default_language
        with open(sources_path, "r", encoding="utf-8") as f:
            self.sources = yaml.safe_load(f)

    def categories(self) -> list[str]:
        return list(self.sources["categories"].keys())

    async def fetch_item(self, category: str, seen_ids: set[str]) -> dict[str, Any] | None:
        entry = self.sources["categories"][category]
        source_type = entry["type"]
        if source_type == "rss":
            return await self._from_rss(category, entry, seen_ids)
        if source_type == "holiday":
            return await self._holiday_item(category)
        if source_type == "nasa_apod":
            return await self._nasa_apod(category, seen_ids)
        if source_type == "wikimedia_featured":
            return await self._wikimedia_featured(category, seen_ids)
        return None

    async def _from_rss(self, category: str, entry: dict[str, Any], seen_ids: set[str]) -> dict[str, Any] | None:
        urls = list(entry.get("feed_urls", []))
        random.shuffle(urls)
        for feed_url in urls:
            parsed = feedparser.parse(feed_url)
            candidates = parsed.entries[:20]
            random.shuffle(candidates)
            for item in candidates:
                external_id = item.get("id") or item.get("link")
                if not external_id or external_id in seen_ids:
                    continue
                title = normalize_text(item.get("title", "Интересная находка"))
                summary = safe_caption(item.get("summary", item.get("description", "")), limit=500)
                media_url = None
                media_candidates = item.get("media_content") or item.get("media_thumbnail") or []
                if media_candidates:
                    media_url = media_candidates[0].get("url")
                if not media_url:
                    soup = BeautifulSoup(item.get("summary", "") or "", "html.parser")
                    img = soup.find("img")
                    if img and img.get("src"):
                        media_url = img["src"]
                return {
                    "category": category,
                    "source_type": "rss",
                    "source_url": feed_url,
                    "external_id": external_id,
                    "title": title,
                    "text": self._render_caption(category, title, summary, item.get("link")),
                    "media_url": media_url,
                    "link": item.get("link"),
                }
        return None

    async def _holiday_item(self, category: str) -> dict[str, Any] | None:
        today = datetime.utcnow().date()
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(f"https://date.nager.at/api/v3/PublicHolidays/{today.year}/AT")
            response.raise_for_status()
            data = response.json()
        holidays_today = [x for x in data if x.get("date") == today.isoformat()]
        if holidays_today:
            holiday = random.choice(holidays_today)
            title = f"Сегодня: {holiday['localName']}"
            text = (
                f"🎉 {holiday['localName']}\n\n"
                f"Сегодня в Австрии отмечают этот день. Можно обыграть тему в комментариях, мемах или мини-подборке."
            )
        else:
            title = f"День {today.strftime('%d.%m')}"
            text = (
                "📅 Новый день — новый повод для контента.\n\n"
                "Сделайте быстрый интерактив: спросите подписчиков, что у них сегодня интересного, какую игру проходят или какой бот советуют."
            )
        return {
            "category": category,
            "source_type": "holiday",
            "source_url": "https://date.nager.at/",
            "external_id": f"holiday:{today.isoformat()}",
            "title": title,
            "text": text,
            "media_url": None,
        }

    async def _nasa_apod(self, category: str, seen_ids: set[str]) -> dict[str, Any] | None:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get("https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY")
            response.raise_for_status()
            data = response.json()
        external_id = f"nasa:{data.get('date')}"
        if external_id in seen_ids:
            return None
        media_url = data.get("hdurl") or data.get("url")
        return {
            "category": category,
            "source_type": "nasa_apod",
            "source_url": "https://api.nasa.gov/",
            "external_id": external_id,
            "title": data.get("title", "Космос дня"),
            "text": self._render_caption(category, data.get("title", "Космос дня"), data.get("explanation", ""), data.get("url")),
            "media_url": media_url if data.get("media_type") == "image" else None,
            "link": data.get("url"),
        }

    async def _wikimedia_featured(self, category: str, seen_ids: set[str]) -> dict[str, Any] | None:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get("https://commons.wikimedia.org/w/api.php", params={
                "action": "query",
                "format": "json",
                "prop": "imageinfo",
                "titles": "Commons:Featured pictures/chronological",
                "iiprop": "url",
            })
            response.raise_for_status()
        external_id = f"wikimedia:{datetime.utcnow().date().isoformat()}"
        if external_id in seen_ids:
            return None
        return {
            "category": category,
            "source_type": "wikimedia_featured",
            "source_url": "https://commons.wikimedia.org/",
            "external_id": external_id,
            "title": "Фото дня",
            "text": "🖼 Сегодняшний визуальный пост. Сохраняйте, делитесь и пишите в комментариях, какая картинка зашла больше всего.",
            "media_url": "https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png",
        }

    def _render_caption(self, category: str, title: str, summary: str, link: str | None) -> str:
        label = self.sources["categories"][category]["label"]
        body = f"🔥 {title}\n\n{summary}"
        if link:
            body += f"\n\nИсточник: {link}"
        body += f"\n\n#{category} #{label.replace(' ', '')[:20]}"
        return safe_caption(body, limit=1024)
