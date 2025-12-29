"""Application configuration using pydantic-settings."""
from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # AI Provider Configuration
    ai_provider: Literal["claude", "openai", "gemini", "deepseek"] = "gemini"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    gemini_api_key: str = ""

    # Model Selection
    claude_model: str = "claude-sonnet-4-5-20251205"
    openai_model: str = "gpt-4o"
    deepseek_model: str = "deepseek-chat"
    gemini_model: str = "gemini-2.5-flash"

    # Provider strategy
    # Options:
    # - "gemini" for both (FREE! 1,500 req/day) - RECOMMENDED FOR PROTOTYPING
    # - "claude" + "deepseek" for production (best quality + cheap narration)
    use_dual_provider: bool = False
    analysis_provider: Literal["claude", "openai", "deepseek", "gemini"] = "gemini"
    narration_provider: Literal["claude", "openai", "deepseek", "gemini"] = "gemini"

    # Server Configuration
    max_file_size_mb: int = 50
    session_ttl_hours: int = 2
    max_concurrent_requests: int = 5

    # CORS
    frontend_url: str = "http://localhost:3000"

    # TTS Configuration
    google_tts_credentials_path: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
