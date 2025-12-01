"""
RecycleOps AI Assistant - Main Application Entry Point
"""
import asyncio
import signal
import sys
from typing import NoReturn

import structlog

from src.config import settings
from src.slack.bot import create_slack_app, start_slack_app
from src.database.connection import init_database
from src.database.vector_store import init_vector_store
from src.learning.scheduler import start_scheduler, stop_scheduler


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.log_format == "json" 
        else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


async def startup() -> None:
    """Initialize all application components."""
    logger.info("Starting RecycleOps AI Assistant...")
    
    # Initialize database
    logger.info("Initializing database connection...")
    await init_database()
    
    # Initialize vector store
    logger.info("Initializing vector store...")
    init_vector_store()
    
    # Start background scheduler for 12-hour rule
    logger.info("Starting background scheduler...")
    start_scheduler()
    
    logger.info("Startup complete!")


async def shutdown() -> None:
    """Gracefully shutdown all components."""
    logger.info("Shutting down RecycleOps AI Assistant...")
    
    # Stop scheduler
    stop_scheduler()
    
    logger.info("Shutdown complete!")


def main() -> NoReturn:
    """Main entry point for the application."""
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(shutdown())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Run startup tasks
        asyncio.run(startup())
        
        # Create and start Slack app
        app = create_slack_app()
        
        logger.info(
            "RecycleOps AI Assistant is running!",
            monitored_channels=settings.monitor_channel_ids,
        )
        
        # Start Slack app (this blocks)
        start_slack_app(app)
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        asyncio.run(shutdown())
    except Exception as e:
        logger.exception("Fatal error occurred", error=str(e))
        asyncio.run(shutdown())
        sys.exit(1)


if __name__ == "__main__":
    main()
