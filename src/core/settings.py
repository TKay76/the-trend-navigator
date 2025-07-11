"""Application settings and configuration management"""

import os
from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment-specific .env file
environment = os.getenv('ENVIRONMENT', 'development')
env_file = f'.env.{environment}'
if os.path.exists(env_file):
    load_dotenv(env_file)
else:
    load_dotenv()  # Fallback to .env


class Settings(BaseSettings):
    """
    Application configuration settings using Pydantic Settings.
    
    Environment variables will automatically override default values.
    """
    
    # YouTube Data API Settings
    youtube_api_key: str = Field(
        default="your_youtube_api_key_here",
        alias="YOUTUBE_API_KEY",
        description="YouTube Data API key from Google Cloud Console"
    )
    
    # LLM Provider Settings
    llm_provider: str = Field(
        default="openai",
        alias="LLM_PROVIDER",
        description="LLM provider (openai, anthropic, google-generativeai)"
    )
    llm_api_key: str = Field(
        default="your_llm_api_key_here",
        alias="LLM_API_KEY",
        description="API key for the selected LLM provider"
    )
    llm_model: str = Field(
        default="gpt-4o-mini",
        alias="LLM_MODEL",
        description="LLM model to use for classification"
    )
    
    # Google API Key (required by pydantic-ai for Google models)
    google_api_key: str = Field(
        default="",
        alias="GOOGLE_API_KEY",
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
    use_mock_llm: bool = Field(
        default=False,
        alias="USE_MOCK_LLM",
        description="Use mock LLM provider instead of real API calls (for testing/development)"
    )
    
    # Environment and Runtime Settings
    environment: str = Field(
        default="development",
        description="Runtime environment (development, staging, production)"
    )
    
    # Circuit Breaker Settings
    circuit_breaker_failure_threshold: int = Field(
        default=5,
        description="Number of failures before circuit breaker opens"
    )
    circuit_breaker_recovery_timeout: int = Field(
        default=60,
        description="Seconds to wait before attempting recovery"
    )
    circuit_breaker_expected_exception_ratio: float = Field(
        default=0.3,
        description="Expected exception ratio for circuit breaker"
    )
    
    # Cache Settings
    enable_cache: bool = Field(
        default=True,
        description="Enable caching for API responses"
    )
    cache_ttl: int = Field(
        default=1800,
        description="Cache time-to-live in seconds"
    )
    redis_url: Optional[str] = Field(
        default=None,
        alias="REDIS_URL",
        description="Redis connection URL for caching"
    )
    
    # Security Settings
    secret_key: Optional[str] = Field(
        default=None,
        description="Secret key for security features"
    )
    allowed_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        description="Allowed hosts for the application"
    )
    
    # Database Settings (for future use)
    database_url: Optional[str] = Field(
        default=None,
        description="Database connection URL"
    )
    
    # Monitoring Settings
    sentry_dsn: Optional[str] = Field(
        default=None,
        description="Sentry DSN for error tracking"
    )
    enable_metrics: bool = Field(
        default=False,
        description="Enable metrics collection"
    )
    
    # Real-time Monitoring Settings
    monitoring_enabled: bool = Field(
        default=False,
        alias="MONITORING_ENABLED",
        description="Enable real-time trend monitoring"
    )
    monitoring_interval_minutes: int = Field(
        default=60,
        alias="MONITORING_INTERVAL_MINUTES",
        description="Monitoring interval in minutes"
    )
    trend_detection_threshold: float = Field(
        default=5.0,
        alias="TREND_DETECTION_THRESHOLD",
        description="Trend detection threshold (multiplier for growth rate)"
    )
    viral_threshold: int = Field(
        default=100000,
        alias="VIRAL_THRESHOLD",
        description="View count threshold for viral content detection"
    )
    
    # Notification Settings
    email_notifications_enabled: bool = Field(
        default=False,
        alias="EMAIL_NOTIFICATIONS_ENABLED",
        description="Enable email notifications"
    )
    smtp_server: str = Field(
        default="smtp.gmail.com",
        alias="SMTP_SERVER",
        description="SMTP server for email notifications"
    )
    smtp_port: int = Field(
        default=587,
        alias="SMTP_PORT",
        description="SMTP server port"
    )
    smtp_username: Optional[str] = Field(
        default=None,
        alias="SMTP_USERNAME",
        description="SMTP username"
    )
    smtp_password: Optional[str] = Field(
        default=None,
        alias="SMTP_PASSWORD",
        description="SMTP password"
    )
    notification_email: Optional[str] = Field(
        default=None,
        alias="NOTIFICATION_EMAIL",
        description="Email address for notifications"
    )
    slack_webhook_url: Optional[str] = Field(
        default=None,
        alias="SLACK_WEBHOOK_URL",
        description="Slack webhook URL for notifications"
    )
    discord_webhook_url: Optional[str] = Field(
        default=None,
        alias="DISCORD_WEBHOOK_URL",
        description="Discord webhook URL for notifications"
    )
    
    @field_validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level is one of the standard levels"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level must be one of {valid_levels}')
        return v.upper()
    
    @field_validator('llm_provider')
    def validate_llm_provider(cls, v):
        """Validate LLM provider is supported"""
        valid_providers = ['openai', 'anthropic', 'google-generativeai']
        if v not in valid_providers:
            raise ValueError(f'llm_provider must be one of {valid_providers}')
        return v
    
    @field_validator('environment')
    def validate_environment(cls, v):
        """Validate environment is recognized"""
        valid_envs = ['development', 'staging', 'production']
        if v not in valid_envs:
            raise ValueError(f'environment must be one of {valid_envs}')
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment == 'development'
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment == 'production'
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "env_prefix": "",
        "extra": "ignore"
    }


# Global settings instance
_settings = None


def get_settings() -> Settings:
    """
    Get application settings instance.
    
    Returns:
        Settings: Application configuration settings
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

def reload_settings() -> Settings:
    """
    Force reload of settings from environment variables.
    
    Returns:
        Settings: Fresh application configuration settings
    """
    global _settings
    _settings = None
    return get_settings()