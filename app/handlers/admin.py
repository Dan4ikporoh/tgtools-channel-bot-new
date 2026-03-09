from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.services.analytics import AnalyticsCollector
from app.services.content_sources import ContentProvider
from app.services.poster import Poster
from app.services.ranking import CategoryRanker
from app.services.storage import Storage

router = Router(name="admin")


def setup_admin_handlers(
    storage: Storage,
    provider: ContentProvider,
    ranker: CategoryRanker,
    poster: Poster,
    analytics: AnalyticsCollector,
    owner_ids: list[int],
    channel_id: str,
):
    def owner_only(message: Message) -> bool:
        return bool(message.from_user and message.from_user.id in owner_ids)

    @router.message(Command("post_now"))
    async def post_now(message: Message) -> None:
        if not owner_only(message):
            return
        categories = provider.categories()
        category = ranker.choose(categories, await storage.category_stats())
        item = await provider.fetch_item(category, await storage.get_recent_external_ids())
        if not item:
            await message.answer("Не удалось подобрать пост. Попробуйте еще раз через пару минут.")
            return
        channel_message_id = await poster.publish(item)
        post_id = await storage.add_post({**item, "channel_message_id": channel_message_id})
        await message.answer(f"Опубликовано: {item['title']}\npost_id={post_id}, message_id={channel_message_id}")

    @router.message(Command("top_posts"))
    async def top_posts(message: Message) -> None:
        if not owner_only(message):
            return
        rows = await storage.top_posts(10)
        if not rows:
            await message.answer("Пока нет данных.")
            return
        lines = ["Топ постов:"]
        for post_id, title, category, score, msg_id in rows:
            lines.append(f"• #{post_id} [{category}] {title} — score={score:.1f}, msg={msg_id}")
        await message.answer("\n".join(lines))

    @router.message(Command("sync_stats"))
    async def sync_stats(message: Message) -> None:
        if not owner_only(message):
            return
        synced = 0
        for post_id, title, category, score, msg_id in await storage.top_posts(20):
            metrics = await analytics.fetch_message_metrics(channel_id, msg_id)
            await storage.update_post_metrics(post_id, views=metrics.views, reactions=metrics.reactions, comments=metrics.comments)
            synced += 1
        await message.answer(f"Синхронизировано постов: {synced}")

    return router
