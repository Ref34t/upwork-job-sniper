"""Application configuration settings."""
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseSettings, Field, validator
from pydantic.types import SecretStr


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    APP_NAME: str = "Upwork Job Sniper"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Upwork API
    UPWORK_API_KEY: str
    UPWORK_API_SECRET: str
    UPWORK_ACCESS_TOKEN: Optional[str] = None
    UPWORK_ACCESS_TOKEN_SECRET: Optional[str] = None
    
    # OpenAI
    OPENAI_API_KEY: SecretStr
    
    # Pushover
    PUSHOVER_API_TOKEN: Optional[str] = None
    PUSHOVER_USER_KEY: Optional[str] = None
    
    # Application Settings
    POLLING_INTERVAL: int = 300  # 5 minutes in seconds
    MAX_RETRIES: int = 3
    
    # File Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
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
