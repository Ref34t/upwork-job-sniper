#!/usr/bin/env python3
"""
Upwork Job Sniper - Main Application

This script serves as the entry point for the Upwork Job Sniper application.
It initializes the application and starts the job monitoring process.
"""

import asyncio
import logging
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

import orjson
from dotenv import load_dotenv

from config import settings
from src.api.upwork_graphql import UpworkGraphQLClient, UpworkAuthenticationError, UpworkAPIError
from src.notifications import PushoverNotifier

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(settings.LOGS_DIR / "upwork_sniper.log")
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class JobTracker:
    """Tracks seen jobs to avoid duplicates."""
    
    def __init__(self, data_dir: Path):
        """Initialize the job tracker."""
        self.data_dir = data_dir
        self.seen_jobs_file = data_dir / "seen_jobs.json"
        self.seen_job_ids: Set[str] = set()
        self._load_seen_jobs()
    
    def _load_seen_jobs(self) -> None:
        """Load seen job IDs from file."""
        if self.seen_jobs_file.exists():
            try:
                with open(self.seen_jobs_file, 'rb') as f:
                    data = orjson.loads(f.read())
                    self.seen_job_ids = set(data.get("seen_job_ids", []))
                logger.info(f"Loaded {len(self.seen_job_ids)} seen job IDs from disk")
            except Exception as e:
                logger.error(f"Failed to load seen jobs: {e}")
    
    def is_new_job(self, job_id: str) -> bool:
        """Check if a job ID has been seen before."""
        return job_id not in self.seen_job_ids
    
    def mark_job_seen(self, job_id: str) -> None:
        """Mark a job ID as seen."""
        self.seen_job_ids.add(job_id)
        self._save_seen_jobs()
    
    def _save_seen_jobs(self) -> None:
        """Save seen job IDs to file."""
        try:
            data = {"seen_job_ids": list(self.seen_job_ids)}
            with open(self.seen_jobs_file, 'wb') as f:
                f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
        except Exception as e:
            logger.error(f"Failed to save seen jobs: {e}")


