"""Application configuration from environment variables."""

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ViolenceLevel(str, Enum):
    """Violence detail level for scenario output."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ModelProvider(str, Enum):
    """LLM provider types."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OPENROUTER = "openrouter"


class ModelType(str, Enum):
    """Available LLM model types."""

    # Anthropic models
    CLAUDE_OPUS = "claude-opus-4-5-20251101"
    CLAUDE_SONNET = "claude-sonnet-4-20250514"
    CLAUDE_HAIKU = "claude-haiku-3-5-20241022"

    # OpenAI models
    GPT_5_2 = "gpt-5.2"

    # OpenRouter models (provider prefix required)
    DEEPSEEK_V3 = "deepseek/deepseek-v3.2"
    GEMINI_3_PRO = "google/gemini-3-pro-preview"
    LLAMA_70B = "meta-llama/llama-3.3-70b-instruct"


class ModelConfig(BaseModel):
    """Configuration for a model assignment."""

    provider: ModelProvider
    model_id: str


# =============================================================================
# Model Assignments
# =============================================================================

MODEL_ASSIGNMENTS: dict[str, ModelConfig] = {
    # Consilium experts
    "strategist": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-sonnet-4-20250514",
    ),
    "tactician": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-sonnet-4-20250514",
    ),
    "logistician": ModelConfig(
        provider=ModelProvider.OPENROUTER,
        model_id="deepseek/deepseek-v3.2",
    ),
    "geographer": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-sonnet-4-20250514",
    ),
    "armorer": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-sonnet-4-20250514",
    ),
    "surgeon": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-sonnet-4-20250514",
    ),
    "commander": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-sonnet-4-20250514",
    ),
    "chronicler": ModelConfig(
        provider=ModelProvider.OPENROUTER,
        model_id="google/gemini-3-pro-preview",
    ),
    "herald": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-sonnet-4-20250514",
    ),
    # Red Team experts
    "auditor": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_id="gpt-5.2",
    ),
    "skeptic": ModelConfig(
        provider=ModelProvider.OPENROUTER,
        model_id="deepseek/deepseek-v3.2",
    ),
    "adversary": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-sonnet-4-20250514",
    ),
    "realist": ModelConfig(
        provider=ModelProvider.OPENROUTER,
        model_id="meta-llama/llama-3.3-70b-instruct",
    ),
    "dramatist": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_id="gpt-5.2",
    ),
    # Moderator
    "moderator": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-opus-4-5-20251101",
    ),
}


# =============================================================================
# Settings
# =============================================================================


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
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openrouter_api_key: str = Field(default="", description="OpenRouter API key")

    # Application settings
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    session_dir: Path = Field(
        default=Path("./sessions"), description="Session storage directory"
    )
    session_ttl_hours: int = Field(default=24, description="Session TTL in hours")

    # Deliberation settings
    max_rounds: int = Field(default=3, description="Maximum deliberation rounds")

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
        return bool(
            self.anthropic_api_key and self.anthropic_api_key != "sk-ant-..."
        )

    @property
    def has_openai_key(self) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(self.openai_api_key and self.openai_api_key != "sk-...")

    @property
    def has_openrouter_key(self) -> bool:
        """Check if OpenRouter API key is configured."""
        return bool(
            self.openrouter_api_key and self.openrouter_api_key != "sk-or-..."
        )

    def get_model_provider(self, model: str) -> ModelProvider:
        """Determine which provider to use for a given model."""
        # Check if model starts with a provider prefix
        if "/" in model:
            # OpenRouter format: provider/model
            return ModelProvider.OPENROUTER

        # Check for GPT models
        if model.startswith("gpt-"):
            return ModelProvider.OPENAI

        # Check for Claude models
        if model.startswith("claude-"):
            return ModelProvider.ANTHROPIC

        # Default to OpenRouter for unknown models
        return ModelProvider.OPENROUTER

    def ensure_session_dir(self) -> None:
        """Create session directory if it doesn't exist."""
        self.session_dir.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Singleton
# =============================================================================


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset settings (for testing)."""
    global _settings
    _settings = None
