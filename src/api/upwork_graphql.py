"""Upwork GraphQL API client implementation."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Union
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import settings from the config package
try:
    from config.settings import settings
except ImportError:
    # Fallback for direct script execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from config.settings import settings

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
        from config import settings
        
        self.access_token = settings.UPWORK_ACCESS_TOKEN
        if not self.access_token:
            raise ValueError("UPWORK_ACCESS_TOKEN is not set in settings")
            
        self.endpoint = settings.UPWORK_GRAPHQL_ENDPOINT
        self.session = self._create_session()
        
        # Log initialization (for debugging)
        logger.info("UpworkGraphQLClient initialized with endpoint: %s", self.endpoint)
        
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
        """Get the headers for API requests."""
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
        
    def search_jobs(self, query: str, hourly_rate_min: int = 30, budget_min: int = 500, limit: int = 10) -> List[Dict]:
        """Search for jobs on Upwork using the GraphQL API.
        
        Args:
            query: Search query string (e.g., "wordpress")
            hourly_rate_min: Minimum hourly rate to filter by (default: 30)
            budget_min: Minimum fixed-price budget (default: 500)
            limit: Maximum number of results to return (default: 10, max: 100)
            
        Returns:
            List of job postings
            
        Raises:
            UpworkAPIError: If there's an error with the API request
        """
        # Build the query with inline arguments
        graphql_query = f"""
        query {{
          marketplaceJobPostingsSearch(
            marketPlaceJobFilter: {{
              titleExpression_eq: "{query}"
              hourlyRate_eq: {{rangeStart: {hourly_rate_min}}}  # Minimum hourly rate
              budgetRange_eq: {{rangeStart: {budget_min}}}  # Minimum fixed-price budget
              pagination_eq: {{first: {min(limit, 100)}, after: "0"}}
            }}
            searchType: USER_JOBS_SEARCH
            sortAttributes: [{{field: RECENCY}}]
          ) {{
            edges {{
              node {{
                ciphertext
                id
                title
                description
                hourlyBudgetMin {{
                  displayValue
                }}
                hourlyBudgetMax {{
                  displayValue
                }}
                createdDateTime
                duration
                experienceLevel
                amount {{
                  displayValue
                }}
                client {{
                  totalReviews
                  totalFeedback
                  verificationStatus
                  totalPostedJobs
                  totalHires
                  totalSpent {{
                    displayValue
                  }}
                }}
                totalApplicants
              }}
            }}
            pageInfo {{
              hasNextPage
              endCursor
            }}
          }}
        }}
        """
        
        # No variables needed since we're using string interpolation
        variables = {}
        
        try:
            logger.info(f"Searching for jobs with query: {query}, min rate: ${hourly_rate_min}/hr")
            result = self._execute_query(graphql_query, variables)
            
            # Extract job nodes from the response and sort by creation date (newest first)
            edges = result.get('data', {}).get('marketplaceJobPostingsSearch', {}).get('edges', [])
            jobs = [edge.get('node', {}) for edge in edges if edge and 'node' in edge]
            
            # Sort jobs by creation date in descending order (newest first)
            jobs.sort(key=lambda x: x.get('createdDateTime', ''), reverse=True)
            
            logger.info(f"Found {len(jobs)} jobs matching the criteria")
            return jobs
            
        except UpworkAuthenticationError as e:
            logger.error(f"Authentication error while searching jobs: {e}")
            raise
        except UpworkAPIError as e:
            logger.error(f"API error while searching jobs: {e}")
            raise
        except Exception as e:
            logger.exception("Unexpected error while searching jobs")
            raise UpworkAPIError(f"Failed to search jobs: {str(e)}") from e

    def _execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Execute a GraphQL query using the Upwork API.
        
        Args:
            query: The GraphQL query string
            variables: Optional variables for the query
            
        Returns:
            The parsed JSON response
            
        Raises:
            UpworkAuthenticationError: If authentication fails
            UpworkAPIError: For other API errors
        """
        # Prepare the request data
        data = {
            "query": query,
            "variables": variables or {}
        }
        
        try:
            # Make the POST request to the GraphQL endpoint using the session
            response = self.session.post(
                self.endpoint,
                headers=self._get_headers(),
                json=data,
                timeout=30
            )
            
            # Check for authentication errors
            if response.status_code == 401:
                raise UpworkAuthenticationError("Invalid or expired access token")
                
            # Check for other HTTP errors
            response.raise_for_status()
            
            # Parse the JSON response
            response_data = response.json()
            
            # Check for GraphQL errors in the response
            if "errors" in response_data:
                error_messages = [e.get("message", "Unknown error") 
                               for e in response_data.get("errors", [])]
                raise UpworkAPIError(f"GraphQL errors: {', '.join(error_messages)}")
                
            return response_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    logger.error(f"Response content: {e.response.text}")
                except:
                    pass
            raise UpworkAPIError(f"API request failed: {e}") from e

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
