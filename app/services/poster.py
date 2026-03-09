from __future__ import annotations

import logging

import httpx
from aiogram import Bot
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)


class Poster:
    def __init__(self, bot: Bot, channel_id: str) -> None:
        self.bot = bot
        self.channel_id = channel_id

    async def publish(self, item: dict) -> int:
        reply_markup = None
        if item.get("link"):
            reply_markup = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="Открыть источник", url=item["link"])]]
            )
        media_url = item.get("media_url")
        if media_url:
            try:
                async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                    resp = await client.get(media_url)
                    resp.raise_for_status()
                ext = media_url.split("?")[0].split(".")[-1].lower()
                if ext in {"jpg", "jpeg", "png", "webp"}:
                    photo = BufferedInputFile(resp.content, filename=f"post.{ext}")
                    msg = await self.bot.send_photo(
                        chat_id=self.channel_id,
                        photo=photo,
                        caption=item["text"],
                        reply_markup=reply_markup,
                    )
                    return msg.message_id
            except Exception as exc:
                logger.warning("Could not send media %s: %s", media_url, exc)
        msg = await self.bot.send_message(
            chat_id=self.channel_id,
            text=item["text"],
            disable_web_page_preview=False,
            reply_markup=reply_markup,
        )
        return msg.message_id
