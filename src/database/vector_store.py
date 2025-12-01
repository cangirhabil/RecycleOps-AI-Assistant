"""
RecycleOps AI Assistant - Vector Store

ChromaDB integration for semantic search and solution retrieval.
Uses Google Gemini embeddings.
"""
from typing import Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
import structlog

from src.config import settings
from src.rag.embeddings import get_embeddings, embed_text


logger = structlog.get_logger(__name__)

# Global ChromaDB client and collections
_chroma_client: Optional[chromadb.PersistentClient] = None
_solutions_collection = None
_conversations_collection = None


def init_vector_store() -> None:
    """Initialize ChromaDB client and collections."""
    global _chroma_client, _solutions_collection, _conversations_collection
    
    logger.info("Initializing ChromaDB (in-memory)...")
    
    # Create ChromaDB client (in-memory for stability)
    _chroma_client = chromadb.Client(
        settings=ChromaSettings(
            anonymized_telemetry=False,
            allow_reset=True,
        ),
    )
    
    # Create or get solutions collection (we'll embed manually with Gemini)
    _solutions_collection = _chroma_client.get_or_create_collection(
        name="solutions",
        metadata={
            "description": "Solution embeddings for error pattern matching",
            "hnsw:space": "cosine",
        },
    )
    
    # Create or get conversations collection
    _conversations_collection = _chroma_client.get_or_create_collection(
        name="conversations",
        metadata={
            "description": "Conversation embeddings for context retrieval",
            "hnsw:space": "cosine",
        },
    )
    
    logger.info(
        "ChromaDB initialized successfully",
        solutions_count=_solutions_collection.count(),
        conversations_count=_conversations_collection.count(),
    )


def get_solutions_collection():
    """Get the solutions collection."""
    if _solutions_collection is None:
        raise RuntimeError("Vector store not initialized. Call init_vector_store() first.")
    return _solutions_collection


def get_conversations_collection():
    """Get the conversations collection."""
    if _conversations_collection is None:
        raise RuntimeError("Vector store not initialized. Call init_vector_store() first.")
    return _conversations_collection


class VectorStore:
    """High-level interface for vector store operations."""
    
    _initialized = False
    
    def __init__(self):
        # Use class-level flag to avoid re-initialization
        if not VectorStore._initialized:
            if _solutions_collection is None:
                init_vector_store()
            VectorStore._initialized = True
        self.solutions = get_solutions_collection()
        self.conversations = get_conversations_collection()
    
    def add_solution(
        self,
        solution_id: str,
        error_pattern: str,
        solution_text: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Add a solution to the vector store.
        
        Args:
            solution_id: Unique identifier for the solution
            error_pattern: The error pattern/description to embed
            solution_text: The solution text
            metadata: Additional metadata to store
        """
        # Combine error pattern and solution for richer embeddings
        combined_text = f"Hata: {error_pattern}\n\nÇözüm: {solution_text}"
        
        # Get embedding from Gemini
        embedding = embed_text(combined_text)
        
        # Prepare metadata
        meta = metadata or {}
        meta.update({
            "error_pattern": error_pattern[:500],
            "solution_preview": solution_text[:500],
        })
        
        self.solutions.add(
            ids=[solution_id],
            embeddings=[embedding],
            documents=[combined_text],
            metadatas=[meta],
        )
        
        logger.info(
            "Added solution to vector store",
            solution_id=solution_id,
        )
    
    def update_solution(
        self,
        solution_id: str,
        error_pattern: str,
        solution_text: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Update an existing solution in the vector store."""
        combined_text = f"Hata: {error_pattern}\n\nÇözüm: {solution_text}"
        
        # Get embedding from Gemini
        embedding = embed_text(combined_text)
        
        meta = metadata or {}
        meta.update({
            "error_pattern": error_pattern[:500],
            "solution_preview": solution_text[:500],
        })
        
        self.solutions.update(
            ids=[solution_id],
            embeddings=[embedding],
            documents=[combined_text],
            metadatas=[meta],
        )
        
        logger.info(
            "Updated solution in vector store",
            solution_id=solution_id,
        )
    
    def delete_solution(self, solution_id: str) -> None:
        """Delete a solution from the vector store."""
        self.solutions.delete(ids=[solution_id])
        logger.info("Deleted solution from vector store", solution_id=solution_id)
    
    def search_solutions(
        self,
        query: str,
        n_results: int = 3,
        min_similarity: float = 0.0,
        filter_metadata: Optional[dict] = None,
    ) -> list[dict]:
        """
        Search for similar solutions.
        
        Args:
            query: The search query (error description)
            n_results: Maximum number of results to return
            min_similarity: Minimum similarity score (0-1, higher is more similar)
            filter_metadata: Optional metadata filters
            
        Returns:
            List of matching solutions with scores
        """
        # Get query embedding from Gemini
        query_embedding = embed_text(query)
        
        results = self.solutions.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata,
            include=["documents", "metadatas", "distances"],
        )
        
        # Process results
        solutions = []
        if results and results["ids"] and results["ids"][0]:
            for i, solution_id in enumerate(results["ids"][0]):
                # ChromaDB returns distances, convert to similarity
                # For cosine distance: similarity = 1 - distance
                distance = results["distances"][0][i] if results["distances"] else 0
                similarity = 1 - distance
                
                if similarity >= min_similarity:
                    solutions.append({
                        "id": solution_id,
                        "document": results["documents"][0][i] if results["documents"] else "",
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "similarity": similarity,
                    })
        
        logger.debug(
            "Solution search completed",
            query=query[:100],
            results_count=len(solutions),
        )
        
        return solutions
    
    def add_conversation(
        self,
        conversation_id: str,
        conversation_text: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Add a conversation to the vector store."""
        # Get embedding from Gemini
        embedding = embed_text(conversation_text)
        
        meta = metadata or {}
        meta["preview"] = conversation_text[:500]
        
        self.conversations.add(
            ids=[conversation_id],
            embeddings=[embedding],
            documents=[conversation_text],
            metadatas=[meta],
        )
        
        logger.info(
            "Added conversation to vector store",
            conversation_id=conversation_id,
        )
    
    def search_conversations(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[dict] = None,
    ) -> list[dict]:
        """Search for similar conversations."""
        # Get query embedding from Gemini
        query_embedding = embed_text(query)
        
        results = self.conversations.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata,
            include=["documents", "metadatas", "distances"],
        )
        
        conversations = []
        if results and results["ids"] and results["ids"][0]:
            for i, conv_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                similarity = 1 - distance
                
                conversations.append({
                    "id": conv_id,
                    "document": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "similarity": similarity,
                })
        
        return conversations
    
    def get_collection_stats(self) -> dict:
        """Get statistics about the vector store collections."""
        return {
            "solutions_count": self.solutions.count(),
            "conversations_count": self.conversations.count(),
        }


def get_vector_store() -> VectorStore:
    """Get a VectorStore instance."""
    return VectorStore()
