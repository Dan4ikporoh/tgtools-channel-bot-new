from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import Settings
from app.db import init_db
from app.handlers.admin import setup_admin_handlers
from app.handlers.moderation import setup_moderation_handlers
from app.services.analytics import AnalyticsCollector
from app.services.content_sources import ContentProvider
from app.services.poster import Poster
from app.services.ranking import CategoryRanker
from app.services.scheduler import SchedulerService
from app.services.storage import Storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = Settings.load()
    settings.validate()
    await init_db()

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    storage = Storage()
    provider = ContentProvider("app/data/sources.yaml", settings.default_language)
    ranker = CategoryRanker()
    poster = Poster(bot, settings.channel_id)
    analytics = AnalyticsCollector(settings.telegram_api_id, settings.telegram_api_hash, settings.telegram_session)
    scheduler = SchedulerService(settings.timezone)

    async def publish_job() -> None:
        seen_ids = await storage.get_recent_external_ids()
        category = ranker.choose(provider.categories(), await storage.category_stats())
        item = await provider.fetch_item(category, seen_ids)
        if not item:
            logger.warning("No content found for category %s", category)
            return
        message_id = await poster.publish(item)
        post_id = await storage.add_post({**item, "channel_message_id": message_id})
        logger.info("Published post %s / message_id=%s", post_id, message_id)

    async def sync_stats_job() -> None:
        if not settings.enable_telethon_analytics:
            return
        for post_id, _title, _category, _score, msg_id in await storage.top_posts(30):
            metrics = await analytics.fetch_message_metrics(settings.channel_id, msg_id)
            await storage.update_post_metrics(post_id, views=metrics.views, reactions=metrics.reactions, comments=metrics.comments)
            if settings.pin_high_performers and (metrics.views * 0.03 + metrics.reactions * 2 + metrics.comments * 1.5) >= settings.high_performer_score:
                with suppress(Exception):
                    await bot.pin_chat_message(settings.channel_id, msg_id, disable_notification=True)
                    await storage.increment_pin(post_id)

    dp.include_router(setup_admin_handlers(storage, provider, ranker, poster, analytics, settings.owner_ids, settings.channel_id))
    dp.include_router(setup_moderation_handlers(bot, storage, settings.discussion_chat_id, settings.moderation_warn_text))

    scheduler.add_daily_jobs(settings.post_times, publish_job)
    scheduler.add_interval_job(90, sync_stats_job, "sync_stats")
    scheduler.start()

    me = await bot.get_me()
    logger.info("Bot started as @%s", me.username)
    await dp.start_polling(
        bot,
        allowed_updates=[
            "message",
            "channel_post",
            "edited_channel_post",
            "message_reaction",
            "message_reaction_count",
        ],
        handle_as_tasks=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
