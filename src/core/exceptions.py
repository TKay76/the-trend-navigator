"""Custom exceptions for the YouTube Shorts trend analysis system"""


class YouTubeTrendAnalysisError(Exception):
    """Base exception for YouTube trend analysis system"""
    pass


class YouTubeAPIError(YouTubeTrendAnalysisError):
    """Exception raised for YouTube Data API errors"""
    pass


class QuotaExceededError(YouTubeAPIError):
    """Exception raised when YouTube API quota is exceeded"""
    pass


class LLMProviderError(YouTubeTrendAnalysisError):
    """Exception raised for LLM provider errors"""
    pass


class ClassificationError(LLMProviderError):
    """Exception raised during video classification"""
    pass


class ValidationError(YouTubeTrendAnalysisError):
    """Exception raised for data validation errors"""
    pass


class ConfigurationError(YouTubeTrendAnalysisError):
    """Exception raised for configuration errors"""
    pass


class RateLimitError(YouTubeAPIError):
    """Exception raised when rate limits are exceeded"""
    pass