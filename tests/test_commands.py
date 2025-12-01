"""
Tests for Slack command handlers.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestSearchCommand:
    """Tests for the /search command."""
    
    @pytest.mark.asyncio
    async def test_search_empty_query(self):
        """Test search with empty query."""
        from src.slack.commands import handle_search_command
        
        ack = AsyncMock()
        respond = AsyncMock()
        command = {"text": "", "user_id": "U123", "channel_id": "C123"}
        client = MagicMock()
        
        await handle_search_command(ack, respond, command, client)
        
        ack.assert_called_once()
        respond.assert_called()
        call_args = respond.call_args
        assert "Lütfen" in call_args[1]["text"]
    
    @pytest.mark.asyncio
    async def test_search_with_query(self):
        """Test search with valid query."""
        from src.slack.commands import handle_search_command
        
        ack = AsyncMock()
        respond = AsyncMock()
        command = {
            "text": "motor hatası",
            "user_id": "U123",
            "channel_id": "C123",
        }
        client = MagicMock()
        
        # Mock the solution service
        with patch('src.slack.commands.SolutionService') as MockService:
            mock_service = MockService.return_value
            mock_service.search_solutions = AsyncMock(return_value=[])
            
            await handle_search_command(ack, respond, command, client)
            
            ack.assert_called_once()
            assert respond.call_count >= 1


class TestFormatSearchResults:
    """Tests for search result formatting."""
    
    def test_format_empty_results(self):
        """Test formatting empty results."""
        from src.slack.commands import format_search_results
        
        blocks = format_search_results("test query", [])
        
        assert len(blocks) > 0
        assert blocks[0]["type"] == "header"
    
    def test_format_with_results(self):
        """Test formatting results."""
        from src.slack.commands import format_search_results
        
        results = [
            {
                "error_pattern": "Test error",
                "solution_summary": "Test solution",
                "similarity": 0.85,
            }
        ]
        
        blocks = format_search_results("test query", results)
        
        assert len(blocks) > 0
        # Should have header, context, divider, result section
        assert any(b["type"] == "section" for b in blocks)


class TestCozumGetirCommand:
    """Tests for the /cozum-getir command."""
    
    @pytest.mark.asyncio
    async def test_cozum_getir_response(self):
        """Test cozum-getir shows usage instructions."""
        from src.slack.commands import handle_cozum_getir_command
        
        ack = AsyncMock()
        respond = AsyncMock()
        command = {"user_id": "U123", "channel_id": "C123"}
        client = MagicMock()
        
        await handle_cozum_getir_command(ack, respond, command, client)
        
        ack.assert_called_once()
        respond.assert_called_once()
        call_args = respond.call_args
        assert "thread" in call_args[1]["text"].lower()


class TestCozumEkleCommand:
    """Tests for the /cozum-ekle command."""
    
    @pytest.mark.asyncio
    async def test_cozum_ekle_response(self):
        """Test cozum-ekle shows usage instructions."""
        from src.slack.commands import handle_cozum_ekle_command
        
        ack = AsyncMock()
        respond = AsyncMock()
        command = {"user_id": "U123", "channel_id": "C123"}
        client = MagicMock()
        
        await handle_cozum_ekle_command(ack, respond, command, client)
        
        ack.assert_called_once()
        respond.assert_called_once()
        call_args = respond.call_args
        assert "thread" in call_args[1]["text"].lower()
