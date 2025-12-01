"""
RecycleOps AI Assistant - Main Application Entry Point
"""
import signal
import sys
import time

import structlog

from src.config import settings


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
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


def main():
    """Main entry point for the application."""
    logger.info("Starting RecycleOps AI Assistant...")
    
    try:
        # Step 1: Initialize ChromaDB FIRST (before Slack)
        logger.info("Step 1/3: Initializing vector store...")
        from src.database.vector_store import init_vector_store, VectorStore
        init_vector_store()
        
        # Pre-warm the VectorStore
        vs = VectorStore()
        logger.info(f"Vector store ready: {vs.get_collection_stats()}")
        
        # Step 2: Pre-warm embeddings
        logger.info("Step 2/3: Warming up embeddings...")
        from src.rag.embeddings import embed_text
        _ = embed_text("warmup test")
        logger.info("Embeddings ready!")
        
        # Step 3: Now start Slack (after everything is ready)
        logger.info("Step 3/3: Starting Slack bot...")
        from src.slack.bot import create_slack_app, start_slack_app
        app = create_slack_app()
        
        logger.info("=" * 50)
        logger.info("RecycleOps AI Assistant is READY!")
        logger.info("You can now use /cozum-ara in Slack")
        logger.info("=" * 50)
        
        # Start Slack app (this blocks)
        start_slack_app(app)
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.exception("Fatal error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
