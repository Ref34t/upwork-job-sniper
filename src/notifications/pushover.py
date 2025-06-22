"""Pushover notification service for the Upwork Job Sniper application."""
import logging
from typing import Dict, Optional, Any

import requests
from requests.exceptions import RequestException

from config import settings

logger = logging.getLogger(__name__)

class PushoverNotifier:
    """Handles sending notifications via Pushover."""
    
    API_URL = "https://api.pushover.net/1/messages.json"
    
    def __init__(self, api_token: str = None, user_key: str = None):
        """Initialize the Pushover notifier.
        
        Args:
            api_token: Pushover API token. If not provided, will use PUSHOVER_API_TOKEN from settings.
            user_key: Pushover user/group key. If not provided, will use PUSHOVER_USER_KEY from settings.
        """
        self.api_token = api_token or settings.PUSHOVER_API_TOKEN
        self.user_key = user_key or settings.PUSHOVER_USER_KEY
        
        if not self.api_token or not self.user_key:
            logger.warning("Pushover API token or user key not configured. Notifications will be disabled.")
    
    def is_configured(self) -> bool:
        """Check if the notifier is properly configured."""
        return bool(self.api_token and self.user_key)
    
    def send_notification(
        self,
        title: str,
        message: str,
        priority: int = 0,
        url: Optional[str] = None,
        url_title: Optional[str] = None,
        sound: Optional[str] = None,
        **kwargs: Any
    ) -> bool:
        """Send a notification via Pushover.
        
        Args:
            title: Notification title
            message: Notification message
            priority: Notification priority (-2 to 2)
            url: URL to include in the notification
            url_title: Title for the URL
            sound: Sound to play for the notification
            **kwargs: Additional parameters to pass to the Pushover API
            
        Returns:
            bool: True if the notification was sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Pushover not configured, skipping notification")
            return False
            
        payload: Dict[str, Any] = {
            "token": self.api_token,
            "user": self.user_key,
            "title": title,
            "message": message,
            "priority": priority,
        }
        
        # Add optional fields if provided
        if url:
            payload["url"] = url
        if url_title:
            payload["url_title"] = url_title
        if sound:
            payload["sound"] = sound
            
        # Add any additional parameters
        payload.update(kwargs)
        
        try:
            response = requests.post(self.API_URL, data=payload, timeout=10)
            response.raise_for_status()
            logger.debug(f"Pushover notification sent: {title}")
            return True
            
        except RequestException as e:
            logger.error(f"Failed to send Pushover notification: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Pushover API response: {e.response.text}")
            return False
    
    def _format_budget(self, job: Dict[str, Any]) -> str:
        """Format budget information from job details."""
        def format_amount(amount):
            if amount is None:
                return 'N/A'
            try:
                amount_str = str(amount)
                # Remove trailing .0 if it's a whole number
                if '.' in amount_str and amount_str.endswith('0'):
                    return amount_str.split('.')[0]
                return amount_str
            except (TypeError, ValueError):
                return 'N/A'
        
        # Check for hourly rate first in the new format
        if 'hourlyBudget' in job and job['hourlyBudget']:
            min_rate = format_amount(job['hourlyBudget'].get('min'))
            max_rate = format_amount(job['hourlyBudget'].get('max'))
            if min_rate != 'N/A' and max_rate != 'N/A' and min_rate != max_rate:
                return f"💵 ${min_rate}-{max_rate}/hr"
            elif min_rate != 'N/A':
                return f"💵 ${min_rate}/hr"
        
        # Check for fixed price in the new format
        if 'budget' in job and job['budget']:
            amount = format_amount(job['budget'].get('amount'))
            if amount != 'N/A':
                return f"💰 ${amount} (Fixed)"
                
        # Check for hourly rate in the old format
        if 'hourlyBudgetMin' in job and job['hourlyBudgetMin']:
            min_rate = format_amount(job['hourlyBudgetMin'].get('amount') or job['hourlyBudgetMin'].get('displayValue', '').replace('$', '').replace('/hr', '').strip())
            max_rate = format_amount(job.get('hourlyBudgetMax', {}).get('amount') or job.get('hourlyBudgetMax', {}).get('displayValue', '').replace('$', '').replace('/hr', '').strip())
            if min_rate != 'N/A' and max_rate != 'N/A' and min_rate != max_rate:
                return f"💵 ${min_rate}-{max_rate}/hr"
            elif min_rate != 'N/A':
                return f"💵 ${min_rate}/hr"
                
        # Check for fixed price in the old format
        if 'amount' in job and job['amount']:
            amount = format_amount(job['amount'].get('amount') or job['amount'].get('displayValue', '').replace('$', '').strip())
            if amount != 'N/A':
                return f"💰 ${amount} (Fixed)"
        
        # Check for budget range in the new format
        if 'budgetRange' in job and job['budgetRange']:
            min_budget = format_amount(job['budgetRange'].get('min') or job['budgetRange'].get('rangeStart'))
            max_budget = format_amount(job['budgetRange'].get('max') or job['budgetRange'].get('rangeEnd'))
            if min_budget != 'N/A' and max_budget != 'N/A' and min_budget != max_budget:
                return f"💰 ${min_budget}-{max_budget} (Fixed)"
            elif min_budget != 'N/A':
                return f"💰 ${min_budget}+ (Fixed)"
                
        # If no budget information is found, check for rate info in the job title or description
        title = str(job.get('title', '')).lower()
        description = str(job.get('description', '')).lower()
        
        # Look for hourly rates in the title or description
        import re
        hourly_match = re.search(r'\$([0-9,.]+)/hr', title) or re.search(r'\$([0-9,.]+)/hr', description)
        if hourly_match:
            rate = format_amount(hourly_match.group(1).replace(',', ''))
            if rate != 'N/A':
                return f"💵 ${rate}/hr"
                
        # Look for fixed prices in the title or description
        fixed_match = re.search(r'\$([0-9,]+)(?:\s*-\s*\$?([0-9,]+))?', title) or re.search(r'\$([0-9,]+)(?:\s*-\s*\$?([0-9,]+))?', description)
        if fixed_match:
            min_price = format_amount(fixed_match.group(1).replace(',', ''))
            max_price = format_amount(fixed_match.group(2).replace(',', '')) if fixed_match.group(2) else None
            if min_price != 'N/A' and max_price and max_price != 'N/A' and min_price != max_price:
                return f"💰 ${min_price}-{max_price} (Fixed)"
            elif min_price != 'N/A':
                return f"💰 ${min_price} (Fixed)"
                
        return "💸 Rate: Not specified"

    def _format_client_info(self, client: Optional[Dict[str, Any]]) -> str:
        """Format essential client information including rating and job stats."""
        if not client or not isinstance(client, dict):
            return "👤 New client (no info)"
            
        lines = []
        
        # Basic client info with rating
        client_info = []
        if client.get('verificationStatus') == 'VERIFIED':
            client_info.append("✅ Verified client")
            
        # Add client rating from totalFeedback
        total_feedback = client.get('totalFeedback')
        if total_feedback:
            try:
                # Extract the numeric rating (e.g., "4.87" from "4.87 of 5" or just "4.87")
                rating_str = str(total_feedback).split()[0]  # Get first part in case it's "4.87 of 5"
                rating = float(rating_str)
                client_info.append(f"⭐ {rating:.1f}")
            except (ValueError, AttributeError):
                pass
                
        if client_info:
            lines.append(" • ".join(client_info))
            
        # Job statistics
        hires = int(client.get('totalHires') or 0)
        posted = int(client.get('totalPostedJobs') or 0)
        
        # Calculate hire rate if possible
        hire_rate = None
        if posted > 0:
            hire_rate = (hires / posted) * 100
        
        # Add job stats
        stats = []
        if posted > 0:
            stats.append(f"📊 {posted} jobs")
        if hires > 0:
            stats.append(f"👥 {hires} hires")
        if hire_rate is not None:
            stats.append(f"🎯 {hire_rate:.0f}% hire rate")
        if stats:
            lines.append(" • ".join(stats))
            
        # Add total spent information with rounded value
        spent = client.get('totalSpent', {})
        if isinstance(spent, dict):
            display_value = spent.get('displayValue')
            if display_value:
                try:
                    # Extract the numeric value and round it
                    amount_str = ''.join(c for c in display_value if c.isdigit() or c == '.')
                    if amount_str:
                        amount = float(amount_str)
                        # Format with K/M suffix if needed
                        if amount >= 1_000_000:
                            amount_str = f"${amount/1_000_000:.1f}M"
                        elif amount >= 1_000:
                            amount_str = f"${amount/1_000:.0f}K"
                        else:
                            amount_str = f"${amount:.0f}"
                        lines.append(f"💳 {amount_str} total spent")
                except (ValueError, TypeError):
                    lines.append(f"💳 {display_value} total spent")
        
        return "\n".join(lines)

    def _format_job_type(self, job: Dict[str, Any]) -> str:
        """Format job type information."""
        job_type = job.get('jobType', '').lower()
        if 'hourly' in job_type:
            return "⏱️ Hourly"
        elif 'fixed' in job_type:
            return "📌 Fixed Price"
        return "📋 Project"

    def _format_posted_time(self, created_time: str) -> str:
        """Format the posted time to be more readable."""
        if not created_time:
            return "🕒 Just now"
            
        from datetime import datetime, timezone
        try:
            # Parse the ISO format time
            dt = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            delta = now - dt
            
            if delta.days > 0:
                return f"📅 {delta.days} day{'s' if delta.days > 1 else ''} ago"
            elif delta.seconds >= 3600:
                hours = delta.seconds // 3600
                return f"🕒 {hours} hour{'s' if hours > 1 else ''} ago"
            else:
                minutes = delta.seconds // 60
                return f"🕒 {minutes} minute{'s' if minutes > 1 else ''} ago"
        except (ValueError, TypeError):
            return f"📅 {created_time}"

    def _clean_description(self, description: str) -> str:
        """Clean and format job description."""
        if not description or not isinstance(description, str):
            return ""
            
        import re
        from html import unescape
        
        try:
            # Remove HTML tags and decode HTML entities
            clean = re.sub(r'<[^>]+>', ' ', description)
            clean = unescape(clean)
            
            # Replace multiple spaces and newlines with single space
            clean = re.sub(r'\s+', ' ', clean).strip()
            
            # Truncate if too long
            max_length = 250
            if len(clean) > max_length:
                clean = clean[:max_length].rsplit(' ', 1)[0] + '...'
                
            return clean
        except Exception as e:
            logger.warning(f"Failed to clean description: {e}")
            return description[:200] + '...' if len(description) > 200 else description

    def send_job_notification(self, job: Dict[str, Any], job_analysis=None) -> bool:
        """Send a notification for a new job posting.
        
        Args:
            job: Job details dictionary
            job_analysis: Optional JobAnalysis object with AI insights
            
        Returns:
            bool: True if the notification was sent successfully, False otherwise
        """
        if not job or not isinstance(job, dict):
            logger.error("Invalid job data provided")
            return False
            
        try:
            job_id = str(job.get('id') or 'unknown').strip()
            job_title = str(job.get('title') or 'Untitled Job').strip()
            
            # Safely get client info
            client = job.get('client')
            if not isinstance(client, dict):
                client = {}
            
            # Format notification components
            budget = self._format_budget(job)
            client_info = self._format_client_info(client)
            job_type = self._format_job_type(job)
            posted_time = self._format_posted_time(job.get('createdDateTime'))
            
            # Get number of applicants if available
            try:
                applicants = str(job.get('totalApplicants', '?'))
            except (TypeError, ValueError):
                applicants = '?'
            
            # Build notification message with rich formatting
            message_parts = [
                f"📢 <b>{job_title}</b>",
                "",  # Empty line for better readability
            ]
            
            # Add AI analysis if available
            if job_analysis:
                score_emoji = "🔥" if job_analysis.score >= 8 else "⭐" if job_analysis.score >= 6 else "📊"
                message_parts.extend([
                    f"{score_emoji} <b>AI Score: {job_analysis.score}/10</b>",
                    f"📝 {job_analysis.summary}",
                    ""
                ])
            
            message_parts.extend([
                f"{budget} • {job_type}",
                f"{client_info}",
                f"{posted_time} • {applicants} proposals",
            ])
            
            # Add AI proposal script if available
            if job_analysis and job_analysis.proposal_script:
                message_parts.extend([
                    "",
                    f"🎬 <b>Proposal Script:</b>",
                    f"<i>{job_analysis.proposal_script[:300]}{'...' if len(job_analysis.proposal_script) > 300 else ''}</i>"
                ])
            else:
                # Add job description if available and no AI analysis
                description = self._clean_description(job.get('description'))
                if description:
                    message_parts.extend(["", description])
            
            # Add job URL if available
            job_url = None
            if job_id and job_id != 'unknown':
                job_url = f"https://www.upwork.com/jobs/~02{job_id}"
            
            # Create notification title with AI score if available
            if job_analysis:
                title = f"🚀 New Job Match! ({job_analysis.score}/10)"
                # Adjust priority and sound based on AI score
                priority = 2 if job_analysis.score >= 9 else 1  # Emergency priority for 9+ scores
                sound = "siren" if job_analysis.score >= 9 else "cashregister"
            else:
                title = "🚀 New Job Match!"
                priority = 1
                sound = "cashregister"
            
            # Send the notification to all devices
            return self.send_notification(
                title=title,
                message="\n".join(message_parts),
                url=job_url,
                url_title="🔍 View on Upwork" if job_url else None,
                priority=priority,
                sound=sound,
                html=1,  # Enable HTML formatting
                retry=30,  # Retry every 30 seconds if not acknowledged
                expire=300  # Stop retrying after 5 minutes
            )
            
        except Exception as e:
            logger.error(f"Failed to format job notification: {e}", exc_info=True)
            return False
