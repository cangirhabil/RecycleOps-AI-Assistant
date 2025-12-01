"""
RecycleOps AI Assistant - Database Connection

Database connection management and session handling.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
import structlog

from src.config import settings
from src.database.models import Base


logger = structlog.get_logger(__name__)

# Async engine for async operations
async_engine = None
async_session_factory = None

# Sync engine for migrations and simple operations
sync_engine = None
sync_session_factory = None


async def init_database() -> None:
    """Initialize database connection and create tables."""
    global async_engine, async_session_factory, sync_engine, sync_session_factory
    
    logger.info("Initializing database...", db_url=settings.db_url.split("@")[-1])
    
    # Create async engine
    async_engine = create_async_engine(
        settings.async_db_url,
        echo=settings.log_level == "DEBUG",
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    
    # Create async session factory
    async_session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    # Create sync engine for migrations
    sync_engine = create_engine(
        settings.db_url,
        echo=settings.log_level == "DEBUG",
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    
    sync_session_factory = sessionmaker(
        bind=sync_engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    # Create tables if they don't exist
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialized successfully")


async def close_database() -> None:
    """Close database connections."""
    global async_engine, sync_engine
    
    if async_engine:
        await async_engine.dispose()
        async_engine = None
    
    if sync_engine:
        sync_engine.dispose()
        sync_engine = None
    
    logger.info("Database connections closed")


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session."""
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def get_sync_session() -> Session:
    """Get a sync database session."""
    if sync_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    return sync_session_factory()
