"""
News Service for RSS Feed Management
Handles fetching, caching, and deduplication of news from multiple sources
"""

import feedparser
import requests
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional
from threading import Thread, Lock
import time
import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)


class NewsItem:
    """Represents a single news article."""
    
    def __init__(self, title: str, source: str, link: str, published: str, summary: str = ""):
        self.title = title.strip()
        self.source = source
        self.link = link
        self.published = published
        self.summary = summary.strip() if summary else ""
        
        # Generate unique ID based on title + link
        self.id = self._generate_id()
        
        # Parse published time
        self.published_dt = self._parse_published_time()
    
    def _generate_id(self) -> str:
        """Generate unique ID for the news item."""
        content = f"{self.title}{self.link}".encode('utf-8')
        return hashlib.md5(content).hexdigest()
    
    def _parse_published_time(self) -> datetime:
        """Parse published time string to datetime."""
        try:
            # Try parsing various formats
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(self.published)
            # Make timezone-aware if not already
            if dt.tzinfo is None:
                from pytz import UTC
                dt = dt.replace(tzinfo=UTC)
            return dt
        except:
            try:
                # Fallback to ISO format
                dt = datetime.fromisoformat(self.published.replace('Z', '+00:00'))
                # Make timezone-aware if not already
                if dt.tzinfo is None:
                    from pytz import UTC
                    dt = dt.replace(tzinfo=UTC)
                return dt
            except:
                # Use current time as fallback (timezone-aware)
                from pytz import UTC
                return datetime.now(UTC)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'source': self.source,
            'url': self.link,
            'published': self.published,
            'summary': self.summary
        }
    
    def __repr__(self):
        return f"<NewsItem: {self.source} - {self.title[:50]}>"


