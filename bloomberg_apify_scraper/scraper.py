#!/usr/bin/env python3
"""
Bloomberg Real-Time Article Scraper using Apify.

This script continuously scrapes Bloomberg news articles using the sitemap
and sends them to the Apify Bloomberg Article Scraper actor.

Supports:
- Real-time mode: Continuously polls sitemap for new articles
- Single-article mode: Scrapes a single article URL and exits
"""

import argparse
import logging
import os
import signal
import sys
import time
from typing import Optional

from dotenv import load_dotenv

from sitemap import SitemapFetcher, URLTracker
from apify_runner import ApifyRunner

# Load environment variables from .env file
load_dotenv()

# Global flag for graceful shutdown
shutdown_requested = False


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('apify_client').setLevel(logging.WARNING)


def get_config() -> dict:
    """
    Load configuration from environment variables.
    
    Returns:
        Dict containing all configuration values
    """
    return {
        'apify_api_token': os.getenv('APIFY_API_TOKEN', ''),
        'scrape_mode': os.getenv('SCRAPE_MODE', 'realtime').lower(),
        'max_initial_urls': int(os.getenv('MAX_INITIAL_URLS', '25')),
        'poll_interval_seconds': int(os.getenv('POLL_INTERVAL_SECONDS', '300')),
        'single_article_url': os.getenv('SINGLE_ARTICLE_URL', ''),
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        'persistence_file': os.getenv('PERSISTENCE_FILE', ''),
        'batch_size': int(os.getenv('BATCH_SIZE', '5')),
    }


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger = logging.getLogger(__name__)
    logger.info("Shutdown signal received. Finishing current operation...")
    shutdown_requested = True


