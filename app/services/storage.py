from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import aiosqlite


class Storage:
    def __init__(self, path: str = "bot.db") -> None:
        self.path = path

    async def add_post(self, data: dict[str, Any]) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO posts (
                    category, source_type, source_url, title, text, media_url,
                    channel_message_id, discussion_message_id, posted_at, external_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["category"], data["source_type"], data.get("source_url"), data["title"], data["text"],
                    data.get("media_url"), data.get("channel_message_id"), data.get("discussion_message_id"),
                    datetime.now(timezone.utc).isoformat(), data.get("external_id"),
                ),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def get_recent_external_ids(self, limit: int = 300) -> set[str]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT external_id FROM posts WHERE external_id IS NOT NULL ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
        return {row[0] for row in rows if row[0]}

    async def record_feedback(self, post_id: int, event_type: str, value: float = 1.0) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO feedback_events (post_id, event_type, value, created_at) VALUES (?, ?, ?, ?)",
                (post_id, event_type, value, now),
            )
            await db.commit()

    async def update_post_metrics(self, post_id: int, *, views: int = 0, reactions: int = 0, comments: int = 0) -> None:
        score = views * 0.03 + reactions * 2 + comments * 1.5
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE posts SET views = ?, reactions = ?, comments = ?, score = ? WHERE id = ?",
                (views, reactions, comments, score, post_id),
            )
            await db.execute(
                """
                INSERT INTO category_stats(category, impressions, reward, last_posted_at)
                SELECT category, 1, ?, ? FROM posts WHERE id = ?
                ON CONFLICT(category) DO UPDATE SET
                  impressions = impressions + 1,
                  reward = reward + excluded.reward,
                  last_posted_at = excluded.last_posted_at
                """,
                (score, datetime.now(timezone.utc).isoformat(), post_id),
            )
            await db.commit()

    async def top_posts(self, limit: int = 5) -> list[tuple]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT id, title, category, score, channel_message_id FROM posts ORDER BY score DESC, id DESC LIMIT ?",
                (limit,),
            )
            return await cursor.fetchall()

    async def get_post_by_channel_message_id(self, channel_message_id: int) -> tuple | None:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT id, category, title, channel_message_id FROM posts WHERE channel_message_id = ?",
                (channel_message_id,),
            )
            return await cursor.fetchone()

    async def add_moderation_event(self, user_id: int | None, username: str | None, text: str, action: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO moderation_events(user_id, username, text, created_at, action) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, text, datetime.now(timezone.utc).isoformat(), action),
            )
            await db.commit()

    async def increment_pin(self, post_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE posts SET pins = pins + 1, was_pinned = 1 WHERE id = ?", (post_id,))
            await db.commit()

    async def category_stats(self) -> list[tuple]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT category, impressions, reward, last_posted_at FROM category_stats ORDER BY reward DESC"
            )
            return await cursor.fetchall()
