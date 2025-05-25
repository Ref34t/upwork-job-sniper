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
        self.setup_signal_handlers()
    
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
        client = job.get('client', {})
        
        lines = [
            f"Title: {job.get('title', 'N/A')}",
            f"Posted: {job.get('createdDateTime', 'N/A')}",
            f"Experience: {job.get('experienceLevel', 'N/A')}",
            f"Applicants: {job.get('totalApplicants', 0)}",
        ]
        
        # Add budget information if available
        if 'hourlyBudgetMin' in job and job['hourlyBudgetMin']:
            min_rate = job['hourlyBudgetMin'].get('displayValue', 'N/A')
            max_rate = job['hourlyBudgetMax'].get('displayValue', 'N/A') if 'hourlyBudgetMax' in job else 'N/A'
            lines.append(f"Hourly Rate: {min_rate} - {max_rate}")
        elif 'amount' in job and job['amount']:
            lines.append(f"Budget: {job['amount'].get('displayValue', 'N/A')}")
        
        # Add client information if available
        if client:
            client_info = [
                f"Client: {client.get('totalReviews', 0)} reviews",
                f"Spent: {client.get('totalSpent', {}).get('displayValue', 'N/A')}",
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
            logger.warning("Received job with no ID, skipping...")
            return
            
        try:
            # Get full job details if we don't have them already
            if 'description' not in job:
                job_details = self.upwork.get_job_details(job_id)
                job = job_details.get('data', {}).get('job', {})
            
            # Log the job details
            logger.info(f"Found new job: {job.get('title')} (ID: {job_id})")
            logger.debug(f"Job details:\n{self._format_job_details(job)}")
            
            # TODO: Add job processing logic here
            # 1. Score the job
            # 2. Generate summary using AI
            # 3. Send notification
            
            # Mark job as processed
            self.job_tracker.mark_job_seen(job_id)
            
        except Exception as e:
            logger.error(f"Failed to process job {job_id}: {e}", exc=True)
    
    async def run(self):
        """Run the main application loop."""
        logger.info("Starting Upwork Job Sniper...")
        
        # No explicit connection needed for GraphQL client
        logger.info("Upwork GraphQL client initialized")
        
        try:
            # Main application loop
            while not self.should_exit:
                logger.info("Checking for new jobs...")
                
                try:
                    # Search for jobs using GraphQL
                    search_results = self.upwork.search_jobs(
                        title_expression="python",  # TODO: Make this configurable
                        hourly_rate_min=30,  # $30/hr minimum
                        budget_min=500,  # $500 minimum for fixed-price jobs
                        limit=10
                    )
                    
                    # Extract jobs from GraphQL response
                    jobs_data = search_results.get('data', {}).get('marketplaceJobPostingsSearch', {})
                    edges = jobs_data.get('edges', [])
                    
                    # Process new jobs
                    new_jobs = 0
                    for edge in edges:
                        job = edge.get('node', {})
                        job_id = job.get('id')
                        if job_id and self.job_tracker.is_new_job(job_id):
                            await self.process_job(edge)  # Pass the edge to get access to cursor if needed
                            new_jobs += 1
                    
                    logger.info(f"Found {len(edges)} jobs, {new_jobs} new")
                    
                except UpworkAuthenticationError as e:
                    logger.error(f"Authentication error: {e}")
                    # Don't retry immediately on auth errors
                    break
                except Exception as e:
                    logger.error(f"Error during job search: {e}", exc_info=True)
                
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
