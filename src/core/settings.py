"""Application settings and configuration management"""

from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """
    Application configuration settings using Pydantic Settings.
    
    Environment variables will automatically override default values.
    """
    
    # YouTube Data API Settings
    youtube_api_key: str = Field(
        ..., 
        description="YouTube Data API key from Google Cloud Console"
    )
    
    # LLM Provider Settings
    llm_provider: str = Field(
        default="openai",
        description="LLM provider (openai, anthropic, google-generativeai)"
    )
    llm_api_key: str = Field(
        ...,
        description="API key for the selected LLM provider"
    )
    llm_model: str = Field(
        default="gpt-4o-mini",
        description="LLM model to use for classification"
    )
    
    # Google API Key (required by pydantic-ai for Google models)
    google_api_key: str = Field(
        default="",
        description="Google API key for Gemini models"
    )
    
    # Application Settings
    max_daily_quota: int = Field(
        default=8000,
        description="Maximum YouTube API quota to use per day"
    )
    rate_limit_per_second: int = Field(
        default=10,
        description="Maximum API requests per second"
    )
    
    # Development Settings
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get application settings instance.
    
    Returns:
        Settings: Application configuration settings
    """
    return settings