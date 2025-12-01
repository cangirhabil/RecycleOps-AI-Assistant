"""
RecycleOps AI Assistant - Conversation Analyzer

Analyzes Slack conversations to extract problem-solution pairs.
"""
from datetime import datetime
from typing import Optional
import asyncio

from slack_sdk import WebClient
import structlog

from src.config import settings
from src.database.connection import get_async_session
from src.database.repositories import (
    ConversationRepository,
    SolutionRepository,
    ExpertRepository,
)
from src.database.vector_store import get_vector_store
from src.rag.generator import get_generator
from src.learning.extractor import SolutionExtractor


logger = structlog.get_logger(__name__)


class ConversationAnalyzer:
    """
    Analyzes Slack conversations to extract and save solutions.
    
    This class handles the "learning" aspect of the system:
    1. Fetches pending conversations from the database
    2. Retrieves full thread content from Slack
    3. Uses LLM to analyze and extract solutions
    4. Saves solutions to PostgreSQL and ChromaDB
    """
    
    def __init__(self, slack_client: Optional[WebClient] = None):
        """
        Initialize the analyzer.
        
        Args:
            slack_client: Optional Slack WebClient instance
        """
        if slack_client:
            self.slack_client = slack_client
        else:
            self.slack_client = WebClient(token=settings.slack_bot_token)
        
        self.extractor = SolutionExtractor()
        self.generator = get_generator()
    
    async def process_pending_conversations(self) -> int:
        """
        Process all conversations that have passed the 12-hour waiting period.
        
        Returns:
            Number of conversations processed
        """
        processed_count = 0
        
        async with get_async_session() as session:
            conv_repo = ConversationRepository(session)
            
            # Get pending conversations
            pending = await conv_repo.get_pending_for_processing(limit=50)
            
            logger.info(f"Found {len(pending)} conversations pending processing")
            
            for conversation in pending:
                try:
                    success = await self._process_conversation(
                        session=session,
                        channel_id=conversation.channel_id,
                        thread_ts=conversation.thread_ts,
                        conversation_id=conversation.id,
                    )
                    
                    if success:
                        processed_count += 1
                        
                except Exception as e:
                    logger.error(
                        "Failed to process conversation",
                        conversation_id=str(conversation.id),
                        error=str(e),
                    )
                    continue
            
            await session.commit()
        
        return processed_count
    
    async def process_single_conversation(
        self,
        channel_id: str,
        thread_ts: str,
    ) -> Optional[dict]:
        """
        Process a single conversation immediately.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            
        Returns:
            Extracted solution dict or None
        """
        async with get_async_session() as session:
            conv_repo = ConversationRepository(session)
            
            # Get or create conversation record
            conversation = await conv_repo.get_by_thread(channel_id, thread_ts)
            
            if conversation:
                success = await self._process_conversation(
                    session=session,
                    channel_id=channel_id,
                    thread_ts=thread_ts,
                    conversation_id=conversation.id,
                )
                await session.commit()
                return {"success": success}
            else:
                logger.warning(
                    "Conversation not found",
                    channel_id=channel_id,
                    thread_ts=thread_ts,
                )
                return None
    
    async def _process_conversation(
        self,
        session,
        channel_id: str,
        thread_ts: str,
        conversation_id,
    ) -> bool:
        """
        Internal method to process a single conversation.
        
        Args:
            session: Database session
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            conversation_id: Database conversation ID
            
        Returns:
            True if solution was extracted and saved
        """
        logger.info(
            "Processing conversation",
            channel_id=channel_id,
            thread_ts=thread_ts,
        )
        
        # Fetch messages from Slack
        try:
            messages = await self._fetch_thread_messages(channel_id, thread_ts)
        except Exception as e:
            logger.error("Failed to fetch thread messages", error=str(e))
            return False
        
        if len(messages) < 2:
            logger.info("Thread too short to analyze", message_count=len(messages))
            # Mark as processed but with no solution
            conv_repo = ConversationRepository(session)
            await conv_repo.mark_as_processed(
                conversation_id=conversation_id,
                is_resolved=False,
            )
            return False
        
        # Analyze conversation
        analysis = await self.generator.analyze_conversation(messages)
        
        if not analysis.get("error_summary") or not analysis.get("solution"):
            logger.info("Could not extract solution from conversation")
            conv_repo = ConversationRepository(session)
            await conv_repo.mark_as_processed(
                conversation_id=conversation_id,
                is_resolved=False,
            )
            return False
        
        # Extract solution details
        solution_data = self.extractor.extract_solution_data(
            messages=messages,
            analysis=analysis,
            channel_id=channel_id,
            thread_ts=thread_ts,
        )
        
        # Save to PostgreSQL
        solution_repo = SolutionRepository(session)
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
            created_by=solution_data.get("resolver_user_id"),
            machine_type=solution_data.get("machine_type"),
        )
        
        # Save to ChromaDB
        vector_store = get_vector_store()
        vector_store.add_solution(
            solution_id=str(solution.id),
            error_pattern=solution_data["error_pattern"],
            solution_text=solution_data["solution_text"],
            metadata={
                "category": solution_data.get("category"),
                "machine_type": solution_data.get("machine_type"),
                "success_rate": 1.0 if analysis.get("successful") else 0.5,
            },
        )
        
        # Update conversation as processed
        conv_repo = ConversationRepository(session)
        await conv_repo.mark_as_processed(
            conversation_id=conversation_id,
            solution_id=solution.id,
            is_resolved=analysis.get("successful", True),
        )
        
        # Update expert statistics
        if solution_data.get("resolver_user_id"):
            expert_repo = ExpertRepository(session)
            await expert_repo.create_or_update(
                slack_user_id=solution_data["resolver_user_id"],
            )
            await expert_repo.increment_solution_count(
                slack_user_id=solution_data["resolver_user_id"],
            )
            
            # Update expertise areas
            if solution_data.get("category"):
                expert = await expert_repo.create_or_update(
                    slack_user_id=solution_data["resolver_user_id"],
                )
                current_areas = expert.expertise_areas or []
                if solution_data["category"] not in current_areas:
                    current_areas.append(solution_data["category"])
                    await expert_repo.update_expertise(
                        slack_user_id=solution_data["resolver_user_id"],
                        expertise_areas=current_areas,
                    )
        
        logger.info(
            "Solution extracted and saved",
            solution_id=str(solution.id),
            category=solution_data.get("category"),
        )
        
        return True
    
    async def _fetch_thread_messages(
        self,
        channel_id: str,
        thread_ts: str,
    ) -> list[dict]:
        """
        Fetch all messages from a Slack thread.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            
        Returns:
            List of message dicts
        """
        result = await asyncio.to_thread(
            self.slack_client.conversations_replies,
            channel=channel_id,
            ts=thread_ts,
            limit=100,
        )
        
        messages = result.get("messages", [])
        
        # Filter out bot messages and system messages
        filtered_messages = [
            msg for msg in messages
            if not msg.get("bot_id") and msg.get("text")
        ]
        
        return filtered_messages
