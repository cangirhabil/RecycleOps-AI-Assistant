"""
RecycleOps AI Assistant - Configuration Module
"""
import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # --- Slack Configuration ---
    slack_bot_token: str = Field(..., description="Slack Bot Token (xoxb-...)")
    slack_app_token: str = Field(..., description="Slack App Token (xapp-...)")
    slack_signing_secret: str = Field(..., description="Slack Signing Secret")
    slack_monitor_channels: str = Field(
        default="",
        description="Comma-separated channel IDs to monitor"
    )
    
    @property
    def monitor_channel_ids(self) -> list[str]:
        """Parse monitor channels into a list."""
        if not self.slack_monitor_channels:
            return []
        return [ch.strip() for ch in self.slack_monitor_channels.split(",") if ch.strip()]
    
    # --- Google Gemini Configuration ---
    google_api_key: str = Field(..., description="Google AI API Key")
    gemini_model: str = Field(default="gemini-2.5-flash", description="Gemini Model for generation")
    gemini_embedding_model: str = Field(
        default="models/text-embedding-004",
        description="Gemini Model for embeddings"
    )
    
    # --- PostgreSQL Configuration ---
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="recycleops")
    postgres_user: str = Field(default="recycleops")
    postgres_password: str = Field(default="")
    database_url: Optional[str] = Field(default=None)
    
    @property
    def db_url(self) -> str:
        """Get database URL, constructing if not provided."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def async_db_url(self) -> str:
        """Get async database URL for asyncpg."""
        base_url = self.db_url
        if base_url.startswith("postgresql://"):
            return base_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return base_url
    
    # --- ChromaDB Configuration ---
    chroma_persist_directory: str = Field(default="./data/chroma")
    chroma_collection_name: str = Field(default="solutions")
    
    # --- Application Settings ---
    learning_delay_hours: int = Field(
        default=12,
        description="Hours to wait before analyzing a conversation"
    )
    similarity_threshold: float = Field(
        default=0.75,
        description="Minimum similarity score for solution matching (0.0 - 1.0)"
    )
    max_search_results: int = Field(
        default=3,
        description="Maximum number of solutions to return in search"
    )
    proactive_support_enabled: bool = Field(
        default=True,
        description="Enable automatic solution suggestions for new errors"
    )
    
    # --- Logging ---
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience alias
settings = get_settings()
