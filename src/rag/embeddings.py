"""
RecycleOps AI Assistant - Embeddings

Google Gemini embeddings integration for text vectorization.
"""
from typing import Optional

from langchain_google_genai import GoogleGenerativeAIEmbeddings
import structlog

from src.config import settings


logger = structlog.get_logger(__name__)

# Singleton embeddings instance
_embeddings: Optional[GoogleGenerativeAIEmbeddings] = None


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """
    Get the Google Gemini embeddings instance.
    
    Returns:
        Configured GoogleGenerativeAIEmbeddings instance
    """
    global _embeddings
    
    if _embeddings is None:
        logger.info(
            "Initializing Google Gemini embeddings",
            model=settings.gemini_embedding_model,
        )
        
        _embeddings = GoogleGenerativeAIEmbeddings(
            google_api_key=settings.google_api_key,
            model=settings.gemini_embedding_model,
        )
    
    return _embeddings


def embed_text(text: str) -> list[float]:
    """
    Embed a single text string.
    
    Args:
        text: Text to embed
        
    Returns:
        Embedding vector as list of floats
    """
    embeddings = get_embeddings()
    return embeddings.embed_query(text)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed multiple texts.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embedding vectors
    """
    embeddings = get_embeddings()
    return embeddings.embed_documents(texts)
