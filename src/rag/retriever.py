"""
RecycleOps AI Assistant - Retriever

Document retrieval from ChromaDB vector store.
"""
from typing import Optional

import structlog

from src.config import settings
from src.database.vector_store import get_vector_store, VectorStore


logger = structlog.get_logger(__name__)


class SolutionRetriever:
    """
    Retriever for solution documents from ChromaDB.
    
    Handles semantic search and filtering of solutions based on
    user queries and optional metadata filters.
    """
    
    def __init__(self, vector_store: Optional[VectorStore] = None):
        """
        Initialize the retriever.
        
        Args:
            vector_store: Optional VectorStore instance. If not provided,
                         a new one will be created.
        """
        self.vector_store = vector_store or get_vector_store()
    
    async def retrieve(
        self,
        query: str,
        n_results: int = 3,
        min_similarity: float = 0.0,
        category: Optional[str] = None,
        machine_type: Optional[str] = None,
    ) -> list[dict]:
        """
        Retrieve similar solutions for a query.
        
        Args:
            query: The search query (error description)
            n_results: Maximum number of results
            min_similarity: Minimum similarity score (0-1)
            category: Optional category filter
            machine_type: Optional machine type filter
            
        Returns:
            List of matching solutions with metadata
        """
        # Build metadata filter
        filter_dict = None
        if category or machine_type:
            filter_dict = {}
            if category:
                filter_dict["category"] = category
            if machine_type:
                filter_dict["machine_type"] = machine_type
        
        # Search vector store
        results = self.vector_store.search_solutions(
            query=query,
            n_results=n_results,
            min_similarity=min_similarity,
            filter_metadata=filter_dict,
        )
        
        logger.info(
            "Solutions retrieved",
            query=query[:100],
            results_count=len(results),
            min_similarity=min_similarity,
        )
        
        return results
    
    async def retrieve_by_error_pattern(
        self,
        error_pattern: str,
        n_results: int = 5,
    ) -> list[dict]:
        """
        Retrieve solutions specifically matching an error pattern.
        
        This method is optimized for finding exact or near-exact
        matches to known error patterns.
        
        Args:
            error_pattern: The error pattern to match
            n_results: Maximum number of results
            
        Returns:
            List of matching solutions
        """
        # Use a higher similarity threshold for pattern matching
        return await self.retrieve(
            query=error_pattern,
            n_results=n_results,
            min_similarity=settings.similarity_threshold,
        )
    
    async def retrieve_with_context(
        self,
        query: str,
        conversation_context: str,
        n_results: int = 3,
    ) -> list[dict]:
        """
        Retrieve solutions using both query and conversation context.
        
        This method combines the immediate query with additional
        conversation context for better retrieval accuracy.
        
        Args:
            query: The primary search query
            conversation_context: Additional context from the conversation
            n_results: Maximum number of results
            
        Returns:
            List of matching solutions
        """
        # Combine query and context
        combined_query = f"{query}\n\nBağlam:\n{conversation_context[:500]}"
        
        return await self.retrieve(
            query=combined_query,
            n_results=n_results,
            min_similarity=settings.similarity_threshold * 0.8,  # Slightly lower threshold
        )


class ConversationRetriever:
    """
    Retriever for past conversations from ChromaDB.
    
    Used to find similar past discussions for context.
    """
    
    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vector_store = vector_store or get_vector_store()
    
    async def retrieve_similar_conversations(
        self,
        query: str,
        n_results: int = 5,
    ) -> list[dict]:
        """
        Find similar past conversations.
        
        Args:
            query: Search query or conversation snippet
            n_results: Maximum number of results
            
        Returns:
            List of similar conversations
        """
        return self.vector_store.search_conversations(
            query=query,
            n_results=n_results,
        )


def get_solution_retriever() -> SolutionRetriever:
    """Get a SolutionRetriever instance."""
    return SolutionRetriever()


def get_conversation_retriever() -> ConversationRetriever:
    """Get a ConversationRetriever instance."""
    return ConversationRetriever()
