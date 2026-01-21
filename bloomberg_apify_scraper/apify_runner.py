"""
Apify runner module for interacting with Bloomberg Article Scraper actor.
"""

import logging
from typing import List, Dict, Any, Optional, Generator

from apify_client import ApifyClient
from apify_client.consts import ActorJobStatus

logger = logging.getLogger(__name__)

# Apify actor identifier
BLOOMBERG_ACTOR_ID = "jamie_tran/bloomberg-article-scraper"


class ApifyRunner:
    """Handles interaction with Apify Bloomberg Article Scraper actor."""
    
    def __init__(self, api_token: str):
        """
        Initialize the Apify runner.
        
        Args:
            api_token: Apify API token for authentication
            
        Raises:
            ValueError: If API token is empty or invalid
        """
        if not api_token or api_token.strip() == "":
            raise ValueError("Apify API token is required")
        
        self.client = ApifyClient(api_token)
        self.actor_id = BLOOMBERG_ACTOR_ID
        logger.info(f"Initialized ApifyRunner with actor: {self.actor_id}")
    
    def scrape_article(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a single article URL.
        
        Args:
            url: Bloomberg article URL to scrape
            
        Returns:
            Scraped article data or None if failed
        """
        return self.scrape_articles([url])
    
    def scrape_articles(self, urls: List[str]) -> Optional[Dict[str, Any]]:
        """
        Scrape multiple article URLs in a single actor run.
        
        Args:
            urls: List of Bloomberg article URLs to scrape
            
        Returns:
            Dict containing run info and items, or None if failed
        """
        if not urls:
            logger.warning("No URLs provided for scraping")
            return None
        
        # Prepare input for the actor
        run_input = {
            "start_urls": [{"url": url} for url in urls]
        }
        
        logger.info(f"Starting Apify actor run with {len(urls)} URL(s)")
        logger.debug(f"URLs: {urls}")
        
        try:
            # Call the actor and wait for completion
            run = self.client.actor(self.actor_id).call(run_input=run_input)
            
            # Check run status
            status = run.get("status")
            if status != ActorJobStatus.SUCCEEDED:
                logger.error(f"Actor run failed with status: {status}")
                return None
            
            dataset_id = run.get("defaultDatasetId")
            logger.info(f"Actor run completed. Dataset ID: {dataset_id}")
            
            # Fetch results from dataset
            items = list(self.client.dataset(dataset_id).iterate_items())
            
            logger.info(f"Retrieved {len(items)} items from dataset")
            
            return {
                "run_id": run.get("id"),
                "dataset_id": dataset_id,
                "status": status,
                "items": items,
                "urls_requested": len(urls),
                "items_received": len(items)
            }
            
        except Exception as e:
            logger.error(f"Error running Apify actor: {e}")
            return None
    
    def scrape_articles_batch(
        self, 
        urls: List[str], 
        batch_size: int = 10
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Scrape articles in batches to manage costs and API limits.
        
        Args:
            urls: List of URLs to scrape
            batch_size: Number of URLs per actor run
            
        Yields:
            Results from each batch run
        """
        total_urls = len(urls)
        logger.info(f"Starting batch scraping: {total_urls} URLs in batches of {batch_size}")
        
        for i in range(0, total_urls, batch_size):
            batch = urls[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_urls + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} URLs)")
            
            result = self.scrape_articles(batch)
            if result:
                result["batch_number"] = batch_num
                result["total_batches"] = total_batches
                yield result
            else:
                logger.warning(f"Batch {batch_num} failed")
                yield {
                    "batch_number": batch_num,
                    "total_batches": total_batches,
                    "status": "FAILED",
                    "items": [],
                    "urls_requested": len(batch),
                    "items_received": 0
                }
    
    def get_dataset_items(self, dataset_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve items from a specific dataset.
        
        Args:
            dataset_id: Apify dataset ID
            
        Returns:
            List of items in the dataset
        """
        try:
            items = list(self.client.dataset(dataset_id).iterate_items())
            logger.info(f"Retrieved {len(items)} items from dataset {dataset_id}")
            return items
        except Exception as e:
            logger.error(f"Error retrieving dataset {dataset_id}: {e}")
            return []
    
    def get_actor_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the Bloomberg scraper actor.
        
        Returns:
            Actor information or None if failed
        """
        try:
            actor = self.client.actor(self.actor_id).get()
            return actor
        except Exception as e:
            logger.error(f"Error getting actor info: {e}")
            return None
    
    def estimate_cost(self, num_urls: int) -> Dict[str, Any]:
        """
        Estimate the cost for scraping a number of URLs.
        
        Note: This is a rough estimate. Actual costs depend on
        actor compute units and your Apify plan.
        
        Args:
            num_urls: Number of URLs to scrape
            
        Returns:
            Dict with cost estimation info
        """
        # Rough estimates based on typical actor performance
        # Actual costs vary based on actor implementation
        estimated_cu_per_url = 0.05  # Compute units per URL (estimate)
        estimated_cu_cost = 0.00025  # USD per compute unit (varies by plan)
        
        total_cu = num_urls * estimated_cu_per_url
        estimated_cost = total_cu * estimated_cu_cost
        
        return {
            "num_urls": num_urls,
            "estimated_compute_units": round(total_cu, 2),
            "estimated_cost_usd": round(estimated_cost, 4),
            "note": "This is a rough estimate. Actual costs depend on actor performance and your Apify plan."
        }
