"""Upwork GraphQL API client implementation with token management."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import settings and token manager
try:
    from config.settings import settings
    from src.utils.token_manager import TokenManager
except ImportError:
    # Fallback for direct script execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from config.settings import settings
    from src.utils.token_manager import TokenManager

logger = logging.getLogger(__name__)

class UpworkAPIError(Exception):
    """Base exception for Upwork API errors."""
    pass

class UpworkAuthenticationError(UpworkAPIError):
    """Raised when authentication with Upwork API fails."""
    pass

class UpworkGraphQLClient:
    """Client for interacting with Upwork's GraphQL API."""

    def __init__(self):
        """Initialize the Upwork GraphQL client with OAuth2 authentication."""
        self.token_manager = TokenManager()
        self.endpoint = settings.UPWORK_GRAPHQL_ENDPOINT
        self.session = self._create_session()
        self._last_token_refresh = 0
        self._token_refresh_interval = 3000  # 50 minutes in seconds
        
        # Log initialization (for debugging)
        logger.info("UpworkGraphQLClient initialized with endpoint: %s", self.endpoint)
    
    def _ensure_valid_token(self) -> None:
        """Ensure the current access token is valid, refresh if needed."""
        current_time = time.time()
        
        # Only attempt to refresh if enough time has passed since last refresh
        if current_time - self._last_token_refresh < self._token_refresh_interval:
            return
        
        try:
            success, message = self.token_manager.refresh_access_token()
            if success:
                logger.info("Successfully refreshed access token")
                self._last_token_refresh = current_time
            else:
                logger.warning("Failed to refresh access token: %s", message)
        except Exception as e:
            logger.error("Error refreshing access token: %s", str(e), exc_info=True)
    
    @property
    def access_token(self) -> str:
        """Get the current access token, refreshing if needed."""
        self._ensure_valid_token()
        return self.token_manager.get_access_token()
        
    def _create_session(self):
        """Create a requests session with retry logic."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        return session
        
    def _get_headers(self) -> Dict[str, str]:
        """Get the headers for API requests with the current access token."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Upwork-API-Version": "1.0",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }
        
    def execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """
        Execute a GraphQL query.
        
        Args:
            query: The GraphQL query string
            variables: Optional variables for the query
            
        Returns:
            Dict containing the response data
            
        Raises:
            UpworkAuthenticationError: If authentication fails
            UpworkAPIError: For other API errors
        """
        try:
            response = self.session.post(
                self.endpoint,
                headers=self._get_headers(),
                json={"query": query, "variables": variables or {}}
            )
            
            # Handle authentication errors
            if response.status_code == 401:
                raise UpworkAuthenticationError("Invalid or expired access token")
                
            response.raise_for_status()
            result = response.json()
            
            # Check for GraphQL errors
            if 'errors' in result:
                error_messages = [e.get('message', 'Unknown error') for e in result.get('errors', [])]
                raise UpworkAPIError(f"GraphQL error: {', '.join(error_messages)}")
                
            return result
            
        except requests.exceptions.RequestException as e:
            raise UpworkAPIError(f"Request failed: {str(e)}")
    
    def get_organization(self) -> Dict[str, Any]:
        """
        Get organization information for the authenticated user.
        
        Returns:
            Dict containing organization details
        """
        query = """
        query {
          organization {
            id
            name
          }
        }
        """
        result = self.execute_query(query)
        return result.get('data', {}).get('organization', {})
        
    def search_jobs(
        self,
        query: str = "wordpress",
        hourly_rate_min: int = 30,
        budget_min: int = 500,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for jobs matching the given criteria.
        
        Args:
            query: Search query string (default: "wordpress")
            hourly_rate_min: Minimum hourly rate (default: 30)
            budget_min: Minimum project budget (default: 500)
            limit: Maximum number of results to return (default: 10)
            
        Returns:
            List of job dictionaries
        """
        try:
            # Ensure we have a valid token before making the request
            self._ensure_valid_token()
            
            # Build the GraphQL query
            query_str = """
            query GetJobs($query: String!, $filters: JobSearchFilters, $paging: Paging) {
                jobs(
                    query: $query,
                    filters: $filters,
                    paging: $paging
                ) {
                    nodes {
                        id
                        title
                        description
                        createdDateTime
                        skills {
                            name
                        }
                        client {
                            name
                            location {
                                country
                            }
                        }
                        amount {
                            amount
                            currency
                            type
                        }
                        duration
                        workload
                        status
                    }
                }
            }
            """
            
            variables = {
                "query": query,
                "filters": {
                    "hourlyRate": {"min": hourly_rate_min},
                    "budget": {"min": budget_min},
                    "jobType": "hourly,fixed"
                },
                "paging": {
                    "first": limit
                }
            }
            
            # Execute the query
            response = self._execute_query(query_str, variables)
            
            # Process the response
            jobs = response.get('data', {}).get('jobs', {}).get('nodes', [])
            
            # Sort jobs by creation date in descending order (newest first)
            jobs.sort(key=lambda x: x.get('createdDateTime', ''), reverse=True)
            
            logger.info(f"Found {len(jobs)} jobs matching the criteria")
            return jobs
            
        except UpworkAuthenticationError as e:
            logger.error(f"Authentication error while searching jobs: {e}")
            raise
        except Exception as e:
            logger.exception("Error while searching jobs")
            raise UpworkAPIError(f"Failed to search jobs: {str(e)}") from e

    def _execute_query(self, query: str, variables: Optional[Dict] = None, retry_on_auth: bool = True) -> Dict:
        """Execute a GraphQL query using the Upwork API with automatic token refresh.
        
        Args:
            query: The GraphQL query string
            variables: Optional variables for the query
            retry_on_auth: Whether to retry once on authentication error
            
        Returns:
            The parsed JSON response
            
        Raises:
            UpworkAuthenticationError: If authentication fails after retry
            UpworkAPIError: For other API errors
        """
        try:
            # Ensure we have a valid token before making the request
            self._ensure_valid_token()
            
            # Make the POST request to the GraphQL endpoint using the session
            response = self.session.post(
                self.endpoint,
                headers=self._get_headers(),
                json={
                    "query": query,
                    "variables": variables or {}
                },
                timeout=30
            )
            
            # Handle authentication errors
            if response.status_code == 401:
                if retry_on_auth:
                    logger.info("Received 401, attempting to refresh token...")
                    success, message = self.token_manager.refresh_access_token()
                    if success:
                        logger.info("Token refreshed, retrying request...")
                        return self._execute_query(query, variables, retry_on_auth=False)
                raise UpworkAuthenticationError("Authentication failed after token refresh")
                
            # Check for other HTTP errors
            response.raise_for_status()
            
            # Parse the JSON response
            response_data = response.json()
            
            # Check for GraphQL errors in the response
            if "errors" in response_data:
                error_messages = [e.get("message", "Unknown error") 
                               for e in response_data.get("errors", [])]
                error_message = ", ".join(error_messages)
                
                # Handle token expiration in GraphQL errors
                if any("token" in msg.lower() and "expired" in msg.lower() for msg in error_messages) and retry_on_auth:
                    logger.info("Token expired, attempting to refresh...")
                    success, message = self.token_manager.refresh_access_token()
                    if success:
                        logger.info("Token refreshed, retrying request...")
                        return self._execute_query(query, variables, retry_on_auth=False)
                
                raise UpworkAPIError(f"GraphQL errors: {error_message}")
                
            return response_data
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            logger.error(f"Request failed: {error_msg}")
            
            # Add more detailed error information if available
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.text
                    logger.error(f"Response content: {error_detail}")
                    error_msg = f"{error_msg} - {error_detail}"
                except Exception as parse_error:
                    logger.error("Failed to parse error response", exc_info=parse_error)
            
            raise UpworkAPIError(f"API request failed: {error_msg}") from e

    # Removed duplicate search_jobs method to use the GraphQL implementation
    
    def get_job_details(self, job_id: str) -> Dict:
        """Get detailed information about a specific job.
        
        Args:
            job_id: The ID of the job to retrieve
            
        Returns:
            Dictionary containing job details
            
        Raises:
            UpworkAPIError: If there's an error with the API request or job not found
        """
        query = """
        query GetJobDetails($id: ID!) {
            job: node(id: $id) {
                ... on JobPosting {
                    id
                    title
                    description
                    createdDateTime
                    duration
                    experienceLevel
                    amount {
                        displayValue
                    }
                    hourlyBudgetMin {
                        displayValue
                    }
                    hourlyBudgetMax {
                        displayValue
                    }
                    client {
                        totalReviews
                        totalFeedback
                        verificationStatus
                        totalPostedJobs
                        totalHires
                        totalSpent {
                            displayValue
                        }
                    }
                    totalApplicants
                    skills {
                        name
                        category
                    }
                    category {
                        name
                    }
                    subcategory {
                        name
                    }
                }
            }
        }
        """
        
        try:
            logger.info(f"Fetching details for job ID: {job_id}")
            result = self._execute_query(query, {"id": job_id})
            
            # Extract the job data from the response
            job_data = result.get('data', {}).get('job')
            if not job_data:
                logger.warning(f"No job found with ID: {job_id}")
                raise UpworkAPIError(f"Job with ID {job_id} not found")
                
            logger.info(f"Successfully retrieved details for job: {job_data.get('title')}")
            return job_data
            
        except Exception as e:
            logger.error(f"Error retrieving job details: {e}")
            if isinstance(e, UpworkAPIError):
                raise
            raise UpworkAPIError(f"Failed to retrieve job details: {str(e)}") from e


# Create a singleton instance for easier imports
upwork_client = UpworkGraphQLClient()
