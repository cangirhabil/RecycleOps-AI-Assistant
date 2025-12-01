"""
RecycleOps AI Assistant - RAG Chain

Orchestrates the complete RAG (Retrieval Augmented Generation) pipeline.
"""
from typing import Optional
from dataclasses import dataclass

import structlog

from src.config import settings
from src.rag.retriever import SolutionRetriever, get_solution_retriever
from src.rag.generator import ResponseGenerator, get_generator


logger = structlog.get_logger(__name__)


@dataclass
class RAGResponse:
    """Response from the RAG pipeline."""
    answer: str
    sources: list[dict]
    confidence: float
    has_solutions: bool
    
    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "sources": self.sources,
            "confidence": self.confidence,
            "has_solutions": self.has_solutions,
        }


class RAGChain:
    """
    Complete RAG pipeline that combines retrieval and generation.
    
    This class orchestrates:
    1. Retrieving relevant documents from ChromaDB
    2. Generating responses using the LLM
    3. Combining and formatting the final output
    """
    
    def __init__(
        self,
        retriever: Optional[SolutionRetriever] = None,
        generator: Optional[ResponseGenerator] = None,
    ):
        """
        Initialize the RAG chain.
        
        Args:
            retriever: Optional retriever instance
            generator: Optional generator instance
        """
        self.retriever = retriever or get_solution_retriever()
        self.generator = generator or get_generator()
    
    def query(
        self,
        question: str,
        n_results: int = 3,
        min_similarity: float = 0.0,
        category: Optional[str] = None,
        machine_type: Optional[str] = None,
        conversation_context: Optional[str] = None,
    ) -> RAGResponse:
        """
        Execute the full RAG pipeline.
        
        Args:
            question: User's question/query
            n_results: Maximum number of documents to retrieve
            min_similarity: Minimum similarity threshold
            category: Optional category filter
            machine_type: Optional machine type filter
            conversation_context: Optional additional context
            
        Returns:
            RAGResponse with answer and sources
        """
        logger.info(
            "Executing RAG query",
            question=question[:100],
            n_results=n_results,
        )
        
        # Step 1: Retrieve relevant documents
        if conversation_context:
            retrieved_docs = self.retriever.retrieve_with_context(
                query=question,
                conversation_context=conversation_context,
                n_results=n_results,
            )
        else:
            retrieved_docs = self.retriever.retrieve(
                query=question,
                n_results=n_results,
                min_similarity=min_similarity,
                category=category,
                machine_type=machine_type,
            )
        
        # Calculate average confidence
        if retrieved_docs:
            avg_confidence = sum(d.get("similarity", 0) for d in retrieved_docs) / len(retrieved_docs)
        else:
            avg_confidence = 0.0
        
        # Step 2: Generate response
        answer = self.generator.generate_solution_response(
            query=question,
            retrieved_solutions=retrieved_docs,
            conversation_context=conversation_context,
        )
        
        # Step 3: Format sources
        sources = []
        for doc in retrieved_docs:
            sources.append({
                "id": doc.get("id"),
                "similarity": doc.get("similarity", 0),
                "error_pattern": doc.get("metadata", {}).get("error_pattern", ""),
                "solution_preview": doc.get("metadata", {}).get("solution_preview", ""),
                "category": doc.get("metadata", {}).get("category"),
                "machine_type": doc.get("metadata", {}).get("machine_type"),
            })
        
        response = RAGResponse(
            answer=answer,
            sources=sources,
            confidence=avg_confidence,
            has_solutions=len(retrieved_docs) > 0,
        )
        
        logger.info(
            "RAG query completed",
            sources_count=len(sources),
            confidence=avg_confidence,
            has_solutions=response.has_solutions,
        )
        
        return response
    
    def analyze_thread(
        self,
        messages: list[dict],
    ) -> dict:
        """
        Analyze a conversation thread to extract solution.
        
        Args:
            messages: List of Slack messages
            
        Returns:
            Extracted solution information
        """
        return self.generator.analyze_conversation(messages)
    
    def get_proactive_suggestion(
        self,
        error_text: str,
        min_similarity: float = 0.7,
    ) -> Optional[str]:
        """
        Get a proactive suggestion for a new error.
        
        Args:
            error_text: The error message
            min_similarity: Minimum similarity for suggestions
            
        Returns:
            Suggestion message or None if no good match
        """
        # Retrieve similar solutions
        similar_solutions = self.retriever.retrieve(
            query=error_text,
            n_results=3,
            min_similarity=min_similarity,
        )
        
        if not similar_solutions:
            logger.debug("No similar solutions found for proactive suggestion")
            return None
        
        # Generate suggestion
        suggestion = self.generator.generate_proactive_suggestion(
            error_text=error_text,
            similar_solutions=similar_solutions,
        )
        
        return suggestion if suggestion else None


def get_rag_chain() -> RAGChain:
    """Get a RAGChain instance."""
    return RAGChain()
