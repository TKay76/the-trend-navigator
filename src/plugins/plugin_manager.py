"""Plugin management system for universal content analysis"""

import asyncio
import logging
import importlib
import inspect
from typing import List, Dict, Any, Optional, Type
from pathlib import Path
from datetime import datetime

from .base_plugin import (
    BaseContentPlugin, PluginRegistry, AnalysisContext, 
    PluginResult, plugin_registry
)
from ..models.video_models import YouTubeVideoRaw, EnhancedClassifiedVideo
from ..models.prompt_models import ParsedUserRequest, ContentType
from ..core.exceptions import ClassificationError

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Centralized manager for content analysis plugins
    
    Handles plugin discovery, loading, routing, and execution
    """
    
    def __init__(self, registry: Optional[PluginRegistry] = None):
        """
        Initialize plugin manager
        
        Args:
            registry: Plugin registry to use (defaults to global registry)
        """
        self.registry = registry or plugin_registry
        self.plugin_discovery_paths = [
            Path(__file__).parent / "content_plugins"
        ]
        self._load_stats = {
            "plugins_discovered": 0,
            "plugins_loaded": 0,
            "plugins_failed": 0,
            "last_discovery": None
        }
        logger.info("PluginManager initialized")
    
    async def discover_and_load_plugins(self) -> Dict[str, Any]:
        """
        Discover and load all available plugins
        
        Returns:
            Dict[str, Any]: Discovery and loading results
        """
        logger.info("Starting plugin discovery and loading...")
        start_time = datetime.now()
        
        # Reset stats
        self._load_stats = {
            "plugins_discovered": 0,
            "plugins_loaded": 0,
            "plugins_failed": 0,
            "last_discovery": start_time
        }
        
        discovered_plugins = []
        
        # Discover plugins in all configured paths
        for discovery_path in self.plugin_discovery_paths:
            if discovery_path.exists():
                discovered_plugins.extend(self._discover_plugins_in_path(discovery_path))
        
        self._load_stats["plugins_discovered"] = len(discovered_plugins)
        logger.info(f"Discovered {len(discovered_plugins)} plugin classes")
        
        # Load and register discovered plugins
        loading_results = {}
        for plugin_class in discovered_plugins:
            try:
                plugin_instance = plugin_class()
                success = self.registry.register_plugin(plugin_instance)
                
                if success:
                    self._load_stats["plugins_loaded"] += 1
                    loading_results[plugin_instance.metadata.name] = {
                        "status": "registered",
                        "initialized": False
                    }
                    logger.info(f"Registered plugin: {plugin_instance.metadata.name}")
                else:
                    self._load_stats["plugins_failed"] += 1
                    loading_results[plugin_class.__name__] = {
                        "status": "registration_failed",
                        "error": "Failed to register plugin"
                    }
                    
            except Exception as e:
                self._load_stats["plugins_failed"] += 1
                loading_results[plugin_class.__name__] = {
                    "status": "instantiation_failed",
                    "error": str(e)
                }
                logger.error(f"Failed to instantiate plugin {plugin_class.__name__}: {e}")
        
        # Initialize all loaded plugins
        logger.info("Initializing plugins...")
        init_results = await self.registry.initialize_all_plugins()
        
        # Update loading results with initialization status
        for plugin_name, init_success in init_results.items():
            if plugin_name in loading_results:
                loading_results[plugin_name]["initialized"] = init_success
                if init_success:
                    loading_results[plugin_name]["status"] = "ready"
                else:
                    loading_results[plugin_name]["status"] = "initialization_failed"
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        summary = {
            "summary": self._load_stats.copy(),
            "processing_time": processing_time,
            "plugins": loading_results
        }
        
        logger.info(
            f"Plugin loading completed: {self._load_stats['plugins_loaded']} loaded, "
            f"{self._load_stats['plugins_failed']} failed in {processing_time:.2f}s"
        )
        
        return summary
    
    def _discover_plugins_in_path(self, path: Path) -> List[Type[BaseContentPlugin]]:
        """
        Discover plugin classes in a specific path
        
        Args:
            path: Path to search for plugins
            
        Returns:
            List[Type[BaseContentPlugin]]: Discovered plugin classes
        """
        plugin_classes = []
        
        if not path.exists():
            logger.warning(f"Plugin discovery path does not exist: {path}")
            return plugin_classes
        
        # Look for Python files in the directory
        for py_file in path.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            
            try:
                # Import the module
                module_name = f"src.plugins.content_plugins.{py_file.stem}"
                module = importlib.import_module(module_name)
                
                # Find plugin classes in the module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Check if it's a subclass of BaseContentPlugin but not the base class itself
                    if (issubclass(obj, BaseContentPlugin) and 
                        obj is not BaseContentPlugin and
                        not inspect.isabstract(obj)):
                        plugin_classes.append(obj)
                        logger.debug(f"Found plugin class: {name} in {py_file.name}")
                        
            except Exception as e:
                logger.error(f"Failed to import plugin module {py_file}: {e}")
        
        return plugin_classes
    
    async def analyze_content(
        self, 
        videos: List[YouTubeVideoRaw], 
        user_request: ParsedUserRequest
    ) -> PluginResult:
        """
        Analyze content using the most appropriate plugin
        
        Args:
            videos: Videos to analyze
            user_request: User's parsed request
            
        Returns:
            PluginResult: Analysis results
        """
        start_time = datetime.now()
        
        try:
            # Determine content type from user request
            content_type = user_request.content_filter.content_type
            
            # Find the best plugin for this content type and request
            plugin = self.registry.find_best_plugin(content_type, user_request)
            
            if not plugin:
                # Fallback to any available plugin that might handle general content
                all_plugins = self.registry.list_plugins()
                if not all_plugins:
                    raise ClassificationError("No plugins available for content analysis")
                
                # Try to find a general purpose plugin
                general_plugins = self.registry.get_plugins_for_content_type(ContentType.GENERAL_CHALLENGE)
                if general_plugins:
                    plugin = general_plugins[0]
                else:
                    # Use any available plugin as last resort
                    plugin = list(self.registry._plugins.values())[0]
                
                logger.warning(f"No specific plugin found for {content_type.value}, using {plugin.metadata.name}")
            
            # Validate input
            if not plugin.validate_input(videos):
                raise ClassificationError(f"Invalid input for plugin {plugin.metadata.name}")
            
            # Create analysis context
            context = AnalysisContext(
                user_request=user_request,
                search_keywords=user_request.content_filter.keywords,
                region_code="US",
                language_preference=user_request.output_preferences.language,
                analysis_depth=user_request.output_preferences.detail_level
            )
            
            # Optimize search keywords if plugin supports it
            try:
                optimized_keywords = await plugin.optimize_search_keywords(
                    context.search_keywords, context
                )
                context.search_keywords = optimized_keywords
            except Exception as e:
                logger.warning(f"Failed to optimize keywords with {plugin.metadata.name}: {e}")
            
            # Perform analysis
            logger.info(f"Analyzing {len(videos)} videos with plugin: {plugin.metadata.name}")
            result = await plugin.analyze_videos(videos, context)
            
            if result.success:
                # Generate additional insights
                try:
                    insights = await plugin.generate_insights(result.analyzed_videos, context)
                    result.insights.update(insights)
                except Exception as e:
                    logger.warning(f"Failed to generate insights: {e}")
                    result.warnings.append(f"Insight generation failed: {str(e)}")
                
                logger.info(
                    f"Content analysis completed successfully: {len(result.analyzed_videos)} videos "
                    f"analyzed in {result.processing_time:.2f}s"
                )
            else:
                logger.error(f"Content analysis failed: {result.error_message}")
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Content analysis failed: {e}")
            
            return PluginResult(
                success=False,
                analyzed_videos=[],
                insights={},
                processing_time=processing_time,
                confidence_score=0.0,
                error_message=str(e),
                warnings=[],
                metadata={
                    "plugin_manager_error": True,
                    "content_type": user_request.content_filter.content_type.value
                }
            )
    
    async def get_recommendations(
        self, 
        base_videos: List[EnhancedClassifiedVideo],
        user_request: ParsedUserRequest,
        max_recommendations: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get content recommendations using appropriate plugin
        
        Args:
            base_videos: Videos to base recommendations on
            user_request: User's parsed request
            max_recommendations: Maximum number of recommendations
            
        Returns:
            List[Dict[str, Any]]: Content recommendations
        """
        try:
            content_type = user_request.content_filter.content_type
            plugin = self.registry.find_best_plugin(content_type, user_request)
            
            if not plugin:
                logger.warning("No plugin available for recommendations")
                return []
            
            context = AnalysisContext(
                user_request=user_request,
                search_keywords=user_request.content_filter.keywords,
                language_preference=user_request.output_preferences.language
            )
            
            recommendations = await plugin.recommend_related_content(
                base_videos, context, max_recommendations
            )
            
            logger.info(f"Generated {len(recommendations)} recommendations using {plugin.metadata.name}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            return []
    
    def get_plugin_stats(self) -> Dict[str, Any]:
        """Get plugin loading and usage statistics"""
        return {
            "load_stats": self._load_stats.copy(),
            "registered_plugins": len(self.registry._plugins),
            "plugins": self.registry.list_plugins()
        }
    
    async def health_check_all_plugins(self) -> Dict[str, Any]:
        """Perform health check on all plugins"""
        health_results = {}
        
        for name, plugin in self.registry._plugins.items():
            try:
                health_info = await plugin.health_check()
                health_results[name] = health_info
            except Exception as e:
                health_results[name] = {
                    "plugin_name": name,
                    "status": "error",
                    "error": str(e)
                }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_plugins": len(self.registry._plugins),
            "healthy_plugins": len([h for h in health_results.values() if h.get("status") == "healthy"]),
            "plugins": health_results
        }


# Factory function
def create_plugin_manager() -> PluginManager:
    """Create a new plugin manager instance"""
    return PluginManager()