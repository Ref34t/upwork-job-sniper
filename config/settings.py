"""Application settings and configuration."""
import os
from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application settings
    APP_NAME: str = Field(default="Upwork Job Sniper")
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")
    
    # Upwork API settings
    UPWORK_API_KEY: str
    UPWORK_API_SECRET: str
    UPWORK_ACCESS_TOKEN: str
    UPWORK_ACCESS_TOKEN_REFRESH: str
    UPWORK_ORGANIZATION_ID: str
    
    # API Endpoints
    UPWORK_GRAPHQL_ENDPOINT: str = "https://api.upwork.com/graphql"
    
    # OpenAI API settings
    OPENAI_API_KEY: SecretStr
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    OPENAI_TEMPERATURE: float = Field(default=0.3)
    OPENAI_MAX_TOKENS: int = Field(default=1000)
    
    # Pushover settings
    PUSHOVER_API_TOKEN: Optional[str] = None
    PUSHOVER_USER_KEY: Optional[str] = None
    
    # Application settings
    MAX_RETRIES: int = 3
    
    # Search parameters
    SEARCH_QUERY: str = "wordpress"
    HOURLY_RATE_MIN: int = 30
    BUDGET_MIN: int = 500
    SEARCH_LIMIT: int = 10
    
    # AI analysis settings
    ENABLE_AI_ANALYSIS: bool = Field(default=True)
    MIN_NOTIFICATION_SCORE: int = Field(default=7)
    
    # File paths
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        env_nested_delimiter="__",
        extra="ignore"
    )

    @validator("DATA_DIR", "LOGS_DIR", pre=True)
    def create_dirs(cls, v: Path) -> Path:
        """Create directories if they don't exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v


# Create settings instance
settings = Settings()

# Create necessary directories
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
