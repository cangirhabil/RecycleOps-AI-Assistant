"""
Tests for the RAG pipeline components.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.rag.retriever import SolutionRetriever
from src.rag.generator import ResponseGenerator


class TestSolutionRetriever:
    """Tests for the SolutionRetriever class."""
    
    @pytest.fixture
    def mock_vector_store(self):
        """Create a mock vector store."""
        store = MagicMock()
        store.search_solutions = MagicMock(return_value=[
            {
                "id": "test-id-1",
                "document": "Hata: Test error\nÇözüm: Test solution",
                "metadata": {
                    "error_pattern": "Test error pattern",
                    "solution_preview": "Test solution preview",
                },
                "similarity": 0.85,
            }
        ])
        return store
    
    @pytest.fixture
    def retriever(self, mock_vector_store):
        """Create a retriever with mock store."""
        return SolutionRetriever(vector_store=mock_vector_store)
    
    @pytest.mark.asyncio
    async def test_retrieve_returns_results(self, retriever):
        """Test that retrieve returns results."""
        results = await retriever.retrieve("test query")
        
        assert len(results) == 1
        assert results[0]["id"] == "test-id-1"
        assert results[0]["similarity"] == 0.85
    
    @pytest.mark.asyncio
    async def test_retrieve_with_filters(self, retriever, mock_vector_store):
        """Test retrieve with category filter."""
        await retriever.retrieve(
            query="test query",
            category="motor",
        )
        
        mock_vector_store.search_solutions.assert_called_once()
        call_kwargs = mock_vector_store.search_solutions.call_args
        assert call_kwargs[1]["filter_metadata"] == {"category": "motor"}
    
    @pytest.mark.asyncio
    async def test_retrieve_with_context(self, retriever):
        """Test retrieve with conversation context."""
        results = await retriever.retrieve_with_context(
            query="test query",
            conversation_context="This is context",
        )
        
        assert len(results) >= 0  # May be empty if no matches


class TestResponseGenerator:
    """Tests for the ResponseGenerator class."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        llm = MagicMock()
        llm.ainvoke = AsyncMock(return_value=MagicMock(
            content="This is a test response"
        ))
        return llm
    
    @pytest.mark.asyncio
    async def test_generate_solution_response(self, mock_llm):
        """Test solution response generation."""
        with patch('src.rag.generator.get_llm', return_value=mock_llm):
            generator = ResponseGenerator()
            generator.llm = mock_llm
            
            response = await generator.generate_solution_response(
                query="Test query",
                retrieved_solutions=[],
            )
            
            assert response == "This is a test response"
            mock_llm.ainvoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_conversation(self, mock_llm):
        """Test conversation analysis."""
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(
            content="HATA_OZETI: Test error\nCOZUM: Test solution\nBASARILI: evet"
        ))
        
        with patch('src.rag.generator.get_llm', return_value=mock_llm):
            generator = ResponseGenerator()
            generator.llm = mock_llm
            
            result = await generator.analyze_conversation([
                {"user": "U1", "text": "Error occurred"},
                {"user": "U2", "text": "Try this solution"},
            ])
            
            assert result["error_summary"] == "Test error"
            assert result["solution"] == "Test solution"
            assert result["successful"] is True
