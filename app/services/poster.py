from __future__ import annotations

import logging

import httpx
from aiogram import Bot
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

BOOST_URL = "https://t.me/boost/tgbots_miniapps"


def build_post_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔥 ГОЛОС", url=BOOST_URL)]
        ]
    )


class Poster:
    def __init__(self, bot: Bot, channel_id: str) -> None:
        self.bot = bot
        self.channel_id = channel_id

    async def publish(self, item: dict) -> int:
        reply_markup = build_post_keyboard()
        media_url = item.get("media_url")

        if media_url:
            try:
                async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                    resp = await client.get(media_url)
                    resp.raise_for_status()

                clean_url = media_url.split("?")[0].lower()
                ext = clean_url.split(".")[-1] if "." in clean_url else ""

                image_exts = {"jpg", "jpeg", "png", "webp"}
                video_exts = {"mp4", "mov", "m4v", "webm"}

                if ext in image_exts:
                    photo = BufferedInputFile(resp.content, filename=f"post.{ext}")
                    msg = await self.bot.send_photo(
                        chat_id=self.channel_id,
                        photo=photo,
                        caption=item["text"],
                        reply_markup=reply_markup,
                    )
                    return msg.message_id

                if ext in video_exts:
                    video = BufferedInputFile(resp.content, filename=f"post.{ext}")
                    msg = await self.bot.send_video(
                        chat_id=self.channel_id,
                        video=video,
                        caption=item["text"],
                        reply_markup=reply_markup,
                        supports_streaming=True,
                    )
                    return msg.message_id

                content_type = resp.headers.get("content-type", "").lower()

                if content_type.startswith("image/"):
                    guessed_ext = content_type.split("/")[-1].split(";")[0] or "jpg"
                    photo = BufferedInputFile(resp.content, filename=f"post.{guessed_ext}")
                    msg = await self.bot.send_photo(
                        chat_id=self.channel_id,
                        photo=photo,
                        caption=item["text"],
                        reply_markup=reply_markup,
                    )
                    return msg.message_id

                if content_type.startswith("video/"):
                    guessed_ext = content_type.split("/")[-1].split(";")[0] or "mp4"
                    video = BufferedInputFile(resp.content, filename=f"post.{guessed_ext}")
                    msg = await self.bot.send_video(
                        chat_id=self.channel_id,
                        video=video,
                        caption=item["text"],
                        reply_markup=reply_markup,
                        supports_streaming=True,
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
