"""
RecycleOps AI Assistant - Database Models

SQLAlchemy models for PostgreSQL database.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class SeverityLevel(enum.Enum):
    """Severity levels for errors."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Solution(Base):
    """
    Solutions knowledge base.
    Stores analyzed and extracted solutions from Slack conversations.
    """
    __tablename__ = "solutions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    # Error information
    error_pattern: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    error_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    error_keywords: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # Solution information
    solution_summary: Mapped[str] = mapped_column(Text, nullable=False)
    solution_text: Mapped[str] = mapped_column(Text, nullable=False)
    solution_steps: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    root_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Source tracking
    source_channel_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_thread_ts: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_message_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metadata
    created_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    machine_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Status and metrics
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    
    # Relationships
    feedbacks: Mapped[list["SolutionFeedback"]] = relationship(
        "SolutionFeedback",
        back_populates="solution",
        cascade="all, delete-orphan",
    )
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of this solution."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total
    
    def __repr__(self) -> str:
        return f"<Solution(id={self.id}, category={self.error_category})>"


class Conversation(Base):
    """
    Conversation tracking for 12-hour rule.
    Tracks Slack threads to know when to analyze them.
    """
    __tablename__ = "conversations"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    # Slack identifiers
    channel_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    thread_ts: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Message tracking
    first_message_ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_message_ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=1)
    
    # Classification
    is_error_thread: Mapped[bool] = mapped_column(Boolean, default=False)
    detected_error_pattern: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[Optional[SeverityLevel]] = mapped_column(
        SQLEnum(SeverityLevel),
        nullable=True,
    )
    
    # Processing status
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_resolved: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    process_after: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Extracted solution reference
    extracted_solution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("solutions.id"),
        nullable=True,
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    
    # Unique constraint on channel + thread
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
    
    def __repr__(self) -> str:
        return f"<Conversation(channel={self.channel_id}, thread={self.thread_ts})>"


class Expert(Base):
    """
    Expert profiles for routing.
    Tracks who has expertise in which areas.
    """
    __tablename__ = "experts"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    # Slack user info
    slack_user_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Expertise tracking
    expertise_areas: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    machine_types: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # Activity metrics
    response_count: Mapped[int] = mapped_column(Integer, default=0)
    solution_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_response_time_minutes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Availability
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    
    def __repr__(self) -> str:
        return f"<Expert(slack_id={self.slack_user_id}, name={self.display_name})>"


class SolutionFeedback(Base):
    """
    Feedback tracking for solutions.
    Records whether solutions were helpful.
    """
    __tablename__ = "solution_feedback"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    # References
    solution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("solutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Feedback
    was_helpful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    feedback_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    
    # Context
    channel_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    thread_ts: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationship
    solution: Mapped["Solution"] = relationship("Solution", back_populates="feedbacks")
    
    def __repr__(self) -> str:
        return f"<SolutionFeedback(solution={self.solution_id}, helpful={self.was_helpful})>"


class ErrorPattern(Base):
    """
    Error patterns for proactive detection.
    Stores regex patterns to identify error messages.
    """
    __tablename__ = "error_patterns"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    # Pattern definition
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    pattern_regex: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pattern_keywords: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # Classification
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    severity: Mapped[SeverityLevel] = mapped_column(
        SQLEnum(SeverityLevel),
        default=SeverityLevel.MEDIUM,
    )
    
    # Behavior
    auto_suggest: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    
    # Metadata
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    
    def __repr__(self) -> str:
        return f"<ErrorPattern(name={self.name}, severity={self.severity})>"
