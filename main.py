#!/usr/bin/env python3
"""
Upwork Job Sniper - Main Application

This script serves as the entry point for the Upwork Job Sniper application.
It initializes the application and starts the job monitoring process.
"""
import asyncio
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

import orjson
from dotenv import load_dotenv

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from config import settings
from src.api.upwork_graphql import UpworkGraphQLClient, UpworkAuthenticationError, UpworkAPIError
from src.notifications import PushoverNotifier
from src.ai import JobAnalyzer

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
        self.data_dir.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
        self.seen_jobs_file = data_dir / "seen_jobs.json"
        self.seen_job_ids: Set[str] = set()
        self._load_seen_jobs()
        logger.info(f"JobTracker initialized with {len(self.seen_job_ids)} seen job(s)")
    
    def _load_seen_jobs(self) -> None:
        """Load seen job IDs from file."""
        if not self.seen_jobs_file.exists():
            logger.info("No existing seen jobs file found, starting fresh")
            return
            
        try:
            with open(self.seen_jobs_file, 'rb') as f:
                data = orjson.loads(f.read())
                loaded_ids = data.get("seen_job_ids", [])
                if not isinstance(loaded_ids, list):
                    raise ValueError("Invalid format in seen_jobs.json")
                    
                self.seen_job_ids = set(loaded_ids)
                logger.info(f"Successfully loaded {len(self.seen_job_ids)} seen job IDs from {self.seen_jobs_file}")
                
        except orjson.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {self.seen_jobs_file}: {e}")
            # Keep existing seen_job_ids (empty set if first run)
        except Exception as e:
            logger.error(f"Failed to load seen jobs: {e}", exc_info=True)
    
    def is_new_job(self, job_id: str) -> bool:
        """Check if a job ID has been seen before."""
        if not job_id:
            logger.warning("Empty job ID provided to is_new_job")
            return False
            
        is_new = job_id not in self.seen_job_ids
        if is_new:
            logger.debug(f"Job {job_id} is new")
        else:
            logger.debug(f"Job {job_id} has been seen before")
        return is_new
    
    def mark_job_seen(self, job_id: str) -> None:
        """Mark a job ID as seen and persist to disk."""
        if not job_id:
            logger.warning("Attempted to mark empty job ID as seen")
            return
            
        if job_id in self.seen_job_ids:
            logger.debug(f"Job {job_id} was already marked as seen")
            return
            
        logger.info(f"Marking job {job_id} as seen")
        self.seen_job_ids.add(job_id)
        self._save_seen_jobs()
    
    def _save_seen_jobs(self) -> None:
        """Save seen job IDs to file."""
        try:
            data = {"seen_job_ids": list(self.seen_job_ids)}
            temp_file = self.seen_jobs_file.with_suffix('.tmp')
            
            # Write to a temporary file first
            with open(temp_file, 'wb') as f:
                f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
            
            # Atomically replace the old file
            if sys.platform == 'win32':
                # On Windows, we can't do atomic replace, so we'll just overwrite
                if self.seen_jobs_file.exists():
                    self.seen_jobs_file.unlink()
                temp_file.rename(self.seen_jobs_file)
            else:
                # On Unix-like systems, we can do an atomic replace
                temp_file.replace(self.seen_jobs_file)
                
            logger.debug(f"Saved {len(self.seen_job_ids)} seen job IDs to {self.seen_jobs_file}")
            
        except Exception as e:
            logger.error(f"Failed to save seen jobs: {e}", exc_info=True)
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass


