#!/usr/bin/env python3
"""
Real YouTube Charts Scraper using Selenium - Korean Shorts Daily Rankings

This script uses Selenium WebDriver to scrape actual YouTube Charts data
for Korean Shorts daily rankings, including trending songs.

=== INSTALLATION ===
1. Install required packages:
   pip install selenium webdriver-manager

2. Run the script:
   python youtube_charts_real.py

=== FEATURES ===
- Uses Selenium WebDriver for real browser automation
- Scrapes actual Korean Shorts daily chart from YouTube Charts
- Identifies trending songs with special indicators
- Provides ranking, title, and artist information
- Handles dynamic content loading
- Automatic Chrome driver management

=== USAGE ===
# Basic usage
python youtube_charts_real.py

# With virtual environment (recommended)
source venv_linux/bin/activate
python youtube_charts_real.py

# Get specific number of songs
python youtube_charts_real.py --limit 5

=== NOTE ===
This script requires Chrome browser to be installed on your system.
It will automatically download and manage the Chrome WebDriver.

Requirements:
- selenium
- webdriver-manager
- Chrome browser (installed on system)

Author: Claude Code
Date: 2025-07-11
"""

import sys
import time
import argparse
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError as e:
    print(f"❌ Missing required package: {e}")
    print("Please install required packages:")
    print("pip install selenium webdriver-manager")
    sys.exit(1)


@dataclass
class ChartSong:
    """Represents a song from the YouTube Charts."""
    rank: int
    title: str
    artist: str
    is_trending: bool = False
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None


class YouTubeChartsRealScraper:
    """
    Real YouTube Charts scraper using Selenium WebDriver.
    
    This class uses Selenium to automate a real browser and scrape
    actual YouTube Charts data for Korean Shorts daily rankings.
    """
    
    def __init__(self, headless: bool = True):
        """
        Initialize the YouTube Charts scraper.
        
        Args:
            headless (bool): Whether to run Chrome in headless mode
        """
        self.url = "https://charts.youtube.com/charts/TopShortsSongs/kr/daily"
        self.headless = headless
        self.driver = None
        
    def _setup_driver(self) -> webdriver.Chrome:
        """Set up Chrome WebDriver with optimized options."""
        print("🔧 Setting up Chrome WebDriver...")
        
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless=new")
            
        # Performance and stability options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # User agent to avoid detection
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Language preference
        chrome_options.add_argument("--lang=ko-KR")
        
        # Window size
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            # Use WebDriverManager to automatically download and manage ChromeDriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Execute script to hide webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
            
        except Exception as e:
            print(f"❌ Failed to setup Chrome WebDriver: {e}")
            print("Make sure Chrome browser is installed on your system")
            raise
    
    def _wait_for_charts_to_load(self, driver: webdriver.Chrome, timeout: int = 30) -> bool:
        """Wait for the charts to load completely."""
        print("⏳ Waiting for charts to load...")
        
        try:
            # Wait for chart container to be present
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='chart-row'], .chart-row, .ytmusic-responsive-list-item-renderer"))
            )
            
            # Additional wait for dynamic content
            time.sleep(3)
            
            return True
            
        except TimeoutException:
            print("⚠️  Charts did not load within timeout period")
            return False
    
    def _extract_chart_data(self, driver: webdriver.Chrome) -> List[ChartSong]:
        """Extract chart data from the loaded page."""
        print("🔍 Extracting chart data...")
        
        songs = []
        
        # Try multiple selector patterns for chart rows
        selectors = [
            "[data-testid='chart-row']",
            ".chart-row",
            ".ytmusic-responsive-list-item-renderer",
            ".ytmusic-shelf-renderer .ytmusic-responsive-list-item-renderer",
            "[role='listitem']",
            ".content-wrapper",
            ".chart-item"
        ]
        
        chart_rows = []
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"✅ Found {len(elements)} elements with selector: {selector}")
                    chart_rows = elements
                    break
            except Exception as e:
                continue
        
        if not chart_rows:
            print("❌ No chart rows found with any selector")
            return []
        
        print(f"📊 Processing {len(chart_rows)} chart entries...")
        
        for i, row in enumerate(chart_rows[:20]):  # Limit to top 20 for safety
            try:
                # Extract rank
                rank = i + 1
                
                # Try to find title and artist
                title = "Unknown Title"
                artist = "Unknown Artist"
                is_trending = False
                thumbnail_url = None
                video_url = None
                
                # Try various selectors for title
                title_selectors = [
                    ".title",
                    ".song-title",
                    ".primary-text",
                    "[data-testid='title']",
                    "h3",
                    ".ytmusic-responsive-list-item-renderer .title",
                    ".flex-column a",
                    "a[href*='watch']"
                ]
                
                for selector in title_selectors:
                    try:
                        title_element = row.find_element(By.CSS_SELECTOR, selector)
                        title = title_element.text.strip() or title_element.get_attribute("title") or title
                        if title and title != "Unknown Title":
                            break
                    except:
                        continue
                
                # Try various selectors for artist
                artist_selectors = [
                    ".artist",
                    ".secondary-text",
                    ".subtitle",
                    "[data-testid='artist']",
                    ".ytmusic-responsive-list-item-renderer .subtitle",
                    ".flex-column a:nth-child(2)",
                    ".metadata .subtitle"
                ]
                
                for selector in artist_selectors:
                    try:
                        artist_element = row.find_element(By.CSS_SELECTOR, selector)
                        artist = artist_element.text.strip()
                        if artist and artist != "Unknown Artist":
                            break
                    except:
                        continue
                
                # Check for trending indicators
                trending_indicators = [
                    ".trending-badge",
                    ".badge",
                    "[data-testid='trending']",
                    ".ytmusic-badge-renderer",
                    ".trend-indicator"
                ]
                
                for indicator in trending_indicators:
                    try:
                        trending_element = row.find_element(By.CSS_SELECTOR, indicator)
                        is_trending = True
                        break
                    except:
                        continue
                
                # Try to get thumbnail
                try:
                    img_element = row.find_element(By.CSS_SELECTOR, "img")
                    thumbnail_url = img_element.get_attribute("src")
                except:
                    pass
                
                # Try to get video URL
                try:
                    link_element = row.find_element(By.CSS_SELECTOR, "a[href*='watch']")
                    video_url = link_element.get_attribute("href")
                except:
                    pass
                
                # Clean up title and artist
                title = title.replace("\n", " ").strip()
                artist = artist.replace("\n", " ").strip()
                
                # Skip if we couldn't extract meaningful data
                if title == "Unknown Title" and artist == "Unknown Artist":
                    continue
                
                song = ChartSong(
                    rank=rank,
                    title=title,
                    artist=artist,
                    is_trending=is_trending,
                    thumbnail_url=thumbnail_url,
                    video_url=video_url
                )
                
                songs.append(song)
                
            except Exception as e:
                print(f"⚠️  Error processing row {i+1}: {e}")
                continue
        
        return songs
    
    def scrape_charts(self, limit: int = 10) -> List[ChartSong]:
        """
        Scrape YouTube Charts for Korean Shorts daily rankings.
        
        Args:
            limit (int): Maximum number of songs to return
            
        Returns:
            List[ChartSong]: List of chart songs
        """
        print("🚀 Starting real YouTube Charts scraping...")
        print(f"🎯 Target: {self.url}")
        print(f"📊 Limit: {limit} songs")
        
        try:
            # Setup driver
            self.driver = self._setup_driver()
            
            # Navigate to charts page
            print("🌐 Navigating to YouTube Charts...")
            self.driver.get(self.url)
            
            # Wait for charts to load
            if not self._wait_for_charts_to_load(self.driver):
                print("❌ Failed to load charts")
                return []
            
            # Extract chart data
            songs = self._extract_chart_data(self.driver)
            
            # Limit results
            if songs:
                songs = songs[:limit]
                print(f"✅ Successfully extracted {len(songs)} songs")
            else:
                print("⚠️  No songs extracted")
            
            return songs
            
        except Exception as e:
            print(f"❌ Error during scraping: {e}")
            return []
            
        finally:
            # Clean up
            if self.driver:
                self.driver.quit()
                print("🧹 WebDriver cleaned up")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.driver:
            self.driver.quit()


