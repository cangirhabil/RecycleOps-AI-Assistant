"""
RecycleOps AI Assistant - Conversation Service

Service for conversation tracking and processing.
"""
from datetime import datetime
from typing import Optional

import structlog

from src.config import settings
from src.database.connection import get_async_session
from src.database.repositories import ConversationRepository, SolutionRepository
from src.database.models import SeverityLevel
from src.learning.analyzer import ConversationAnalyzer


logger = structlog.get_logger(__name__)


class ConversationService:
    """
    Service for conversation-related operations.
    
    Handles:
    - Tracking new messages and conversations
    - Managing the 12-hour learning rule
    - Processing conversations for solution extraction
    """
    
    def __init__(self):
        self.analyzer = ConversationAnalyzer()
    
    async def track_message(
        self,
        channel_id: str,
        thread_ts: str,
        message_ts: str,
        user_id: str,
        text: str,
    ) -> None:
        """
        Track a message in a conversation.
        
        This is called for every message to:
        1. Create or update conversation record
        2. Detect if it's an error thread
        3. Reset the 12-hour processing timer
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            message_ts: Message timestamp
            user_id: Author's user ID
            text: Message text
        """
        from src.slack.events import is_error_message, extract_error_info
        
        # Check if this looks like an error
        is_error = is_error_message(text)
        error_info = extract_error_info(text) if is_error else {}
        
        # Determine severity (simple heuristic)
        severity = None
        if is_error:
            text_lower = text.lower()
            if any(w in text_lower for w in ["acil", "kritik", "durdu", "üretim"]):
                severity = SeverityLevel.CRITICAL
            elif any(w in text_lower for w in ["önemli", "hata"]):
                severity = SeverityLevel.HIGH
            else:
                severity = SeverityLevel.MEDIUM
        
        # Convert message_ts to datetime
        try:
            ts_float = float(message_ts)
            msg_datetime = datetime.fromtimestamp(ts_float)
        except (ValueError, TypeError):
            msg_datetime = datetime.utcnow()
        
        async with get_async_session() as session:
            conv_repo = ConversationRepository(session)
            
            await conv_repo.create_or_update(
                channel_id=channel_id,
                thread_ts=thread_ts,
                message_ts=msg_datetime,
                is_error_thread=is_error,
                detected_error_pattern=error_info.get("error_type"),
                severity=severity,
            )
            
            await session.commit()
        
        logger.debug(
            "Message tracked",
            channel_id=channel_id,
            thread_ts=thread_ts,
            is_error=is_error,
        )
    
    async def analyze_and_save_solution(
        self,
        channel_id: str,
        thread_ts: str,
        messages: list[dict],
        added_by: str,
        force: bool = False,
    ):
        """
        Analyze a conversation and save the extracted solution.
        
        Used by /cozum-ekle for immediate solution extraction.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            messages: List of Slack messages
            added_by: User who triggered the save
            force: Bypass 12-hour rule
            
        Returns:
            Created Solution or None
        """
        from src.rag.generator import get_generator
        from src.learning.extractor import SolutionExtractor
        from src.database.vector_store import get_vector_store
        
        if len(messages) < 2:
            logger.info("Not enough messages to extract solution")
            return None
        
        # Analyze conversation
        generator = get_generator()
        analysis = await generator.analyze_conversation(messages)
        
        if not analysis.get("error_summary") or not analysis.get("solution"):
            logger.info("Could not extract solution from conversation")
            return None
        
        # Extract structured data
        extractor = SolutionExtractor()
        solution_data = extractor.extract_solution_data(
            messages=messages,
            analysis=analysis,
            channel_id=channel_id,
            thread_ts=thread_ts,
        )
        
        # Save to database
        async with get_async_session() as session:
            solution_repo = SolutionRepository(session)
            conv_repo = ConversationRepository(session)
            
            solution = await solution_repo.create(
                error_pattern=solution_data["error_pattern"],
                solution_summary=solution_data["solution_summary"],
                solution_text=solution_data["solution_text"],
                error_category=solution_data.get("category"),
                error_keywords=solution_data.get("keywords"),
                solution_steps=solution_data.get("steps"),
                root_cause=solution_data.get("root_cause"),
                source_channel_id=channel_id,
                source_thread_ts=thread_ts,
                created_by=added_by,
                machine_type=solution_data.get("machine_type"),
            )
            
            # Save to vector store
            vector_store = get_vector_store()
            vector_store.add_solution(
                solution_id=str(solution.id),
                error_pattern=solution_data["error_pattern"],
                solution_text=solution_data["solution_text"],
                metadata={
                    "category": solution_data.get("category"),
                    "machine_type": solution_data.get("machine_type"),
                },
            )
            
            # Mark conversation as processed
            conversation = await conv_repo.get_by_thread(channel_id, thread_ts)
            if conversation:
                await conv_repo.mark_as_processed(
                    conversation_id=conversation.id,
                    solution_id=solution.id,
                    is_resolved=analysis.get("successful", True),
                )
            
            await session.commit()
            
            logger.info(
                "Solution saved via /cozum-ekle",
                solution_id=str(solution.id),
                added_by=added_by,
            )
            
            return solution