class NewsService:
    """
    Production-ready news service with caching and deduplication.
    """
    
    # RSS Feed URLs
    FEEDS = {
        "NSE Announcements": "https://www.nseindia.com/rss/corporate-announcements.xml",
        "NSE Circulars": "https://www.nseindia.com/rss/circulars.xml",
        "BSE Announcements": "https://www.bseindia.com/xml-data/corpfiling/announcements.xml",
        "RBI Press Releases": "https://www.rbi.org.in/rss/PressReleases.aspx",
        "SEBI": "https://www.sebi.gov.in/sebirss.xml",
        "MoneyControl": "https://www.moneycontrol.com/rss/MCtopnews.xml",
        "Economic Times": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "Live Mint": "https://www.livemint.com/rss/markets",
    }
    
    def __init__(self, update_interval: int = 30, max_items: int = 100):
        """
        Initialize News Service.
        
        Args:
            update_interval: Seconds between feed updates (default: 30)
            max_items: Maximum news items to cache (default: 100)
        """
        self.update_interval = update_interval
        self.max_items = max_items
        
        # Cache for news items (ordered by time)
        self.news_cache: OrderedDict[str, NewsItem] = OrderedDict()
        self.cache_lock = Lock()
        
        # Track seen item IDs to prevent duplicates
        self.seen_ids: Set[str] = set()
        
        # Service state
        self.is_running = False
        self.update_thread: Optional[Thread] = None
        self.last_update: Optional[datetime] = None
        
        # Statistics
        self.total_fetches = 0
        self.failed_fetches = 0
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        import re
        if not text:
            return ""
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text).strip()
    
    def _fetch_single_feed(self, source: str, url: str) -> List[NewsItem]:
        """
        Fetch and parse a single RSS feed.
        
        Args:
            source: Name of the news source
            url: RSS feed URL
            
        Returns:
            List of NewsItem objects
        """
        items = []
        
        try:
            # Set headers to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/rss+xml, application/xml, text/xml, */*'
            }
            
            # Fetch with timeout
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Parse feed
            feed = feedparser.parse(response.content)
            
            # Extract entries
            for entry in feed.entries[:20]:  # Limit to 20 per feed
                try:
                    title = entry.get('title', 'No Title')
                    link = entry.get('link', '')
                    published = entry.get('published', entry.get('updated', ''))
                    summary = entry.get('summary', entry.get('description', ''))
                    
                    # Clean summary
                    summary = self._clean_html(summary)[:300]  # Limit length
                    
                    # Create news item
                    item = NewsItem(
                        title=title,
                        source=source,
                        link=link,
                        published=published,
                        summary=summary
                    )
                    
                    items.append(item)
                    
                except Exception as e:
                    logger.debug(f"Error parsing entry from {source}: {e}")
                    continue
            
            logger.info(f"Fetched {len(items)} items from {source}")
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching {source}")
            self.failed_fetches += 1
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error for {source}: {e}")
            self.failed_fetches += 1
        except Exception as e:
            logger.error(f"Unexpected error fetching {source}: {e}")
            self.failed_fetches += 1
        
        return items
    
    def _fetch_all_feeds(self) -> List[NewsItem]:
        """
        Fetch all RSS feeds concurrently.
        
        Returns:
            List of all NewsItem objects, deduplicated and sorted
        """
        all_items = []
        
        # Fetch feeds sequentially (can be made concurrent with ThreadPoolExecutor)
        for source, url in self.FEEDS.items():
            items = self._fetch_single_feed(source, url)
            all_items.extend(items)
        
        # Remove duplicates based on ID
        unique_items = OrderedDict()
        for item in all_items:
            if item.id not in unique_items:
                unique_items[item.id] = item
        
        # Sort by published time (newest first)
        sorted_items = sorted(
            unique_items.values(),
            key=lambda x: x.published_dt,
            reverse=True
        )
        
        return sorted_items[:self.max_items]
    
    def update_cache(self):
        """Update news cache with latest items."""
        try:
            logger.info("Updating news cache...")
            
            # Fetch latest news
            new_items = self._fetch_all_feeds()
            
            with self.cache_lock:
                # Clear old cache
                self.news_cache.clear()
                self.seen_ids.clear()
                
                # Add new items
                for item in new_items:
                    self.news_cache[item.id] = item
                    self.seen_ids.add(item.id)
                
                self.last_update = datetime.now()
            
            self.total_fetches += 1
            logger.info(f"Cache updated with {len(new_items)} items")
            
        except Exception as e:
            logger.error(f"Error updating cache: {e}")
            self.failed_fetches += 1
    
    def get_latest_news(self, count: Optional[int] = None) -> List[NewsItem]:
        """
        Get latest news items from cache.
        
        Args:
            count: Number of items to return (None = all)
            
        Returns:
            List of NewsItem objects
        """
        with self.cache_lock:
            items = list(self.news_cache.values())
            if count:
                return items[:count]
            return items
    
    def get_new_items_since(self, last_seen_id: str) -> List[NewsItem]:
        """
        Get news items that are newer than the given ID.
        
        Args:
            last_seen_id: ID of last seen news item
            
        Returns:
            List of newer NewsItem objects
        """
        with self.cache_lock:
            items = list(self.news_cache.values())
            
            # Find index of last seen item
            try:
                last_index = next(i for i, item in enumerate(items) if item.id == last_seen_id)
                return items[:last_index]
            except StopIteration:
                # Last seen item not found, return all
                return items
    
    def get_sources(self) -> List[str]:
        """Get list of configured news sources."""
        return list(self.FEEDS.keys())
    
    def get_status(self) -> Dict:
        """
        Get service status information.
        
        Returns:
            Dictionary with status info
        """
        with self.cache_lock:
            return {
                "is_running": self.is_running,
                "cached_items": len(self.news_cache),
                "last_update": self.last_update.isoformat() if self.last_update else None,
                "total_fetches": self.total_fetches,
                "failed_fetches": self.failed_fetches,
                "update_interval": self.update_interval,
                "sources_count": len(self.FEEDS)
            }
    
    def force_refresh(self):
        """Force an immediate cache refresh."""
        logger.info("Force refresh triggered")
        self.update_cache()
    
    def _update_loop(self):
        """Background update loop."""
        logger.info("Starting news update loop")
        
        # Initial update
        self.update_cache()
        
        while self.is_running:
            time.sleep(self.update_interval)
            if self.is_running:
                self.update_cache()
    
    def start(self):
        """Start background updates."""
        if self.is_running:
            logger.warning("Service already running")
            return
        
        self.is_running = True
        self.update_thread = Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        
        logger.info(f"News service started (update interval: {self.update_interval}s)")
    
    def stop(self):
        """Stop background updates."""
        if not self.is_running:
            return
        
        logger.info("Stopping news service...")
        self.is_running = False
        
        if self.update_thread:
            self.update_thread.join(timeout=5)
        
        logger.info("News service stopped")
