"""
RecycleOps AI Assistant - Background Scheduler

APScheduler-based scheduler for background tasks like
the 12-hour learning rule.
"""
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
import structlog

from src.config import settings
from src.learning.analyzer import ConversationAnalyzer


logger = structlog.get_logger(__name__)

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """Get the scheduler instance."""
    global _scheduler
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call start_scheduler() first.")
    return _scheduler


def start_scheduler() -> None:
    """
    Initialize and start the background scheduler.
    
    Sets up jobs for:
    - Processing conversations (12-hour rule)
    - Updating expert statistics
    - Cleaning up old data
    """
    global _scheduler
    
    logger.info("Starting background scheduler...")
    
    # Configure job stores (use PostgreSQL for persistence)
    jobstores = {}
    
    # Use default memory store if DB URL not available
    # In production, we'd use SQLAlchemyJobStore for persistence:
    # jobstores = {
    #     'default': SQLAlchemyJobStore(url=settings.db_url)
    # }
    
    # Create scheduler
    _scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        job_defaults={
            'coalesce': True,  # Combine missed runs
            'max_instances': 1,  # Only one instance per job
            'misfire_grace_time': 3600,  # 1 hour grace time
        },
    )
    
    # Add job: Process pending conversations (every hour)
    _scheduler.add_job(
        process_pending_conversations,
        trigger=IntervalTrigger(hours=1),
        id='process_conversations',
        name='Process pending conversations (12-hour rule)',
        replace_existing=True,
    )
    
    # Add job: Update expert statistics (daily at 3 AM)
    _scheduler.add_job(
        update_expert_statistics,
        trigger=CronTrigger(hour=3, minute=0),
        id='update_expert_stats',
        name='Update expert statistics',
        replace_existing=True,
    )
    
    # Add job: Cleanup old unprocessed conversations (weekly)
    _scheduler.add_job(
        cleanup_old_conversations,
        trigger=CronTrigger(day_of_week='sun', hour=4, minute=0),
        id='cleanup_conversations',
        name='Cleanup old conversations',
        replace_existing=True,
    )
    
    # Start the scheduler
    _scheduler.start()
    
    logger.info(
        "Scheduler started",
        jobs=len(_scheduler.get_jobs()),
    )


def stop_scheduler() -> None:
    """Stop the background scheduler gracefully."""
    global _scheduler
    
    if _scheduler is not None:
        logger.info("Stopping background scheduler...")
        _scheduler.shutdown(wait=True)
        _scheduler = None
        logger.info("Scheduler stopped")


async def process_pending_conversations() -> None:
    """
    Process conversations that have passed the 12-hour waiting period.
    
    This job:
    1. Fetches conversations where last_message_ts + 12h < now
    2. Analyzes each conversation to extract solutions
    3. Saves extracted solutions to the database and vector store
    """
    logger.info("Starting conversation processing job...")
    
    try:
        analyzer = ConversationAnalyzer()
        processed_count = await analyzer.process_pending_conversations()
        
        logger.info(
            "Conversation processing complete",
            processed_count=processed_count,
        )
    except Exception as e:
        logger.error("Error processing conversations", error=str(e))


async def update_expert_statistics() -> None:
    """
    Update expert statistics based on recent activity.
    
    This job:
    1. Calculates response times for experts
    2. Updates expertise areas based on solutions
    3. Refreshes availability status
    """
    logger.info("Starting expert statistics update...")
    
    try:
        # TODO: Implement expert statistics update
        # This would involve:
        # - Querying recent solutions
        # - Aggregating by user
        # - Updating expert profiles
        
        logger.info("Expert statistics update complete")
    except Exception as e:
        logger.error("Error updating expert statistics", error=str(e))


async def cleanup_old_conversations() -> None:
    """
    Clean up old unprocessed conversations.
    
    Removes conversation records that:
    - Were never processed
    - Are older than 30 days
    - Are not associated with any solution
    """
    logger.info("Starting conversation cleanup...")
    
    try:
        # TODO: Implement cleanup logic
        # This would involve:
        # - Finding old unprocessed conversations
        # - Deleting orphaned records
        
        logger.info("Conversation cleanup complete")
    except Exception as e:
        logger.error("Error cleaning up conversations", error=str(e))


def schedule_immediate_processing(channel_id: str, thread_ts: str) -> None:
    """
    Schedule immediate processing of a specific thread.
    
    Used by /cozum-ekle to bypass the 12-hour waiting period.
    
    Args:
        channel_id: Slack channel ID
        thread_ts: Thread timestamp
    """
    scheduler = get_scheduler()
    
    job_id = f"immediate_{channel_id}_{thread_ts}"
    
    scheduler.add_job(
        process_specific_thread,
        args=[channel_id, thread_ts],
        id=job_id,
        name=f"Immediate processing: {thread_ts}",
        replace_existing=True,
    )
    
    logger.info(
        "Scheduled immediate processing",
        channel_id=channel_id,
        thread_ts=thread_ts,
    )


async def process_specific_thread(channel_id: str, thread_ts: str) -> None:
    """
    Process a specific thread immediately.
    
    Args:
        channel_id: Slack channel ID
        thread_ts: Thread timestamp
    """
    logger.info(
        "Processing specific thread",
        channel_id=channel_id,
        thread_ts=thread_ts,
    )
    
    try:
        analyzer = ConversationAnalyzer()
        await analyzer.process_single_conversation(channel_id, thread_ts)
    except Exception as e:
        logger.error(
            "Error processing thread",
            channel_id=channel_id,
            thread_ts=thread_ts,
            error=str(e),
        )
