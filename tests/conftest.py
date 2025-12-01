"""
RecycleOps AI Assistant - Test Configuration
"""
import pytest
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def mock_slack_client():
    """Mock Slack WebClient."""
    client = MagicMock()
    client.chat_postMessage = AsyncMock()
    client.conversations_replies = AsyncMock()
    client.users_info = AsyncMock()
    return client


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    settings = MagicMock()
    settings.slack_bot_token = "xoxb-test-token"
    settings.slack_app_token = "xapp-test-token"
    settings.slack_signing_secret = "test-secret"
    settings.openai_api_key = "sk-test-key"
    settings.openai_model = "gpt-4o-mini"
    settings.openai_embedding_model = "text-embedding-3-small"
    settings.chroma_persist_directory = "./test_data/chroma"
    settings.similarity_threshold = 0.75
    settings.max_search_results = 3
    settings.learning_delay_hours = 12
    return settings


@pytest.fixture
def sample_conversation():
    """Sample Slack conversation for testing."""
    return {
        "channel": "C12345678",
        "thread_ts": "1234567890.123456",
        "messages": [
            {
                "user": "U111111",
                "text": "[DESTEK] A1100 makinesinde şişe sıkışması hatası alıyoruz",
                "ts": "1234567890.123456",
            },
            {
                "user": "U222222",
                "text": "Hangi bölgede sıkışma var?",
                "ts": "1234567891.123456",
            },
            {
                "user": "U111111",
                "text": "Besleme konveyöründe, sensör 3 yanıp sönüyor",
                "ts": "1234567892.123456",
            },
            {
                "user": "U222222",
                "text": "Anladım, bu genellikle konveyör hız ayarından kaynaklanıyor. Hızı 50'ye düşürün ve sensörü temizleyin.",
                "ts": "1234567893.123456",
            },
            {
                "user": "U111111",
                "text": "Teşekkürler, çözdük! Hız ayarı işe yaradı.",
                "ts": "1234567894.123456",
            },
        ],
    }


@pytest.fixture
def sample_solution():
    """Sample solution for testing."""
    return {
        "id": "test-solution-id",
        "error_pattern": "A1100 şişe sıkışması sensör 3",
        "error_category": "konveyör",
        "solution_text": "Konveyör hızını 50'ye düşürün ve sensörü temizleyin.",
        "solution_steps": [
            "Konveyör hızını kontrol panelinden 50'ye düşürün",
            "Sensör 3'ü temiz bir bezle silin",
            "Sistemi yeniden başlatın",
        ],
        "source_channel_id": "C12345678",
        "source_thread_ts": "1234567890.123456",
    }
