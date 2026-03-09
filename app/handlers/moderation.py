from __future__ import annotations

from aiogram import Bot, Router
from aiogram.types import Message

from app.services.storage import Storage
from app.utils.text import contains_bad_language

router = Router(name="moderation")


def setup_moderation_handlers(bot: Bot, storage: Storage, discussion_chat_id: int, warn_text: str):
    @router.message()
    async def moderate(message: Message) -> None:
        if message.chat.id != discussion_chat_id:
            return
        if not message.text:
            return
        if not contains_bad_language(message.text):
            return
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        finally:
            await storage.add_moderation_event(
                user_id=message.from_user.id if message.from_user else None,
                username=message.from_user.username if message.from_user else None,
                text=message.text,
                action="delete_bad_language",
            )
        await bot.send_message(chat_id=message.chat.id, text=warn_text)

    return router
