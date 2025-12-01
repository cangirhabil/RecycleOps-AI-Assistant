"""
RecycleOps AI Assistant - Database Repositories

Data access layer for database operations.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.database.models import (
    Solution,
    Conversation,
    Expert,
    SolutionFeedback,
    ErrorPattern,
    SeverityLevel,
)


logger = structlog.get_logger(__name__)


class SolutionRepository:
    """Repository for Solution operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        error_pattern: str,
        solution_summary: str,
        solution_text: str,
        error_category: Optional[str] = None,
        error_keywords: Optional[list[str]] = None,
        solution_steps: Optional[dict] = None,
        root_cause: Optional[str] = None,
        source_channel_id: Optional[str] = None,
        source_thread_ts: Optional[str] = None,
        created_by: Optional[str] = None,
        machine_type: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Solution:
        """Create a new solution."""
        solution = Solution(
            error_pattern=error_pattern,
            solution_summary=solution_summary,
            solution_text=solution_text,
            error_category=error_category,
            error_keywords=error_keywords,
            solution_steps=solution_steps,
            root_cause=root_cause,
            source_channel_id=source_channel_id,
            source_thread_ts=source_thread_ts,
            created_by=created_by,
            machine_type=machine_type,
            location=location,
        )
        self.session.add(solution)
        await self.session.flush()
        
        logger.info(
            "Created new solution",
            solution_id=str(solution.id),
            category=error_category,
        )
        return solution
    
    async def get_by_id(self, solution_id: uuid.UUID) -> Optional[Solution]:
        """Get a solution by ID."""
        result = await self.session.execute(
            select(Solution).where(Solution.id == solution_id)
        )
        return result.scalar_one_or_none()
    
    async def search_by_category(
        self,
        category: str,
        limit: int = 10,
    ) -> list[Solution]:
        """Search solutions by category."""
        result = await self.session.execute(
            select(Solution)
            .where(Solution.error_category == category)
            .order_by(Solution.success_count.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def search_by_keywords(
        self,
        keywords: list[str],
        limit: int = 10,
    ) -> list[Solution]:
        """Search solutions by keywords."""
        # Use PostgreSQL array overlap operator
        result = await self.session.execute(
            select(Solution)
            .where(Solution.error_keywords.overlap(keywords))
            .order_by(Solution.success_count.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def update_success_count(
        self,
        solution_id: uuid.UUID,
        was_successful: bool,
    ) -> None:
        """Update success/failure count for a solution."""
        if was_successful:
            await self.session.execute(
                update(Solution)
                .where(Solution.id == solution_id)
                .values(success_count=Solution.success_count + 1)
            )
        else:
            await self.session.execute(
                update(Solution)
                .where(Solution.id == solution_id)
                .values(failure_count=Solution.failure_count + 1)
            )
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> list[Solution]:
        """Get all solutions with pagination."""
        result = await self.session.execute(
            select(Solution)
            .order_by(Solution.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())


class ConversationRepository:
    """Repository for Conversation operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_or_update(
        self,
        channel_id: str,
        thread_ts: str,
        message_ts: datetime,
        is_error_thread: bool = False,
        detected_error_pattern: Optional[str] = None,
        severity: Optional[SeverityLevel] = None,
    ) -> Conversation:
        """Create or update a conversation record."""
        # Check if conversation exists
        result = await self.session.execute(
            select(Conversation).where(
                and_(
                    Conversation.channel_id == channel_id,
                    Conversation.thread_ts == thread_ts,
                )
            )
        )
        conversation = result.scalar_one_or_none()
        
        if conversation:
            # Update existing conversation
            conversation.last_message_ts = message_ts
            conversation.message_count += 1
            if is_error_thread:
                conversation.is_error_thread = True
            if detected_error_pattern:
                conversation.detected_error_pattern = detected_error_pattern
            if severity:
                conversation.severity = severity
            # Reset process_after time (12-hour rule)
            conversation.process_after = message_ts + timedelta(hours=12)
            conversation.is_processed = False
        else:
            # Create new conversation
            conversation = Conversation(
                channel_id=channel_id,
                thread_ts=thread_ts,
                first_message_ts=message_ts,
                last_message_ts=message_ts,
                message_count=1,
                is_error_thread=is_error_thread,
                detected_error_pattern=detected_error_pattern,
                severity=severity,
                process_after=message_ts + timedelta(hours=12),
            )
            self.session.add(conversation)
        
        await self.session.flush()
        return conversation
    
    async def get_pending_for_processing(
        self,
        limit: int = 50,
    ) -> list[Conversation]:
        """Get conversations that are ready to be processed (12 hours passed)."""
        now = datetime.utcnow()
        result = await self.session.execute(
            select(Conversation)
            .where(
                and_(
                    Conversation.is_processed == False,
                    Conversation.is_error_thread == True,
                    Conversation.process_after <= now,
                )
            )
            .order_by(Conversation.process_after)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def mark_as_processed(
        self,
        conversation_id: uuid.UUID,
        solution_id: Optional[uuid.UUID] = None,
        is_resolved: bool = True,
    ) -> None:
        """Mark a conversation as processed."""
        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(
                is_processed=True,
                processed_at=datetime.utcnow(),
                extracted_solution_id=solution_id,
                is_resolved=is_resolved,
            )
        )
    
    async def get_by_thread(
        self,
        channel_id: str,
        thread_ts: str,
    ) -> Optional[Conversation]:
        """Get a conversation by channel and thread."""
        result = await self.session.execute(
            select(Conversation).where(
                and_(
                    Conversation.channel_id == channel_id,
                    Conversation.thread_ts == thread_ts,
                )
            )
        )
        return result.scalar_one_or_none()


class ExpertRepository:
    """Repository for Expert operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_or_update(
        self,
        slack_user_id: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Expert:
        """Create or update an expert profile."""
        result = await self.session.execute(
            select(Expert).where(Expert.slack_user_id == slack_user_id)
        )
        expert = result.scalar_one_or_none()
        
        if expert:
            if display_name:
                expert.display_name = display_name
            if email:
                expert.email = email
            expert.last_active_at = datetime.utcnow()
        else:
            expert = Expert(
                slack_user_id=slack_user_id,
                display_name=display_name,
                email=email,
                last_active_at=datetime.utcnow(),
            )
            self.session.add(expert)
        
        await self.session.flush()
        return expert
    
    async def increment_response_count(self, slack_user_id: str) -> None:
        """Increment the response count for an expert."""
        await self.session.execute(
            update(Expert)
            .where(Expert.slack_user_id == slack_user_id)
            .values(
                response_count=Expert.response_count + 1,
                last_active_at=datetime.utcnow(),
            )
        )
    
    async def increment_solution_count(self, slack_user_id: str) -> None:
        """Increment the solution count for an expert."""
        await self.session.execute(
            update(Expert)
            .where(Expert.slack_user_id == slack_user_id)
            .values(
                solution_count=Expert.solution_count + 1,
                last_active_at=datetime.utcnow(),
            )
        )
    
    async def update_expertise(
        self,
        slack_user_id: str,
        expertise_areas: list[str],
        machine_types: Optional[list[str]] = None,
    ) -> None:
        """Update expertise areas for an expert."""
        await self.session.execute(
            update(Expert)
            .where(Expert.slack_user_id == slack_user_id)
            .values(
                expertise_areas=expertise_areas,
                machine_types=machine_types,
            )
        )
    
    async def find_by_expertise(
        self,
        expertise_area: str,
        limit: int = 3,
    ) -> list[Expert]:
        """Find experts by expertise area."""
        result = await self.session.execute(
            select(Expert)
            .where(
                and_(
                    Expert.expertise_areas.contains([expertise_area]),
                    Expert.is_available == True,
                )
            )
            .order_by(Expert.solution_count.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def find_by_machine_type(
        self,
        machine_type: str,
        limit: int = 3,
    ) -> list[Expert]:
        """Find experts by machine type."""
        result = await self.session.execute(
            select(Expert)
            .where(
                and_(
                    Expert.machine_types.contains([machine_type]),
                    Expert.is_available == True,
                )
            )
            .order_by(Expert.solution_count.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_top_experts(self, limit: int = 5) -> list[Expert]:
        """Get top experts by solution count."""
        result = await self.session.execute(
            select(Expert)
            .where(Expert.is_available == True)
            .order_by(Expert.solution_count.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class SolutionFeedbackRepository:
    """Repository for SolutionFeedback operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        solution_id: uuid.UUID,
        user_id: str,
        was_helpful: bool,
        feedback_text: Optional[str] = None,
        rating: Optional[int] = None,
        channel_id: Optional[str] = None,
        thread_ts: Optional[str] = None,
    ) -> SolutionFeedback:
        """Create a new feedback entry."""
        feedback = SolutionFeedback(
            solution_id=solution_id,
            user_id=user_id,
            was_helpful=was_helpful,
            feedback_text=feedback_text,
            rating=rating,
            channel_id=channel_id,
            thread_ts=thread_ts,
        )
        self.session.add(feedback)
        await self.session.flush()
        
        logger.info(
            "Created solution feedback",
            solution_id=str(solution_id),
            was_helpful=was_helpful,
        )
        return feedback
    
    async def get_feedback_stats(
        self,
        solution_id: uuid.UUID,
    ) -> dict:
        """Get feedback statistics for a solution."""
        result = await self.session.execute(
            select(
                func.count(SolutionFeedback.id).label("total"),
                func.sum(
                    func.cast(SolutionFeedback.was_helpful, Integer)
                ).label("helpful"),
                func.avg(SolutionFeedback.rating).label("avg_rating"),
            ).where(SolutionFeedback.solution_id == solution_id)
        )
        row = result.one()
        return {
            "total": row.total or 0,
            "helpful": row.helpful or 0,
            "avg_rating": float(row.avg_rating) if row.avg_rating else None,
        }


class ErrorPatternRepository:
    """Repository for ErrorPattern operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        name: str,
        pattern_regex: Optional[str] = None,
        pattern_keywords: Optional[list[str]] = None,
        category: Optional[str] = None,
        severity: SeverityLevel = SeverityLevel.MEDIUM,
        description: Optional[str] = None,
    ) -> ErrorPattern:
        """Create a new error pattern."""
        pattern = ErrorPattern(
            name=name,
            pattern_regex=pattern_regex,
            pattern_keywords=pattern_keywords,
            category=category,
            severity=severity,
            description=description,
        )
        self.session.add(pattern)
        await self.session.flush()
        return pattern
    
    async def get_active_patterns(self) -> list[ErrorPattern]:
        """Get all active error patterns."""
        result = await self.session.execute(
            select(ErrorPattern)
            .where(ErrorPattern.is_active == True)
            .order_by(ErrorPattern.priority.desc())
        )
        return list(result.scalars().all())
    
    async def get_by_category(self, category: str) -> list[ErrorPattern]:
        """Get error patterns by category."""
        result = await self.session.execute(
            select(ErrorPattern)
            .where(
                and_(
                    ErrorPattern.category == category,
                    ErrorPattern.is_active == True,
                )
            )
        )
        return list(result.scalars().all())
