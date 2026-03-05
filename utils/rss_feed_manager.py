"""
RSS Feed Manager for Market News

Fetches and manages RSS feeds from multiple Indian financial sources:
- NSE India
- BSE India
- RBI
- SEBI
- MoneyControl
- Economic Times
- Live Mint
"""

import feedparser
import requests
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Dict, Optional
import logging
from threading import Thread, Lock
import time

logger = logging.getLogger(__name__)


class RSSFeedItem:
    """Represents a single news item from RSS feed."""
    
    def __init__(self, title: str, source: str, link: str, published: str, summary: str = ""):
        self.title = title
        self.source = source
        self.link = link
        self.published = published
        self.summary = summary
        self.timestamp = datetime.now()
        self.published_dt = self._parse_published_datetime(published)

    def _parse_published_datetime(self, published: str) -> datetime:
        """Parse RSS published text into datetime, fallback to current time."""
        if not published:
            return self.timestamp

        try:
            dt = parsedate_to_datetime(published)
            if dt:
                return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except Exception:
            pass

        # Try common datetime format fallback
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(published[:19], fmt)
            except Exception:
                continue

        return self.timestamp
    
    def __repr__(self):
        return f"<RSSFeedItem: {self.source} - {self.title[:50]}...>"


class RSSFeedManager:
    """
    Manages RSS feeds from multiple Indian financial sources.
    Fetches, parses, and provides consolidated news feed.
    """
    
    # RSS Feed URLs
    FEEDS = {
        "Investing - General News": "https://www.investing.com/rss/news.rss",
        "Investing - Markets": "https://www.investing.com/rss/news_25.rss",
        "Investing - Category 301": "https://www.investing.com/rss/news_301.rss",
    }
    
    def __init__(self, max_items: int = 50):
        """
        Initialize RSS Feed Manager.
        
        Args:
            max_items: Maximum number of news items to store
        """
        self.max_items = max_items
        self.news_items: List[RSSFeedItem] = []
        self.lock = Lock()
        self.last_update = None
        self.is_running = False
        self.update_thread = None
    
    def fetch_feed(self, source: str, url: str) -> List[RSSFeedItem]:
        """
        Fetch and parse a single RSS feed.
        
        Args:
            source: Name of the news source
            url: RSS feed URL
            
        Returns:
            List of RSSFeedItem objects
        """
        items = []
        try:
            # Set user agent to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            # Fetch feed with timeout
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse feed
            feed = feedparser.parse(response.content)
            
            # Extract items
            for entry in feed.entries[:10]:  # Limit to 10 items per feed
                try:
                    title = entry.get('title', 'No Title')
                    link = entry.get('link', '')
                    published = entry.get('published', entry.get('updated', ''))
                    summary = entry.get('summary', entry.get('description', ''))
                    
                    # Clean HTML tags from summary
                    if summary:
                        summary = self._clean_html(summary)
                    
                    item = RSSFeedItem(
                        title=title,
                        source=source,
                        link=link,
                        published=published,
                        summary=summary[:200]  # Limit summary length
                    )
                    items.append(item)
                    
                except Exception as e:
                    logger.warning(f"Error parsing entry from {source}: {e}")
                    continue
            
            logger.info(f"Fetched {len(items)} items from {source}")
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching feed from {source}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error fetching feed from {source}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching feed from {source}: {e}")
        
        return items
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        import re
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text).strip()
    
    def fetch_all_feeds(self) -> List[RSSFeedItem]:
        """
        Fetch all RSS feeds from configured sources.
        
        Returns:
            Consolidated list of all news items
        """
        all_items = []
        
        for source, url in self.FEEDS.items():
            items = self.fetch_feed(source, url)
            all_items.extend(items)
        
        # Sort by published datetime (most recent first)
        all_items.sort(key=lambda x: x.published_dt, reverse=True)
        
        return all_items[:self.max_items]
    
    def update_feeds(self):
        """Update news feeds from all sources."""
        with self.lock:
            self.news_items = self.fetch_all_feeds()
            self.last_update = datetime.now()
            logger.info(f"Updated RSS feeds: {len(self.news_items)} total items")
    
    def get_latest_items(self, count: int = 10) -> List[RSSFeedItem]:
        """
        Get the latest news items.
        
        Args:
            count: Number of items to return
            
        Returns:
            List of latest RSSFeedItem objects
        """
        with self.lock:
            return self.news_items[:count]
    
    def start_auto_update(self, interval: int = 300):
        """
        Start automatic feed updates in background thread.
        
        Args:
            interval: Update interval in seconds (default: 300 = 5 minutes)
        """
        if self.is_running:
            logger.warning("Auto-update already running")
            return
        
        self.is_running = True
        
        def update_loop():
            # Initial update
            self.update_feeds()
            
            while self.is_running:
                time.sleep(interval)
                if self.is_running:
                    self.update_feeds()
        
        self.update_thread = Thread(target=update_loop, daemon=True)
        self.update_thread.start()
        logger.info(f"Started RSS feed auto-update (interval: {interval}s)")
    
    def stop_auto_update(self):
        """Stop automatic feed updates."""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join(timeout=2)
        logger.info("Stopped RSS feed auto-update")
    
    def get_feed_status(self) -> Dict:
        """
        Get status information about feeds.
        
        Returns:
            Dictionary with status information
        """
        with self.lock:
            return {
                "total_items": len(self.news_items),
                "last_update": self.last_update,
                "is_running": self.is_running,
                "sources": list(self.FEEDS.keys())
            }
