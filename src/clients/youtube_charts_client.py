"""YouTube Charts data collection client using Selenium for dynamic content"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import json

from ..core.settings import get_settings
from ..core.exceptions import YouTubeAPIError
from ..models.video_models import ChartSong

# Setup logging
logger = logging.getLogger(__name__)


class YouTubeChartsClient:
    """
    YouTube Charts scraper using Selenium for dynamic content.
    Handles Korean daily charts for shorts songs.
    """
    
    def __init__(self, headless: bool = True):
        """
        Initialize YouTube Charts client.
        
        Args:
            headless: Whether to run browser in headless mode
        """
        self.settings = get_settings()
        self.headless = headless
        self.driver = None
        self.base_url = "https://charts.youtube.com"
        
        # Rate limiting
        self.request_delay = 2.0  # seconds between requests
        self.last_request_time = 0
        
    def _setup_driver(self) -> webdriver.Chrome:
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Common options for stability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # User agent to avoid detection
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return driver
        except Exception as e:
            raise YouTubeAPIError(f"Failed to initialize Chrome driver: {str(e)}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._rate_limit()
        self.driver = self._setup_driver()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.driver:
            self.driver.quit()
    
    async def _rate_limit(self):
        """Implement rate limiting to avoid detection"""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            await asyncio.sleep(self.request_delay - time_since_last)
        
        self.last_request_time = asyncio.get_event_loop().time()
    
    async def get_top_shorts_songs_kr(self, chart_type: str = "daily") -> List[ChartSong]:
        """
        Get top shorts songs from Korean charts.
        
        Args:
            chart_type: Type of chart ("daily", "weekly", "monthly")
            
        Returns:
            List of chart songs with metadata
            
        Raises:
            YouTubeAPIError: When scraping fails
        """
        if not self.driver:
            raise YouTubeAPIError("Driver not initialized. Use async context manager.")
        
        chart_url = f"{self.base_url}/charts/TopShortsSongs/kr/{chart_type}"
        logger.info(f"Fetching chart data from: {chart_url}")
        
        try:
            await self._rate_limit()
            self.driver.get(chart_url)
            
            # Wait for chart data to load
            wait = WebDriverWait(self.driver, 20)
            
            # Look for chart container - adjust selector based on actual page structure
            chart_container = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='chart-container'], .chart-container, .chart-list"))
            )
            
            # Wait additional time for dynamic content
            await asyncio.sleep(3)
            
            # Extract chart data
            songs = await self._extract_chart_data()
            
            logger.info(f"Successfully extracted {len(songs)} songs from chart")
            return songs
            
        except TimeoutException:
            raise YouTubeAPIError("Timeout waiting for chart data to load")
        except WebDriverException as e:
            raise YouTubeAPIError(f"WebDriver error: {str(e)}")
        except Exception as e:
            raise YouTubeAPIError(f"Unexpected error during chart scraping: {str(e)}")
    
    async def _extract_chart_data(self) -> List[ChartSong]:
        """Extract chart data from the loaded page"""
        songs = []
        
        try:
            # Try multiple possible selectors for chart items
            possible_selectors = [
                ".chart-item",
                ".chart-row",
                "[data-testid='chart-item']",
                ".ytmusic-responsive-list-item-renderer",
                ".chart-table-row"
            ]
            
            chart_items = None
            for selector in possible_selectors:
                try:
                    chart_items = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if chart_items:
                        logger.debug(f"Found {len(chart_items)} items with selector: {selector}")
                        break
                except:
                    continue
            
            if not chart_items:
                # Fallback: try to extract from page source
                return await self._extract_from_page_source()
            
            # Extract data from each chart item
            for i, item in enumerate(chart_items[:50]):  # Limit to top 50
                try:
                    song_data = await self._extract_song_from_element(item, i + 1)
                    if song_data:
                        songs.append(song_data)
                except Exception as e:
                    logger.warning(f"Failed to extract song at position {i + 1}: {str(e)}")
                    continue
            
            return songs
            
        except Exception as e:
            logger.error(f"Error extracting chart data: {str(e)}")
            return []
    
    async def _extract_song_from_element(self, element, rank: int) -> Optional[ChartSong]:
        """Extract song data from a chart item element"""
        try:
            # Try to find title and artist - adjust selectors based on actual page
            title_selectors = [
                ".song-title",
                ".track-name",
                ".title",
                "h3",
                ".ytmusic-responsive-list-item-renderer .title"
            ]
            
            artist_selectors = [
                ".artist-name",
                ".artist",
                ".secondary-text",
                ".ytmusic-responsive-list-item-renderer .subtitle"
            ]
            
            title = None
            artist = None
            
            # Try to find title
            for selector in title_selectors:
                try:
                    title_element = element.find_element(By.CSS_SELECTOR, selector)
                    title = title_element.text.strip()
                    if title:
                        break
                except:
                    continue
            
            # Try to find artist
            for selector in artist_selectors:
                try:
                    artist_element = element.find_element(By.CSS_SELECTOR, selector)
                    artist = artist_element.text.strip()
                    if artist:
                        break
                except:
                    continue
            
            if not title or not artist:
                return None
            
            # Try to extract video ID from links
            video_id = None
            try:
                link_element = element.find_element(By.CSS_SELECTOR, "a[href*='watch']")
                href = link_element.get_attribute("href")
                if href and "watch?v=" in href:
                    video_id = href.split("watch?v=")[1].split("&")[0]
            except:
                pass
            
            return ChartSong(
                title=title,
                artist=artist,
                rank=rank,
                video_id=video_id
            )
            
        except Exception as e:
            logger.debug(f"Error extracting song from element: {str(e)}")
            return None
    
    async def _extract_from_page_source(self) -> List[ChartSong]:
        """Fallback method: extract data from page source"""
        songs = []
        
        try:
            page_source = self.driver.page_source
            
            # Look for JSON data in page source
            # This is a simplified approach - you may need to adjust based on actual page structure
            if '"trackMetadata"' in page_source or '"chartData"' in page_source:
                # Try to find and parse JSON data
                # This would require more specific parsing based on the actual page structure
                logger.info("Found potential JSON data in page source")
                
                # Placeholder for JSON extraction logic
                # You would need to implement specific parsing based on the page structure
                
            logger.warning("Fallback extraction not fully implemented")
            return songs
            
        except Exception as e:
            logger.error(f"Error in fallback extraction: {str(e)}")
            return songs
    
    async def get_chart_history(self, days: int = 7) -> Dict[str, List[ChartSong]]:
        """
        Get chart history for multiple days.
        
        Args:
            days: Number of days to fetch (limited to avoid detection)
            
        Returns:
            Dictionary mapping date strings to chart data
        """
        if days > 7:
            logger.warning("Limiting days to 7 to avoid detection")
            days = 7
        
        history = {}
        
        # For now, we'll only support daily charts
        # You could extend this to fetch historical data if available
        current_chart = await self.get_top_shorts_songs_kr("daily")
        today = datetime.now().strftime("%Y-%m-%d")
        history[today] = current_chart
        
        return history
    
    def get_supported_regions(self) -> List[str]:
        """Get list of supported region codes"""
        return ["kr", "us", "jp", "gb", "de", "fr", "br", "in"]
    
    def get_supported_chart_types(self) -> List[str]:
        """Get list of supported chart types"""
        return ["daily", "weekly"]