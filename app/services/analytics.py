from __future__ import annotations

import logging
from dataclasses import dataclass

from telethon import TelegramClient
from telethon.errors import RPCError
from telethon.tl.functions.channels import GetMessagesRequest
from telethon.tl.types import InputMessageID

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PostMetrics:
    views: int = 0
    reactions: int = 0
    comments: int = 0


class AnalyticsCollector:
    def __init__(self, api_id: str | None, api_hash: str | None, session: str) -> None:
        self.api_id = api_id
        self.api_hash = api_hash
        self.session = session

    async def fetch_message_metrics(self, channel: str, message_id: int) -> PostMetrics:
        if not self.api_id or not self.api_hash:
            return PostMetrics()
        client = TelegramClient(self.session, int(self.api_id), self.api_hash)
        await client.connect()
        try:
            entity = await client.get_entity(channel)
            messages = await client(GetMessagesRequest(id=[InputMessageID(message_id)], channel=entity))
            if not messages.messages:
                return PostMetrics()
            message = messages.messages[0]
            reactions = 0
            if getattr(message, "reactions", None) and getattr(message.reactions, "results", None):
                reactions = sum(int(x.count) for x in message.reactions.results)
            return PostMetrics(
                views=int(getattr(message, "views", 0) or 0),
                reactions=reactions,
                comments=int(getattr(message, "replies", None).replies if getattr(message, "replies", None) else 0),
            )
        except RPCError as exc:
            logger.warning("Failed to fetch metrics via Telethon: %s", exc)
            return PostMetrics()
        finally:
            await client.disconnect()
