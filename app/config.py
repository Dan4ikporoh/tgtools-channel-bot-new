from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass(slots=True)
class Settings:
    bot_token: str
    channel_id: str
    discussion_chat_id: int
    owner_ids: List[int]
    timezone: str
    post_times: List[str]
    default_language: str
    enable_telethon_analytics: bool
    telegram_api_id: str | None
    telegram_api_hash: str | None
    telegram_session: str
    pin_high_performers: bool
    high_performer_score: int
    moderation_warn_text: str


    @classmethod
    def load(cls) -> "Settings":
        owners = [int(x.strip()) for x in os.getenv("OWNER_IDS", "").split(",") if x.strip()]
        return cls(
            bot_token=os.getenv("BOT_TOKEN", ""),
            channel_id=os.getenv("CHANNEL_ID", ""),
            discussion_chat_id=int(os.getenv("DISCUSSION_CHAT_ID", "0")),
            owner_ids=owners,
            timezone=os.getenv("TIMEZONE", "Europe/Vienna"),
            post_times=[x.strip() for x in os.getenv("POST_TIMES", "09:30,19:30").split(",") if x.strip()],
            default_language=os.getenv("DEFAULT_LANGUAGE", "ru"),
            enable_telethon_analytics=os.getenv("ENABLE_TELETHON_ANALYTICS", "false").lower() == "true",
            telegram_api_id=os.getenv("TELEGRAM_API_ID") or None,
            telegram_api_hash=os.getenv("TELEGRAM_API_HASH") or None,
            telegram_session=os.getenv("TELEGRAM_SESSION", "analytics_session"),
            pin_high_performers=os.getenv("PIN_HIGH_PERFORMERS", "true").lower() == "true",
            high_performer_score=int(os.getenv("HIGH_PERFORMER_SCORE", "18")),
            moderation_warn_text=os.getenv(
                "MODERATION_WARN_TEXT",
                "Мат, оскорбления и токсичность запрещены. Комментарий удален. Соблюдайте уважительный тон.",
            ),
        )

    def validate(self) -> None:
        missing = []
        if not self.bot_token:
            missing.append("BOT_TOKEN")
        if not self.channel_id:
            missing.append("CHANNEL_ID")
        if not self.discussion_chat_id:
            missing.append("DISCUSSION_CHAT_ID")
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
