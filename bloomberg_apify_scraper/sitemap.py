"""
Sitemap module for fetching and parsing Bloomberg news sitemap.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Set, List
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

BLOOMBERG_SITEMAP_URL = "https://www.bloomberg.com/sitemaps/news/latest.xml"

# XML namespaces used in Bloomberg sitemap
NAMESPACES = {
    'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
    'news': 'http://www.google.com/schemas/sitemap-news/0.9'
}


class SitemapFetcher:
    """Handles fetching and parsing Bloomberg news sitemap."""
    
    def __init__(self, sitemap_url: str = BLOOMBERG_SITEMAP_URL):
        """
        Initialize the sitemap fetcher.
        
        Args:
            sitemap_url: URL of the Bloomberg sitemap to fetch
        """
        self.sitemap_url = sitemap_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; NewsScraper/1.0)',
            'Accept': 'application/xml, text/xml, */*'
        })
    
    def fetch_sitemap(self) -> str:
        """
        Fetch the raw XML content from the sitemap URL.
        
        Returns:
            Raw XML string content
            
        Raises:
            requests.RequestException: If the request fails
        """
        logger.info(f"Fetching sitemap from {self.sitemap_url}")
        
        try:
            response = self.session.get(self.sitemap_url, timeout=30)
            response.raise_for_status()
            logger.debug(f"Sitemap fetched successfully, size: {len(response.content)} bytes")
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch sitemap: {e}")
            raise
    
    def parse_urls(self, xml_content: str) -> List[str]:
        """
        Parse article URLs from sitemap XML content.
        
        Args:
            xml_content: Raw XML string from sitemap
            
        Returns:
            List of article URLs found in the sitemap
        """
        urls = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # Find all <loc> elements within <url> elements
            for url_elem in root.findall('.//sitemap:url', NAMESPACES):
                loc_elem = url_elem.find('sitemap:loc', NAMESPACES)
                if loc_elem is not None and loc_elem.text:
                    url = loc_elem.text.strip()
                    if self._is_valid_article_url(url):
                        urls.append(url)
            
            # Fallback: try without namespace if no results
            if not urls:
                for url_elem in root.findall('.//url'):
                    loc_elem = url_elem.find('loc')
                    if loc_elem is not None and loc_elem.text:
                        url = loc_elem.text.strip()
                        if self._is_valid_article_url(url):
                            urls.append(url)
            
            logger.info(f"Parsed {len(urls)} article URLs from sitemap")
            return urls
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse sitemap XML: {e}")
            return []
    
    def _is_valid_article_url(self, url: str) -> bool:
        """
        Validate that a URL is a valid Bloomberg article URL.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is a valid Bloomberg article URL
        """
        try:
            parsed = urlparse(url)
            
            # Must be Bloomberg domain
            if 'bloomberg.com' not in parsed.netloc:
                return False
            
            # Must be HTTPS
            if parsed.scheme != 'https':
                return False
            
            # Filter for news articles (typically contain /news/ or /articles/)
            path = parsed.path.lower()
            if '/news/' in path or '/articles/' in path:
                return True
            
            return False
            
        except Exception:
            return False
    
    def get_article_urls(self, max_urls: int = None) -> List[str]:
        """
        Fetch sitemap and return article URLs.
        
        Args:
            max_urls: Maximum number of URLs to return (None for all)
            
        Returns:
            List of article URLs
        """
        xml_content = self.fetch_sitemap()
        urls = self.parse_urls(xml_content)
        
        if max_urls is not None and max_urls > 0:
            urls = urls[:max_urls]
            logger.info(f"Limited to {len(urls)} URLs (max_urls={max_urls})")
        
        return urls


class URLTracker:
    """Tracks scraped URLs to avoid duplicates."""
    
    def __init__(self, persistence_file: str = None):
        """
        Initialize URL tracker.
        
        Args:
            persistence_file: Optional path to JSON file for persistence
        """
        self.scraped_urls: Set[str] = set()
        self.persistence_file = persistence_file
        
        if persistence_file:
            self._load_from_file()
    
    def _load_from_file(self) -> None:
        """Load previously scraped URLs from persistence file."""
        import json
        import os
        
        if self.persistence_file and os.path.exists(self.persistence_file):
            try:
                with open(self.persistence_file, 'r') as f:
                    data = json.load(f)
                    self.scraped_urls = set(data.get('scraped_urls', []))
                logger.info(f"Loaded {len(self.scraped_urls)} URLs from persistence file")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load persistence file: {e}")
    
    def _save_to_file(self) -> None:
        """Save scraped URLs to persistence file."""
        import json
        
        if self.persistence_file:
            try:
                with open(self.persistence_file, 'w') as f:
                    json.dump({'scraped_urls': list(self.scraped_urls)}, f)
                logger.debug(f"Saved {len(self.scraped_urls)} URLs to persistence file")
            except IOError as e:
                logger.warning(f"Failed to save persistence file: {e}")
    
    def is_scraped(self, url: str) -> bool:
        """Check if a URL has already been scraped."""
        return url in self.scraped_urls
    
    def mark_scraped(self, url: str) -> None:
        """Mark a URL as scraped."""
        self.scraped_urls.add(url)
        self._save_to_file()
    
    def get_new_urls(self, urls: List[str]) -> List[str]:
        """
        Filter out already scraped URLs.
        
        Args:
            urls: List of URLs to filter
            
        Returns:
            List of URLs that haven't been scraped yet
        """
        new_urls = [url for url in urls if not self.is_scraped(url)]
        logger.info(f"Found {len(new_urls)} new URLs out of {len(urls)} total")
        return new_urls
    
    def get_stats(self) -> dict:
        """Get tracker statistics."""
        return {
            'total_scraped': len(self.scraped_urls),
            'persistence_enabled': self.persistence_file is not None
        }
