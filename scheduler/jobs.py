
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db.client import ensure_indexes
from scheduler.change_detector import detect_changes_for_all_books
from crawler.crawler import crawl_all
from utils.logger import logger
import asyncio

scheduler = AsyncIOScheduler()

async def startup():
    await ensure_indexes()

def schedule_jobs():
    # daily crawl at 02:00 local time
    scheduler.add_job(crawl_all, "cron", hour=2, minute=56)
    # daily change detection at 02:00 local time
    scheduler.add_job(detect_changes_for_all_books, "cron", hour=2, minute=0)
    scheduler.start()

async def main():
    await startup()
    schedule_jobs()
    logger.info("Scheduler running — press Ctrl+C to exit")
    try:
        while True:
            await asyncio.sleep(3600) # Keep the main loop alive asynchronously
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")

if __name__ == "__main__":
    asyncio.run(main())
