"""Application configuration from environment variables."""

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ViolenceLevel(str, Enum):
    """Violence detail level for scenario output."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ModelType(str, Enum):
    """Available LLM model types."""

    # Anthropic models
    CLAUDE_OPUS = "claude-opus-4-5-20251101"
    CLAUDE_SONNET = "claude-sonnet-4-20250514"
    CLAUDE_HAIKU = "claude-haiku-3-5-20241022"

    # OpenRouter models
    GPT4O = "openai/gpt-4o"
    GPT4O_MINI = "openai/gpt-4o-mini"
    LLAMA_70B = "meta-llama/llama-3.1-70b-instruct"


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    openrouter_api_key: str = Field(default="", description="OpenRouter API key")

    # Application settings
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    session_dir: Path = Field(default=Path("./sessions"), description="Session storage directory")
    session_ttl_hours: int = Field(default=24, description="Session TTL in hours")

    # Model overrides
    moderator_model: str = Field(
        default=ModelType.CLAUDE_OPUS.value,
        description="Model for Moderator",
    )
    consilium_model: str = Field(
        default=ModelType.CLAUDE_SONNET.value,
        description="Default model for Consilium experts",
    )

    # Content settings
    default_violence_level: ViolenceLevel = Field(
        default=ViolenceLevel.MEDIUM,
        description="Default violence detail level",
    )

    @field_validator("session_dir", mode="before")
    @classmethod
    def ensure_path(cls, v: str | Path) -> Path:
        """Convert string to Path."""
        return Path(v) if isinstance(v, str) else v

    @property
    def has_anthropic_key(self) -> bool:
        """Check if Anthropic API key is configured."""
        return bool(self.anthropic_api_key and self.anthropic_api_key != "sk-ant-...")

    @property
    def has_openrouter_key(self) -> bool:
        """Check if OpenRouter API key is configured."""
        return bool(self.openrouter_api_key and self.openrouter_api_key != "sk-or-...")

    def get_model_provider(self, model: str) -> Literal["anthropic", "openrouter"]:
        """Determine which provider to use for a given model."""
        if model.startswith("claude-"):
            return "anthropic"
        return "openrouter"

    def ensure_session_dir(self) -> None:
        """Create session directory if it doesn't exist."""
        self.session_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
