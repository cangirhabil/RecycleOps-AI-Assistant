"""
RecycleOps AI Assistant - Embeddings

OpenAI embeddings integration for text vectorization.
"""
from typing import Optional

from langchain_openai import OpenAIEmbeddings
import structlog

from src.config import settings


logger = structlog.get_logger(__name__)

# Singleton embeddings instance
_embeddings: Optional[OpenAIEmbeddings] = None


def get_embeddings() -> OpenAIEmbeddings:
    """
    Get the OpenAI embeddings instance.
    
    Returns:
        Configured OpenAIEmbeddings instance
    """
    global _embeddings
    
    if _embeddings is None:
        logger.info(
            "Initializing OpenAI embeddings",
            model=settings.openai_embedding_model,
        )
        
        _embeddings = OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
        )
    
    return _embeddings


async def embed_text(text: str) -> list[float]:
    """
    Embed a single text string.
    
    Args:
        text: Text to embed
        
    Returns:
        Embedding vector as list of floats
    """
    embeddings = get_embeddings()
    return await embeddings.aembed_query(text)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed multiple texts.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embedding vectors
    """
    embeddings = get_embeddings()
    return await embeddings.aembed_documents(texts)
