"""Base plugin interface for universal content analysis"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from ..models.video_models import YouTubeVideoRaw, EnhancedClassifiedVideo
from ..models.prompt_models import ParsedUserRequest, ContentType


class PluginCapability(str, Enum):
    """Capabilities that plugins can provide"""
    CONTENT_CLASSIFICATION = "content_classification"
    VIDEO_ANALYSIS = "video_analysis"
    TREND_ANALYSIS = "trend_analysis"
    SEARCH_OPTIMIZATION = "search_optimization"
    RECOMMENDATION = "recommendation"


@dataclass
class PluginMetadata:
    """Metadata about a content analysis plugin"""
    name: str
    version: str
    description: str
    content_types: List[ContentType]
    capabilities: List[PluginCapability]
    supported_languages: List[str]
    author: str
    min_confidence_threshold: float = 0.5
    max_videos_per_batch: int = 50


@dataclass
class AnalysisContext:
    """Context information for content analysis"""
    user_request: ParsedUserRequest
    search_keywords: List[str]
    target_audience: Optional[str] = None
    region_code: str = "US"
    language_preference: str = "korean"
    analysis_depth: str = "medium"  # basic, medium, detailed


@dataclass
class PluginResult:
    """Result from plugin analysis"""
    success: bool
    analyzed_videos: List[EnhancedClassifiedVideo]
    insights: Dict[str, Any]
    processing_time: float
    confidence_score: float
    error_message: Optional[str] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}


class BaseContentPlugin(ABC):
    """
    Abstract base class for all content analysis plugins
    
    Each plugin should implement specific analysis logic for a content type
    (e.g., dance challenges, food content, beauty tutorials, etc.)
    """
    
    def __init__(self):
        """Initialize the plugin"""
        self._metadata = self._define_metadata()
        self._initialized = False
    
    @abstractmethod
    def _define_metadata(self) -> PluginMetadata:
        """Define plugin metadata including supported content types and capabilities"""
        pass
    
    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata"""
        return self._metadata
    
    @property
    def is_initialized(self) -> bool:
        """Check if plugin is initialized"""
        return self._initialized
    
    async def initialize(self) -> bool:
        """
        Initialize the plugin (load models, setup connections, etc.)
        
        Returns:
            bool: True if initialization successful
        """
        try:
            await self._setup()
            self._initialized = True
            return True
        except Exception as e:
            print(f"Failed to initialize plugin {self.metadata.name}: {e}")
            return False
    
    async def _setup(self) -> None:
        """
        Plugin-specific setup logic
        Override this method for custom initialization
        """
        pass
    
    def can_handle(self, content_type: ContentType, user_request: ParsedUserRequest) -> float:
        """
        Check if this plugin can handle the given content type and user request
        
        Args:
            content_type: The type of content to analyze
            user_request: User's parsed request
            
        Returns:
            float: Confidence score (0.0-1.0) for handling this request
        """
        if content_type in self.metadata.content_types:
            return self._calculate_handling_confidence(user_request)
        return 0.0
    
    def _calculate_handling_confidence(self, user_request: ParsedUserRequest) -> float:
        """
        Calculate confidence score for handling a specific user request
        Override for custom confidence calculation
        
        Args:
            user_request: User's parsed request
            
        Returns:
            float: Confidence score (0.0-1.0)
        """
        # Default implementation - can be overridden
        base_confidence = 0.8
        
        # Adjust based on request specificity
        if user_request.content_filter.keywords:
            base_confidence += 0.1
        if user_request.content_filter.difficulty:
            base_confidence += 0.05
        if user_request.content_filter.participants.value != "any":
            base_confidence += 0.05
            
        return min(base_confidence, 1.0)
    
    @abstractmethod
    async def analyze_videos(
        self, 
        videos: List[YouTubeVideoRaw], 
        context: AnalysisContext
    ) -> PluginResult:
        """
        Analyze videos using plugin-specific logic
        
        Args:
            videos: List of raw YouTube videos to analyze
            context: Analysis context with user request and preferences
            
        Returns:
            PluginResult: Analysis results with enhanced video data
        """
        pass
    
    @abstractmethod
    async def generate_insights(
        self, 
        analyzed_videos: List[EnhancedClassifiedVideo],
        context: AnalysisContext
    ) -> Dict[str, Any]:
        """
        Generate content-specific insights from analyzed videos
        
        Args:
            analyzed_videos: List of analyzed videos
            context: Analysis context
            
        Returns:
            Dict[str, Any]: Content-specific insights and trends
        """
        pass
    
    async def optimize_search_keywords(
        self, 
        original_keywords: List[str], 
        context: AnalysisContext
    ) -> List[str]:
        """
        Optimize search keywords for this content type
        
        Args:
            original_keywords: Original search keywords
            context: Analysis context
            
        Returns:
            List[str]: Optimized keywords for better search results
        """
        # Default implementation - can be overridden
        return original_keywords
    
    async def recommend_related_content(
        self, 
        base_videos: List[EnhancedClassifiedVideo],
        context: AnalysisContext,
        max_recommendations: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recommend related content based on analyzed videos
        
        Args:
            base_videos: Videos to base recommendations on
            context: Analysis context
            max_recommendations: Maximum number of recommendations
            
        Returns:
            List[Dict[str, Any]]: Content recommendations
        """
        # Default implementation - can be overridden
        return []
    
    def validate_input(self, videos: List[YouTubeVideoRaw]) -> bool:
        """
        Validate input videos for this plugin
        
        Args:
            videos: Videos to validate
            
        Returns:
            bool: True if input is valid
        """
        if not videos:
            return False
        
        if len(videos) > self.metadata.max_videos_per_batch:
            return False
            
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check for the plugin
        
        Returns:
            Dict[str, Any]: Health status information
        """
        return {
            "plugin_name": self.metadata.name,
            "version": self.metadata.version,
            "initialized": self._initialized,
            "capabilities": [cap.value for cap in self.metadata.capabilities],
            "status": "healthy" if self._initialized else "not_initialized"
        }


class PluginRegistry:
    """Registry for managing content analysis plugins"""
    
    def __init__(self):
        self._plugins: Dict[str, BaseContentPlugin] = {}
        self._content_type_mapping: Dict[ContentType, List[str]] = {}
    
    def register_plugin(self, plugin: BaseContentPlugin) -> bool:
        """
        Register a new plugin
        
        Args:
            plugin: Plugin instance to register
            
        Returns:
            bool: True if registration successful
        """
        try:
            plugin_name = plugin.metadata.name
            
            if plugin_name in self._plugins:
                print(f"Warning: Plugin {plugin_name} already registered, overwriting")
            
            self._plugins[plugin_name] = plugin
            
            # Update content type mapping
            for content_type in plugin.metadata.content_types:
                if content_type not in self._content_type_mapping:
                    self._content_type_mapping[content_type] = []
                if plugin_name not in self._content_type_mapping[content_type]:
                    self._content_type_mapping[content_type].append(plugin_name)
            
            return True
            
        except Exception as e:
            print(f"Failed to register plugin: {e}")
            return False
    
    def get_plugin(self, plugin_name: str) -> Optional[BaseContentPlugin]:
        """Get plugin by name"""
        return self._plugins.get(plugin_name)
    
    def get_plugins_for_content_type(self, content_type: ContentType) -> List[BaseContentPlugin]:
        """Get all plugins that can handle a specific content type"""
        plugin_names = self._content_type_mapping.get(content_type, [])
        return [self._plugins[name] for name in plugin_names if name in self._plugins]
    
    def find_best_plugin(
        self, 
        content_type: ContentType, 
        user_request: ParsedUserRequest
    ) -> Optional[BaseContentPlugin]:
        """
        Find the best plugin for handling a specific request
        
        Args:
            content_type: Content type to handle
            user_request: User's parsed request
            
        Returns:
            Optional[BaseContentPlugin]: Best plugin or None if no suitable plugin found
        """
        candidates = self.get_plugins_for_content_type(content_type)
        
        if not candidates:
            return None
        
        # Score each plugin and select the best one
        best_plugin = None
        best_score = 0.0
        
        for plugin in candidates:
            if not plugin.is_initialized:
                continue
                
            score = plugin.can_handle(content_type, user_request)
            if score > best_score and score >= plugin.metadata.min_confidence_threshold:
                best_score = score
                best_plugin = plugin
        
        return best_plugin
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all registered plugins with their metadata"""
        return [
            {
                "name": plugin.metadata.name,
                "version": plugin.metadata.version,
                "description": plugin.metadata.description,
                "content_types": [ct.value for ct in plugin.metadata.content_types],
                "capabilities": [cap.value for cap in plugin.metadata.capabilities],
                "initialized": plugin.is_initialized
            }
            for plugin in self._plugins.values()
        ]
    
    async def initialize_all_plugins(self) -> Dict[str, bool]:
        """Initialize all registered plugins"""
        results = {}
        for name, plugin in self._plugins.items():
            if not plugin.is_initialized:
                results[name] = await plugin.initialize()
            else:
                results[name] = True
        return results


# Global plugin registry instance
plugin_registry = PluginRegistry()