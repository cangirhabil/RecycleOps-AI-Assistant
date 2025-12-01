"""
RecycleOps AI Assistant - Solution Service

Core business logic for solution search and management.
"""
import uuid
from typing import Optional

import structlog

from src.config import settings
from src.database.connection import get_async_session
from src.database.repositories import SolutionRepository
from src.database.vector_store import get_vector_store
from src.rag.chain import get_rag_chain


logger = structlog.get_logger(__name__)


class SolutionService:
    """
    Service for solution-related operations.
    
    Provides high-level methods for:
    - Searching solutions
    - Adding new solutions
    - Updating solution metrics
    """
    
    def __init__(self):
        self.rag_chain = get_rag_chain()
        self.vector_store = get_vector_store()
    
    def search_solutions(
        self,
        query: str,
        max_results: int = 3,
        min_similarity: float = 0.0,
        category: Optional[str] = None,
        machine_type: Optional[str] = None,
    ) -> list[dict]:
        """
        Search for solutions matching a query.
        
        Args:
            query: Search query (error description)
            max_results: Maximum number of results
            min_similarity: Minimum similarity threshold
            category: Optional category filter
            machine_type: Optional machine type filter
            
        Returns:
            List of matching solutions
        """
        # Use RAG chain for intelligent search
        rag_response = self.rag_chain.query(
            question=query,
            n_results=max_results,
            min_similarity=min_similarity,
            category=category,
            machine_type=machine_type,
        )
        
        # Return sources directly for now (skip DB enrichment to simplify)
        results = []
        for source in rag_response.sources:
            results.append({
                "id": source.get("id"),
                "similarity": source.get("similarity", 0),
                "error_pattern": source.get("error_pattern", ""),
                "solution_summary": source.get("solution_preview", ""),
                "category": source.get("category"),
                "machine_type": source.get("machine_type"),
            })
        
        logger.info(
            "Solution search completed",
            query=query[:50],
            results_count=len(results),
        )
        
        return results
    
    async def get_solution_by_id(self, solution_id: str) -> Optional[dict]:
        """
        Get a specific solution by ID.
        
        Args:
            solution_id: Solution UUID
            
        Returns:
            Solution dict or None
        """
        async with get_async_session() as session:
            solution_repo = SolutionRepository(session)
            
            try:
                uid = uuid.UUID(solution_id)
                solution = await solution_repo.get_by_id(uid)
                
                if solution:
                    return {
                        "id": str(solution.id),
                        "error_pattern": solution.error_pattern,
                        "error_category": solution.error_category,
                        "solution_summary": solution.solution_summary,
                        "solution_text": solution.solution_text,
                        "solution_steps": solution.solution_steps,
                        "root_cause": solution.root_cause,
                        "machine_type": solution.machine_type,
                        "success_rate": solution.success_rate,
                        "verified": solution.verified,
                        "created_at": solution.created_at.isoformat(),
                    }
            except ValueError:
                logger.warning(f"Invalid solution ID: {solution_id}")
        
        return None
    
    async def record_solution_feedback(
        self,
        solution_id: str,
        user_id: str,
        was_helpful: bool,
    ) -> bool:
        """
        Record user feedback on a solution.
        
        Args:
            solution_id: Solution UUID
            user_id: Slack user ID
            was_helpful: Whether the solution was helpful
            
        Returns:
            True if feedback was recorded
        """
        async with get_async_session() as session:
            solution_repo = SolutionRepository(session)
            
            try:
                uid = uuid.UUID(solution_id)
                await solution_repo.update_success_count(uid, was_helpful)
                await session.commit()
                
                logger.info(
                    "Solution feedback recorded",
                    solution_id=solution_id,
                    was_helpful=was_helpful,
                )
                return True
            except Exception as e:
                logger.error(f"Failed to record feedback: {e}")
                return False
    
    async def add_solution(
        self,
        error_pattern: str,
        solution_text: str,
        created_by: str,
        **kwargs,
    ) -> Optional[str]:
        """
        Add a new solution to the knowledge base.
        
        Args:
            error_pattern: Error description
            solution_text: Solution description
            created_by: Slack user ID
            **kwargs: Additional solution fields
            
        Returns:
            Solution ID or None
        """
        async with get_async_session() as session:
            solution_repo = SolutionRepository(session)
            
            try:
                solution = await solution_repo.create(
                    error_pattern=error_pattern,
                    solution_summary=kwargs.get("summary", error_pattern[:200]),
                    solution_text=solution_text,
                    error_category=kwargs.get("category"),
                    error_keywords=kwargs.get("keywords"),
                    solution_steps=kwargs.get("steps"),
                    root_cause=kwargs.get("root_cause"),
                    source_channel_id=kwargs.get("channel_id"),
                    source_thread_ts=kwargs.get("thread_ts"),
                    created_by=created_by,
                    machine_type=kwargs.get("machine_type"),
                )
                
                # Add to vector store
                self.vector_store.add_solution(
                    solution_id=str(solution.id),
                    error_pattern=error_pattern,
                    solution_text=solution_text,
                    metadata={
                        "category": kwargs.get("category"),
                        "machine_type": kwargs.get("machine_type"),
                    },
                )
                
                await session.commit()
                
                logger.info(
                    "Solution added",
                    solution_id=str(solution.id),
                    created_by=created_by,
                )
                
                return str(solution.id)
                
            except Exception as e:
                logger.error(f"Failed to add solution: {e}")
                return None