class UpworkJobSniper:
    """Main application class for Upwork Job Sniper."""
    
    def __init__(self):
        """Initialize the application."""
        self.should_exit = False
        self.upwork = UpworkGraphQLClient()
        self.job_tracker = JobTracker(settings.DATA_DIR)
        self.notifier = PushoverNotifier()
        self.ai_analyzer = JobAnalyzer() if settings.ENABLE_AI_ANALYSIS else None
        self.setup_signal_handlers()
        
        # Log component status
        if self.notifier.is_configured():
            logger.info("Pushover notifications are enabled")
        else:
            logger.warning("Pushover notifications are not configured. Set PUSHOVER_API_TOKEN and PUSHOVER_USER_KEY in .env to enable.")
        
        if self.ai_analyzer:
            logger.info(f"AI analysis is enabled using {self.ai_analyzer.model} (min score: {settings.MIN_NOTIFICATION_SCORE})")
        else:
            logger.warning("AI analysis is disabled. Set ENABLE_AI_ANALYSIS=true to enable job scoring and summarization.")
    
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
        
        # Log the job details
        logger.info(f"Found new job: {job.get('title')} (ID: {job_id})")
        logger.debug(f"Job details:\n{self._format_job_details(job)}")
        
        notification_sent = False
        
        try:
            # AI Analysis
            job_analysis = None
            if self.ai_analyzer:
                logger.debug(f"Analyzing job {job_id} with AI...")
                job_analysis = self.ai_analyzer.analyze_job(job)
                
                if job_analysis:
                    logger.info(f"Job {job_id} scored {job_analysis.score}/10: {job_analysis.summary[:100]}...")
                else:
                    logger.warning(f"AI analysis failed for job {job_id}")
            
            # Determine if we should send notification
            should_notify = True
            if job_analysis and self.ai_analyzer:
                should_notify = self.ai_analyzer.should_notify(job_analysis)
                if not should_notify:
                    logger.info(f"Job {job_id} score ({job_analysis.score}) below threshold ({settings.MIN_NOTIFICATION_SCORE}), skipping notification")
            
            # Send notification if conditions are met
            if should_notify and self.notifier.is_configured():
                notification_sent = self.notifier.send_job_notification(job, job_analysis)
                if notification_sent:
                    logger.info(f"Sent notification for job {job_id}")
                else:
                    logger.warning(f"Failed to send notification for job {job_id}")
            elif not self.notifier.is_configured():
                logger.debug(f"Processed job {job_id} (notifications not configured)")
            else:
                logger.debug(f"Processed job {job_id} (notification skipped)")
            
        except Exception as e:
            logger.exception(f"Error processing job {job_id}: {e}")
        finally:
            # Always mark the job as seen, even if there was an error
            # This prevents getting stuck on the same job if there are persistent issues
            try:
                self.job_tracker.mark_job_seen(job_id)
                logger.debug(f"Marked job {job_id} as seen")
            except Exception as e:
                logger.exception(f"Failed to mark job {job_id} as seen: {e}")
    
    async def run_search(self, search_config: dict) -> int:
        """Run a single search with the given configuration."""
        try:
            logger.info(f"Searching for: {search_config['query']} (${search_config['hourly_rate_min']}/hr, ${search_config['budget_min']} min)")
            
            # Get jobs from Upwork
            jobs = self.upwork.search_jobs(
                query=search_config['query'],
                hourly_rate_min=search_config['hourly_rate_min'],
                budget_min=search_config['budget_min'],
                limit=search_config.get('limit', 10)
            )
            
            # Process new jobs one at a time
            new_jobs = 0
            processed_jobs = 0
            
            for job in jobs:
                if self.should_exit:
                    break
                    
                job_id = job.get('id')
                if not job_id:
                    logger.warning("Skipping job with missing ID")
                    continue
                
                # Process one job at a time
                if self.job_tracker.is_new_job(job_id):
                    logger.debug(f"Processing new job: {job_id}")
                    await self.process_job(job)
                    new_jobs += 1
                else:
                    logger.debug(f"Skipping seen job: {job_id}")
                
                processed_jobs += 1
                if processed_jobs >= search_config.get('limit', 10):
                    break
                
                # Small delay between jobs
                await asyncio.sleep(1)
            
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
        
        # 10 minutes in seconds
        SEARCH_INTERVAL = 10 * 60
        
        try:
            while not self.should_exit:
                logger.info(f"Searching for '{settings.SEARCH_QUERY}' jobs (${settings.HOURLY_RATE_MIN}+/hr, ${settings.BUDGET_MIN}+ budget)...")
                
                try:
                    # Search with configured parameters
                    jobs = self.upwork.search_jobs(
                        query=settings.SEARCH_QUERY,
                        hourly_rate_min=settings.HOURLY_RATE_MIN,
                        budget_min=settings.BUDGET_MIN,
                        limit=settings.SEARCH_LIMIT
                    )
                    logger.info(f"Found {len(jobs)} jobs")
                    
                    # Process new jobs
                    new_jobs = 0
                    for job in jobs:
                        job_id = job.get('id')
                        if job_id and self.job_tracker.is_new_job(job_id):
                            await self.process_job(job)
                            self.job_tracker.mark_job_seen(job_id)
                            new_jobs += 1
                    
                    logger.info(f"Processed {new_jobs} new jobs")
                            
                except UpworkAuthenticationError:
                    logger.error("Authentication error. Please check your credentials.")
                    self.should_exit = True
                    break
                except Exception as e:
                    logger.error(f"Error in search: {e}", exc_info=True)
                
                # Wait before next search
                if not self.should_exit:
                    logger.info(f"Waiting {SEARCH_INTERVAL//60} minutes until next search...")
                    for _ in range(SEARCH_INTERVAL):
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