def run_single_article_mode(
    apify_runner: ApifyRunner,
    article_url: str
) -> bool:
    """
    Run single article scraping mode.
    
    Args:
        apify_runner: Configured ApifyRunner instance
        article_url: URL of the article to scrape
        
    Returns:
        True if successful, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    logger.info(f"Single article mode: Scraping {article_url}")
    
    result = apify_runner.scrape_article(article_url)
    
    if result and result.get('items'):
        logger.info("=" * 60)
        logger.info("SCRAPE RESULTS")
        logger.info("=" * 60)
        logger.info(f"Dataset ID: {result.get('dataset_id')}")
        logger.info(f"Run ID: {result.get('run_id')}")
        logger.info(f"Items received: {result.get('items_received')}")
        logger.info("-" * 60)
        
        for i, item in enumerate(result['items'], 1):
            logger.info(f"\n--- Article {i} ---")
            logger.info(f"Title: {item.get('title', 'N/A')}")
            logger.info(f"URL: {item.get('url', 'N/A')}")
            logger.info(f"Author: {item.get('author', 'N/A')}")
            logger.info(f"Published: {item.get('publishedAt', item.get('date', 'N/A'))}")
            
            # Print a preview of the content
            content = item.get('content', item.get('text', ''))
            if content:
                preview = content[:500] + '...' if len(content) > 500 else content
                logger.info(f"Content preview: {preview}")
        
        logger.info("=" * 60)
        return True
    else:
        logger.error("Failed to scrape article or no data returned")
        return False


def run_realtime_mode(
    apify_runner: ApifyRunner,
    sitemap_fetcher: SitemapFetcher,
    url_tracker: URLTracker,
    config: dict
) -> None:
    """
    Run real-time continuous scraping mode.
    
    Args:
        apify_runner: Configured ApifyRunner instance
        sitemap_fetcher: Configured SitemapFetcher instance
        url_tracker: URLTracker for deduplication
        config: Configuration dictionary
    """
    global shutdown_requested
    logger = logging.getLogger(__name__)
    
    max_initial_urls = config['max_initial_urls']
    poll_interval = config['poll_interval_seconds']
    batch_size = config['batch_size']
    
    logger.info("=" * 60)
    logger.info("STARTING REAL-TIME SCRAPING MODE")
    logger.info("=" * 60)
    logger.info(f"Max initial URLs: {max_initial_urls}")
    logger.info(f"Poll interval: {poll_interval} seconds")
    logger.info(f"Batch size: {batch_size}")
    logger.info("Press Ctrl+C to stop gracefully")
    logger.info("=" * 60)
    
    iteration = 0
    total_scraped = 0
    
    while not shutdown_requested:
        iteration += 1
        logger.info(f"\n--- Iteration {iteration} ---")
        
        try:
            # Fetch URLs from sitemap
            if iteration == 1:
                # First iteration: limit URLs
                all_urls = sitemap_fetcher.get_article_urls(max_urls=max_initial_urls)
            else:
                # Subsequent iterations: get all URLs
                all_urls = sitemap_fetcher.get_article_urls()
            
            # Filter out already scraped URLs
            new_urls = url_tracker.get_new_urls(all_urls)
            
            if not new_urls:
                logger.info("No new articles found in this iteration")
            else:
                logger.info(f"Found {len(new_urls)} new article(s) to scrape")
                
                # Show cost estimate
                estimate = apify_runner.estimate_cost(len(new_urls))
                logger.info(f"Estimated cost: ~${estimate['estimated_cost_usd']:.4f} USD")
                
                # Scrape in batches
                for batch_result in apify_runner.scrape_articles_batch(new_urls, batch_size):
                    if shutdown_requested:
                        break
                    
                    if batch_result.get('status') == 'SUCCEEDED':
                        items_count = batch_result.get('items_received', 0)
                        total_scraped += items_count
                        
                        logger.info(
                            f"Batch {batch_result['batch_number']}/{batch_result['total_batches']} "
                            f"completed: {items_count} items"
                        )
                        
                        # Log scraped articles
                        for item in batch_result.get('items', []):
                            title = item.get('title', 'Unknown')
                            url = item.get('url', 'Unknown')
                            logger.info(f"  ✓ {title[:60]}...")
                            url_tracker.mark_scraped(url)
                        
                        # Mark URLs as scraped even if no items returned
                        # (to avoid retrying failed URLs)
                        for url in new_urls[
                            (batch_result['batch_number'] - 1) * batch_size:
                            batch_result['batch_number'] * batch_size
                        ]:
                            url_tracker.mark_scraped(url)
                    else:
                        logger.warning(
                            f"Batch {batch_result['batch_number']} failed"
                        )
            
            # Show stats
            stats = url_tracker.get_stats()
            logger.info(f"Total URLs tracked: {stats['total_scraped']}")
            logger.info(f"Total articles scraped this session: {total_scraped}")
            
        except Exception as e:
            logger.error(f"Error in iteration {iteration}: {e}")
        
        if shutdown_requested:
            break
        
        # Wait before next poll
        logger.info(f"Waiting {poll_interval} seconds before next poll...")
        
        # Use small sleep intervals to allow for graceful shutdown
        for _ in range(poll_interval):
            if shutdown_requested:
                break
            time.sleep(1)
    
    logger.info("\n" + "=" * 60)
    logger.info("SCRAPING SESSION ENDED")
    logger.info(f"Total iterations: {iteration}")
    logger.info(f"Total articles scraped: {total_scraped}")
    logger.info("=" * 60)


def main():
    """Main entry point for the scraper."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Bloomberg Real-Time Article Scraper using Apify'
    )
    parser.add_argument(
        '--url',
        type=str,
        help='Single article URL to scrape (overrides SINGLE_ARTICLE_URL env var)'
    )
    parser.add_argument(
        '--mode',
        type=str,
        choices=['realtime', 'single'],
        help='Scraping mode (overrides SCRAPE_MODE env var)'
    )
    args = parser.parse_args()
    
    # Load configuration
    config = get_config()
    
    # Setup logging
    setup_logging(config['log_level'])
    logger = logging.getLogger(__name__)
    
    # Override config with CLI arguments
    if args.mode:
        config['scrape_mode'] = args.mode
    if args.url:
        config['single_article_url'] = args.url
        config['scrape_mode'] = 'single'
    
    # Validate API token
    if not config['apify_api_token']:
        logger.error("APIFY_API_TOKEN is not set. Please configure it in your .env file.")
        sys.exit(1)
    
    logger.info("Bloomberg Real-Time Article Scraper")
    logger.info(f"Mode: {config['scrape_mode']}")
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize components
        apify_runner = ApifyRunner(config['apify_api_token'])
        sitemap_fetcher = SitemapFetcher()
        
        # Setup URL tracker with optional persistence
        persistence_file = config.get('persistence_file') or None
        url_tracker = URLTracker(persistence_file=persistence_file)
        
        if config['scrape_mode'] == 'single':
            # Single article mode
            article_url = config['single_article_url']
            
            if not article_url:
                logger.error(
                    "No article URL provided. Use --url argument or set "
                    "SINGLE_ARTICLE_URL in .env file."
                )
                sys.exit(1)
            
            success = run_single_article_mode(apify_runner, article_url)
            sys.exit(0 if success else 1)
            
        elif config['scrape_mode'] == 'realtime':
            # Real-time continuous mode
            run_realtime_mode(
                apify_runner,
                sitemap_fetcher,
                url_tracker,
                config
            )
        else:
            logger.error(f"Unknown scrape mode: {config['scrape_mode']}")
            sys.exit(1)
            
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
