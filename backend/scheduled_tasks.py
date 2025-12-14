"""Scheduled tasks for periodic scraping."""

import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional

from database import SessionLocal, ScrapeSchedule
from scrapers.scraping_service import scraping_service

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()

async def execute_scrape_job(schedule_id: int):
    """
    Execute a single scheduled scrape job.
    """
    logger.info(f"Executing scheduled job {schedule_id}")
    db = SessionLocal()
    try:
        schedule = db.query(ScrapeSchedule).filter(ScrapeSchedule.id == schedule_id).first()
        if not schedule or not schedule.is_active:
            logger.warning(f"Schedule {schedule_id} not found or inactive")
            return

        # Execute based on type (Runs in thread pool via scraping_service)
        # Note: scraping_service methods are sync, but execute_scrape_job is async.
        # APScheduler runs async jobs in event loop. Blocking calls here will block loop.
        # scraping_service uses ThreadPoolExecutor internally? No, it uses it for concurrent sub-tasks.
        # But the methods themselves are synchronous wrapper calls.
        # We should run them in a thread executor to be safe.
        
        import asyncio
        loop = asyncio.get_running_loop()
        
        params = schedule.job_params or {}
        
        if schedule.job_type == "job_boards":
            await loop.run_in_executor(None, lambda: scraping_service.scrape_job_boards(**params))
        elif schedule.job_type == "startup_listings":
            await loop.run_in_executor(None, lambda: scraping_service.scrape_startup_listings(**params))
        elif schedule.job_type == "custom_urls":
            await loop.run_in_executor(None, lambda: scraping_service.scrape_custom_urls(**params))
        
        # Update stats
        schedule.last_run_at = datetime.utcnow()
        db.commit()
        logger.info(f"Job {schedule_id} ({schedule.name}) completed")

    except Exception as e:
        logger.error(f"Error in scheduled job {schedule_id}: {e}")
    finally:
        db.close()

def configure_scheduler():
    """
    Load schedules from DB and configure scheduler.
    """
    db = SessionLocal()
    try:
        schedules = db.query(ScrapeSchedule).filter(ScrapeSchedule.is_active == True).all()
        
        # Clear existing jobs to avoid duplicates on reload
        scheduler.remove_all_jobs()
        
        for sched in schedules:
            trigger = None
            try:
                if sched.schedule_type == "cron" and sched.cron_expression:
                    trigger = CronTrigger.from_crontab(sched.cron_expression)
                elif sched.schedule_type == "interval" and sched.interval_minutes:
                    trigger = IntervalTrigger(minutes=sched.interval_minutes)
                
                if trigger:
                    scheduler.add_job(
                        execute_scrape_job,
                        trigger=trigger,
                        args=[sched.id],
                        id=str(sched.id),
                        name=sched.name,
                        replace_existing=True
                    )
                    logger.info(f"Loaded schedule: {sched.name} ({sched.schedule_type})")
            except Exception as e:
                logger.error(f"Error loading schedule {sched.name}: {e}")
                
    except Exception as e:
        logger.error(f"Error configuring scheduler: {e}")
    finally:
        db.close()

def start_scheduler():
    """Start the scheduler."""
    if not scheduler.running:
        configure_scheduler()
        scheduler.start()
        logger.info("Scheduler started successfully")
    else:
        logger.warning("Scheduler is already running")

def stop_scheduler():
    """Stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")

def refresh_scheduler():
    """Reload schedules from DB."""
    logger.info("Refreshing scheduler...")
    configure_scheduler()


def get_scheduled_jobs() -> List[Dict[str, Any]]:
    """Return a serializable list of currently scheduled jobs."""
    jobs = []
    try:
        for job in scheduler.get_jobs():
            next_run_time: Optional[str] = None
            if job.next_run_time:
                try:
                    next_run_time = job.next_run_time.isoformat()
                except Exception:
                    next_run_time = str(job.next_run_time)

            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": next_run_time,
                    "trigger": str(job.trigger),
                }
            )
    except Exception as e:
        logger.error(f"Error retrieving scheduled jobs: {e}")

    return jobs


def trigger_job_now(job_id: str) -> bool:
    """Force a scheduled job to run as soon as possible."""
    job = scheduler.get_job(job_id)
    if not job:
        return False

    try:
        scheduler.modify_job(job_id, next_run_time=datetime.utcnow())
        return True
    except Exception as e:
        logger.error(f"Error triggering job {job_id}: {e}")
        return False
