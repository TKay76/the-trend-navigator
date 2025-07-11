#!/usr/bin/env python3
"""
YouTube Charts Scraper using Playwright - Korean Shorts Daily Rankings

This script uses Playwright to scrape actual YouTube Charts data
for Korean Shorts daily rankings. Playwright is more lightweight
than Selenium and doesn't require Chrome installation.

=== INSTALLATION ===
1. Install Playwright:
   pip install playwright

2. Install browser (one-time setup):
   playwright install chromium

3. Run the script:
   python youtube_charts_playwright.py

=== FEATURES ===
- Uses Playwright for reliable web scraping
- No Chrome installation required
- Scrapes actual Korean Shorts daily chart
- Identifies trending songs
- Lightweight and fast

=== USAGE ===
# Basic usage
python youtube_charts_playwright.py

# With virtual environment
source venv_linux/bin/activate
python youtube_charts_playwright.py

# Get specific number of songs
python youtube_charts_playwright.py --limit 5

Requirements:
- playwright
- No additional browser installation needed

Author: Claude Code
Date: 2025-07-11
"""

import sys
import asyncio
import argparse
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    print("❌ Playwright not installed. Installing now...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    try:
        from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
    except ImportError:
        print("❌ Failed to install Playwright")
        print("Please install manually: pip install playwright")
        sys.exit(1)


@dataclass
class ChartSong:
    """Represents a song from the YouTube Charts."""
    rank: int
    title: str
    artist: str
    is_trending: bool = False
    thumbnail_url: Optional[str] = None
    view_count: Optional[str] = None


class YouTubeChartsPlaywrightScraper:
    """
    YouTube Charts scraper using Playwright.
    
    This class uses Playwright to scrape actual YouTube Charts data
    for Korean Shorts daily rankings.
    """
    
    def __init__(self, headless: bool = True):
        """
        Initialize the scraper.
        
        Args:
            headless (bool): Whether to run browser in headless mode
        """
        self.url = "https://charts.youtube.com/charts/TopShortsSongs/kr/daily"
        self.headless = headless
        
    async def scrape_charts(self, limit: int = 10) -> List[ChartSong]:
        """
        Scrape YouTube Charts for Korean Shorts daily rankings.
        
        Args:
            limit (int): Maximum number of songs to return
            
        Returns:
            List[ChartSong]: List of chart songs
        """
        print("🚀 Starting Playwright-based YouTube Charts scraping...")
        print(f"🎯 Target: {self.url}")
        print(f"📊 Limit: {limit} songs")
        
        songs = []
        
        try:
            async with async_playwright() as p:
                # Launch browser
                print("🔧 Launching browser...")
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-extensions",
                        "--lang=ko-KR"
                    ]
                )
                
                # Create context with user agent
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="ko-KR"
                )
                
                # Create page
                page = await context.new_page()
                
                # Navigate to charts
                print("🌐 Navigating to YouTube Charts...")
                await page.goto(self.url, wait_until="networkidle", timeout=60000)
                
                # Wait for content to load
                print("⏳ Waiting for content to load...")
                await page.wait_for_timeout(5000)
                
                # Try to find chart items with multiple selectors
                print("🔍 Looking for chart items...")
                
                chart_selectors = [
                    "ytmusic-responsive-list-item-renderer",
                    "[data-testid='chart-row']",
                    ".chart-row",
                    ".ytmusic-shelf-renderer .ytmusic-responsive-list-item-renderer",
                    ".content-wrapper"
                ]
                
                chart_items = []
                for selector in chart_selectors:
                    try:
                        items = await page.query_selector_all(selector)
                        if items:
                            print(f"✅ Found {len(items)} items with selector: {selector}")
                            chart_items = items
                            break
                    except Exception as e:
                        continue
                
                if not chart_items:
                    print("❌ No chart items found")
                    # Try to get page content for debugging
                    content = await page.content()
                    if "charts" in content.lower():
                        print("📄 Page loaded but no chart items detected")
                    else:
                        print("❌ Page may not have loaded correctly")
                    return []
                
                print(f"📊 Processing {len(chart_items)} chart items...")
                
                # Extract data from each item
                for i, item in enumerate(chart_items[:limit]):
                    try:
                        rank = i + 1
                        
                        # Try to get title
                        title = "Unknown Title"
                        title_selectors = [
                            ".title",
                            ".primary-text",
                            "h3",
                            "[data-testid='title']",
                            ".ytmusic-responsive-list-item-renderer .title",
                            "a[href*='watch']"
                        ]
                        
                        for selector in title_selectors:
                            try:
                                title_element = await item.query_selector(selector)
                                if title_element:
                                    title_text = await title_element.text_content()
                                    if title_text and title_text.strip():
                                        title = title_text.strip()
                                        break
                            except:
                                continue
                        
                        # Try to get artist
                        artist = "Unknown Artist"
                        artist_selectors = [
                            ".artist",
                            ".secondary-text",
                            ".subtitle",
                            "[data-testid='artist']",
                            ".ytmusic-responsive-list-item-renderer .subtitle"
                        ]
                        
                        for selector in artist_selectors:
                            try:
                                artist_element = await item.query_selector(selector)
                                if artist_element:
                                    artist_text = await artist_element.text_content()
                                    if artist_text and artist_text.strip():
                                        artist = artist_text.strip()
                                        break
                            except:
                                continue
                        
                        # Check for trending indicators
                        is_trending = False
                        trending_selectors = [
                            ".badge",
                            ".trending-badge",
                            ".ytmusic-badge-renderer"
                        ]
                        
                        for selector in trending_selectors:
                            try:
                                badge_element = await item.query_selector(selector)
                                if badge_element:
                                    badge_text = await badge_element.text_content()
                                    if badge_text and any(keyword in badge_text.lower() for keyword in ["trending", "급상승", "인기"]):
                                        is_trending = True
                                        break
                            except:
                                continue
                        
                        # Get thumbnail
                        thumbnail_url = None
                        try:
                            img_element = await item.query_selector("img")
                            if img_element:
                                thumbnail_url = await img_element.get_attribute("src")
                        except:
                            pass
                        
                        # Clean up text
                        title = title.replace("\n", " ").strip()
                        artist = artist.replace("\n", " ").strip()
                        
                        # Skip if no meaningful data
                        if title == "Unknown Title" and artist == "Unknown Artist":
                            continue
                        
                        song = ChartSong(
                            rank=rank,
                            title=title,
                            artist=artist,
                            is_trending=is_trending,
                            thumbnail_url=thumbnail_url
                        )
                        
                        songs.append(song)
                        print(f"  ✅ #{rank}: {title} - {artist}")
                        
                    except Exception as e:
                        print(f"⚠️  Error processing item {i+1}: {e}")
                        continue
                
                # Close browser
                await browser.close()
                
        except PlaywrightTimeoutError:
            print("❌ Timeout while loading page")
        except Exception as e:
            print(f"❌ Error during scraping: {e}")
        
        return songs


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


async def main():
    """Main async function to run the scraper."""
    parser = argparse.ArgumentParser(
        description="Playwright YouTube Charts Scraper for Korean Shorts",
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
        help="Run browser in visible mode (for debugging)"
    )
    
    args = parser.parse_args()
    
    # Validate limit
    if args.limit < 1 or args.limit > 100:
        print("❌ Limit must be between 1 and 100")
        sys.exit(1)
    
    try:
        # Create scraper
        scraper = YouTubeChartsPlaywrightScraper(headless=not args.no_headless)
        
        # Scrape charts
        songs = await scraper.scrape_charts(limit=args.limit)
        
        # Display results
        display_results(songs)
        
    except KeyboardInterrupt:
        print("\n🛑 Scraping interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


def run_main():
    """Wrapper to run async main function."""
    asyncio.run(main())


if __name__ == "__main__":
    run_main()