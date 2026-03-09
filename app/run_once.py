from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import Settings
from app.db import init_db
from app.services.content_sources import ContentProvider
from app.services.poster import Poster
from app.services.ranking import CategoryRanker
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
    storage = Storage()
    provider = ContentProvider("app/data/sources.yaml", settings.default_language)
    ranker = CategoryRanker()
    poster = Poster(bot, settings.channel_id)

    seen_ids = await storage.get_recent_external_ids()
    category = ranker.choose(provider.categories(), await storage.category_stats())
    item = await provider.fetch_item(category, seen_ids)
    if not item:
        logger.warning("No content found for category %s", category)
        return

    message_id = await poster.publish(item)
    post_id = await storage.add_post({**item, "channel_message_id": message_id})
    logger.info("Published post %s / message_id=%s", post_id, message_id)
    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
