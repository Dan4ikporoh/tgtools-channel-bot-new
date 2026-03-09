from __future__ import annotations

import aiosqlite


SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_url TEXT,
    title TEXT NOT NULL,
    text TEXT NOT NULL,
    media_url TEXT,
    channel_message_id INTEGER,
    discussion_message_id INTEGER,
    posted_at TEXT NOT NULL,
    external_id TEXT,
    score REAL DEFAULT 0,
    views INTEGER DEFAULT 0,
    reactions INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    pins INTEGER DEFAULT 0,
    was_pinned INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS feedback_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    value REAL NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY(post_id) REFERENCES posts(id)
);

CREATE TABLE IF NOT EXISTS moderation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    text TEXT,
    created_at TEXT NOT NULL,
    action TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS category_stats (
    category TEXT PRIMARY KEY,
    impressions REAL NOT NULL DEFAULT 0,
    reward REAL NOT NULL DEFAULT 0,
    last_posted_at TEXT
);
"""


async def init_db(path: str = "bot.db") -> None:
    async with aiosqlite.connect(path) as db:
        await db.executescript(SCHEMA)
        await db.commit()
