from __future__ import annotations

import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self, timezone: str) -> None:
        self.scheduler = AsyncIOScheduler(timezone=ZoneInfo(timezone))

    def add_daily_jobs(self, times: list[str], func) -> None:
        for idx, time_str in enumerate(times, start=1):
            hour, minute = [int(x) for x in time_str.split(":", 1)]
            self.scheduler.add_job(
                func,
                CronTrigger(hour=hour, minute=minute),
                id=f"daily_post_{idx}",
                replace_existing=True,
            )
            logger.info("Scheduled daily post at %s", time_str)

    def add_interval_job(self, minutes: int, func, job_id: str) -> None:
        self.scheduler.add_job(func, "interval", minutes=minutes, id=job_id, replace_existing=True)

    def start(self) -> None:
        self.scheduler.start()