class UpworkJobSniper:
    """Main application class for Upwork Job Sniper."""
    
    def __init__(self):
        """Initialize the application."""
        self.should_exit = False
        self.upwork = UpworkGraphQLClient()
        self.job_tracker = JobTracker(settings.DATA_DIR)
        self.notifier = PushoverNotifier()
        self.setup_signal_handlers()
        self.current_query_index = 0
        
        # Validate search queries
        if not hasattr(settings, 'SEARCH_QUERIES') or not settings.SEARCH_QUERIES:
            logger.warning("No search queries configured in settings.SEARCH_QUERIES")
        
        # Log notification status
        if self.notifier.is_configured():
            logger.info("Pushover notifications are enabled")
        else:
            logger.warning("Pushover notifications are not configured. Set PUSHOVER_API_TOKEN and PUSHOVER_USER_KEY in .env to enable.")
    
    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self.handle_exit)
        signal.signal(signal.SIGTERM, self.handle_exit)
    
    def handle_exit(self, signum, frame):
        """Handle application shutdown."""
        logger.info("Shutting down gracefully...")
        self.should_exit = True
    
    def _format_job_details(self, job: Dict[str, Any]) -> str:
        """Format job details for logging and display."""
        if not job:
            return "No job details available"
            
        lines = []
        
        # Safely extract client information
        client = job.get('client') or {}
        
        # Add job title and ID
        lines.append(f"Title: {job.get('title', 'N/A')} (ID: {job.get('id', 'N/A')})")
        
        # Add job description (first 200 chars)
        description = job.get('description', '')
        if description:
            desc = (description[:200] + '...') if len(description) > 200 else description
            lines.append(f"Description: {desc}")
        
        # Add budget information
        hourly_min = job.get('hourlyBudgetMin', {}) or {}
        hourly_max = job.get('hourlyBudgetMax', {}) or {}
        amount = job.get('amount', {}) or {}
        
        if hourly_min.get('displayValue') and hourly_max.get('displayValue'):
            min_rate = hourly_min.get('displayValue', 'N/A')
            max_rate = hourly_max.get('displayValue', 'N/A')
            lines.append(f"Hourly Rate: {min_rate} - {max_rate}")
        elif amount.get('displayValue'):
            lines.append(f"Budget: {amount.get('displayValue', 'N/A')}")
        
        # Add client information if available
        if client:
            total_spent = (client.get('totalSpent') or {}).get('displayValue', 'N/A')
            client_info = [
                f"Client: {client.get('totalReviews', 0)} reviews",
                f"Spent: {total_spent}",
                f"Hires: {client.get('totalHires', 'N/A')}",
                f"Verification: {client.get('verificationStatus', 'N/A')}"
            ]
            lines.extend(client_info)
        
        return "\n".join(lines)
    
    async def process_job(self, job_node: Dict[str, Any]) -> None:
        """Process a single job."""
        job = job_node.get('node', {}) if 'node' in job_node else job_node
        job_id = job.get('id')
        
        if not job_id:
            logger.warning("Job missing ID, skipping")
            return
        
        try:
            # Mark job as seen first to avoid duplicates if processing fails
            self.job_tracker.mark_job_seen(job_id)
            
            # Log the job details
            logger.info(f"Found new job: {job.get('title')} (ID: {job_id})")
            logger.debug(f"Job details:\n{self._format_job_details(job)}")
            
            # TODO: Add job processing logic here
            # 1. Score the job
            # 2. Generate summary
            # 3. Send notification if score is above threshold
            
            # Send notification for the new job
            if self.notifier.is_configured():
                success = self.notifier.send_job_notification(job)
                if success:
                    logger.info(f"Sent notification for job {job_id}")
                else:
                    logger.warning(f"Failed to send notification for job {job_id}")
            else:
                logger.debug(f"Processed job {job_id} (notifications not configured)")
            
        except Exception as e:
            logger.exception(f"Failed to process job {job_id}")
    
    async def run_search(self, search_config: dict) -> int:
        """Run a single search with the given configuration."""
        try:
            logger.info(f"Searching for: {search_config['query']} (${search_config['hourly_rate_min']}/hr, ${search_config['budget_min']} min)")
            
            jobs = self.upwork.search_jobs(
                query=search_config['query'],
                hourly_rate_min=search_config['hourly_rate_min'],
                budget_min=search_config['budget_min'],
                limit=search_config.get('limit', 10)
            )
            
            # Process new jobs
            new_jobs = 0
            for job in jobs:
                job_id = job.get('id')
                if job_id and self.job_tracker.is_new_job(job_id):
                    await self.process_job(job)
                    new_jobs += 1
            
            logger.info(f"Found {len(jobs)} jobs, {new_jobs} new for query: {search_config['query']}")
            return new_jobs
            
        except UpworkAuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error during job search for {search_config['query']}: {e}", exc_info=True)
            return 0
    
    async def run(self):
        """Run the main application loop."""
        logger.info("Starting Upwork Job Sniper...")
        
        # No explicit connection needed for GraphQL client
        logger.info("Upwork GraphQL client initialized")
        
        if not hasattr(settings, 'SEARCH_QUERIES') or not settings.SEARCH_QUERIES:
            logger.error("No search queries configured. Please set SEARCH_QUERIES in settings.")
            return
        
        try:
            # Main application loop
            while not self.should_exit:
                # Get the current search config
                search_config = settings.SEARCH_QUERIES[self.current_query_index]
                
                try:
                    await self.run_search(search_config)
                    
                    # Move to the next query for the next iteration
                    self.current_query_index = (self.current_query_index + 1) % len(settings.SEARCH_QUERIES)
                    
                except UpworkAuthenticationError:
                    # Don't retry immediately on auth errors
                    break
                except Exception as e:
                    logger.error(f"Unexpected error: {e}", exc_info=True)
                
                # Wait before next poll
                logger.info(f"Waiting {settings.POLLING_INTERVAL} seconds before next check...")
                for _ in range(settings.POLLING_INTERVAL):
                    if self.should_exit:
                        break
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"An error occurred: {e}", exc_info=True)
        finally:
            logger.info("Upwork Job Sniper has been shut down.")


def main():
    """Initialize and run the application."""
    # Create data directory if it doesn't exist
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize and run the application
    app = UpworkJobSniper()
    asyncio.run(app.run())


if __name__ == "__main__":
    main()
