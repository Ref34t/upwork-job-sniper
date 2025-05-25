"""Tests for the Upwork GraphQL API client."""
import os
from unittest.mock import MagicMock, patch, ANY

import pytest
from dotenv import load_dotenv

from src.api.upwork_graphql import UpworkGraphQLClient, UpworkAuthenticationError, UpworkAPIError

# Load environment variables for testing
load_dotenv()

class TestUpworkGraphQLClient:
    """Test cases for the UpworkGraphQLClient class."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock for requests.Session."""
        with patch('requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_response = MagicMock()
            mock_session.post.return_value = mock_response
            yield mock_session, mock_response

    @pytest.fixture
    def graphql_client(self, mock_session):
        """Create an instance of UpworkGraphQLClient with test settings."""
        client = UpworkGraphQLClient()
        # Replace the session with our mock
        mock_session, _ = mock_session
        client.session = mock_session
        return client

    def test_get_organization_success(self, graphql_client, mock_session):
        """Test successful retrieval of organization information."""
        # Get the mock session and response
        _, mock_response = mock_session
        
        # Mock successful response
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "organization": {
                    "id": "test_org_id",
                    "name": "Test Organization"
                }
            }
        }

        # Call the method
        result = graphql_client.get_organization()

        # Assertions
        assert result == {"id": "test_org_id", "name": "Test Organization"}
        graphql_client.session.post.assert_called_once()

    def test_authentication_error(self, graphql_client, mock_session):
        """Test handling of authentication errors."""
        # Get the mock response
        _, mock_response = mock_session
        
        # Mock authentication error
        mock_response.status_code = 401

        # Assert that authentication error is raised
        with pytest.raises(UpworkAuthenticationError):
            graphql_client.get_organization()
            
        # Verify the session.post was called
        graphql_client.session.post.assert_called_once()

    def test_api_error(self, graphql_client, mock_session):
        """Test handling of API errors."""
        # Get the mock response
        _, mock_response = mock_session
        
        # Mock API error
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errors": [{"message": "Test error"}]
        }

        # Assert that API error is raised
        with pytest.raises(UpworkAPIError):
            graphql_client.get_organization()
            
        # Verify the session.post was called
        graphql_client.session.post.assert_called_once()
        
    def test_search_jobs_success(self, graphql_client, mock_session):
        """Test successful job search."""
        # Get the mock response
        _, mock_response = mock_session
        
        # Mock successful response
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "marketplaceJobPostingsSearch": {
                    "edges": [
                        {
                            "node": {
                                "ciphertext": "test_cipher",
                                "id": "test_job_id",
                                "title": "Test Job",
                                "description": "Test job description",
                                "hourlyBudgetMin": {"displayValue": "$30.00"},
                                "hourlyBudgetMax": {"displayValue": "$50.00"},
                                "createdDateTime": "2023-01-01T00:00:00Z",
                                "duration": "1 to 3 months",
                                "experienceLevel": "Intermediate",
                                "amount": {"displayValue": "$1000"},
                                "client": {
                                    "totalReviews": 10,
                                    "totalFeedback": 5,
                                    "verificationStatus": "VERIFIED",
                                    "totalPostedJobs": 20,
                                    "totalHires": 15,
                                    "totalSpent": {"displayValue": "$5000"}
                                },
                                "totalApplicants": 5
                            }
                        }
                    ]
                }
            }
        }
        
        # Call the method
        result = graphql_client.search_jobs("test query")
        
        # Assertions
        assert len(result) == 1
        assert result[0]["id"] == "test_job_id"
        assert result[0]["title"] == "Test Job"
        graphql_client.session.post.assert_called_once()
        
        # Verify the query and variables were passed correctly
        call_args = graphql_client.session.post.call_args
        assert call_args[0][0] == graphql_client.endpoint
        assert call_args[1]["json"]["query"].strip().startswith("query SearchJobs")
        assert call_args[1]["json"]["variables"]["filter"]["titleExpression"]["eq"] == "test query"
        
    def test_get_job_details_success(self, graphql_client, mock_session):
        """Test successful retrieval of job details."""
        # Get the mock response
        _, mock_response = mock_session
        
        # Mock successful response
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "job": {
                    "id": "test_job_id",
                    "title": "Test Job",
                    "description": "Test job description",
                    "createdDateTime": "2023-01-01T00:00:00Z",
                    "duration": "1 to 3 months",
                    "experienceLevel": "Intermediate",
                    "amount": {"displayValue": "$1000"},
                    "hourlyBudgetMin": {"displayValue": "$30.00"},
                    "hourlyBudgetMax": {"displayValue": "$50.00"},
                    "client": {
                        "totalReviews": 10,
                        "totalFeedback": 5,
                        "verificationStatus": "VERIFIED",
                        "totalPostedJobs": 20,
                        "totalHires": 15,
                        "totalSpent": {"displayValue": "$5000"}
                    },
                    "totalApplicants": 5,
                    "skills": [
                        {"name": "Python", "category": "Web Development"},
                        {"name": "Django", "category": "Web Development"}
                    ],
                    "category": {"name": "Web & Mobile Development"},
                    "subcategory": {"name": "Web Development"}
                }
            }
        }
        
        # Call the method
        result = graphql_client.get_job_details("test_job_id")
        
        # Assertions
        assert result["id"] == "test_job_id"
        assert result["title"] == "Test Job"
        assert len(result["skills"]) == 2
        assert result["category"]["name"] == "Web & Mobile Development"
        graphql_client.session.post.assert_called_once()
        
        # Verify the query and variables were passed correctly
        call_args = graphql_client.session.post.call_args
        assert call_args[0][0] == graphql_client.endpoint
        assert call_args[1]["json"]["query"].strip().startswith("query GetJobDetails")
        assert call_args[1]["json"]["variables"]["id"] == "test_job_id"
        
    def test_search_jobs_empty_response(self, graphql_client, mock_session):
        """Test handling of empty response from the API."""
        # Get the mock response
        _, mock_response = mock_session
        
        # Mock empty response
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"marketplaceJobPostingsSearch": {"edges": []}}}
        
        # Call the method
        result = graphql_client.search_jobs("test query")
        
        # Assertions
        assert result == []
        graphql_client.session.post.assert_called_once()
        
    def test_search_jobs_api_error(self, graphql_client, mock_session):
        """Test handling of API errors during job search."""
        # Get the mock response
        _, mock_response = mock_session
        
        # Mock API error
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errors": [{"message": "Test error"}]
        }
        
        # Assert that API error is raised
        with pytest.raises(UpworkAPIError):
            graphql_client.search_jobs("test query")
            
    def test_search_jobs_http_error(self, graphql_client, mock_session):
        """Test handling of HTTP errors during job search."""
        # Get the mock response
        _, mock_response = mock_session
        
        # Mock HTTP error
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Test HTTP error")
        
        # Call the method and expect an exception
        with pytest.raises(UpworkAPIError):
            graphql_client.search_jobs("test query")