def display_results(songs: List[ChartSong]) -> None:
    """Display the scraped results in a formatted way."""
    if not songs:
        print("❌ No songs found")
        return
    
    print(f"\n🎵 YouTube Charts - Korean Shorts Daily Rankings")
    print("=" * 50)
    print(f"📅 Scraped on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Show trending songs
    trending_songs = [song for song in songs if song.is_trending]
    if trending_songs:
        print(f"\n🔥 TRENDING SONGS:")
        for song in trending_songs:
            print(f"   🔥 #{song.rank}: {song.title} - {song.artist}")
    
    # Show all songs
    print(f"\n📊 TOP {len(songs)} SONGS:")
    for song in songs:
        trending_indicator = " 🔥" if song.is_trending else ""
        print(f"   #{song.rank:2d}: {song.title} - {song.artist}{trending_indicator}")
    
    print(f"\n✅ Successfully scraped {len(songs)} songs!")


def main():
    """Main function to run the scraper."""
    parser = argparse.ArgumentParser(
        description="Real YouTube Charts Scraper for Korean Shorts",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=10,
        help="Maximum number of songs to scrape (default: 10)"
    )
    
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run Chrome in visible mode (for debugging)"
    )
    
    args = parser.parse_args()
    
    # Validate limit
    if args.limit < 1 or args.limit > 100:
        print("❌ Limit must be between 1 and 100")
        sys.exit(1)
    
    try:
        # Create scraper
        scraper = YouTubeChartsRealScraper(headless=not args.no_headless)
        
        # Scrape charts
        songs = scraper.scrape_charts(limit=args.limit)
        
        # Display results
        display_results(songs)
        
    except KeyboardInterrupt:
        print("\n🛑 Scraping interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()