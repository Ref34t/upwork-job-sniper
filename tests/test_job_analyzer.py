"""Tests for the AI job analyzer module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.ai.job_analyzer import JobAnalyzer, JobAnalysis


class TestJobAnalysis:
    """Test the JobAnalysis data class."""
    
    def test_job_analysis_creation(self):
        """Test creating a JobAnalysis object."""
        analysis = JobAnalysis(
            job_id="test123",
            summary="Test job summary",
            score=8,
            proposal_script="Test proposal script",
            analysis_timestamp=datetime.now(),
            reasoning="Good score because..."
        )
        
        assert analysis.job_id == "test123"
        assert analysis.summary == "Test job summary"
        assert analysis.score == 8
        assert analysis.proposal_script == "Test proposal script"
        assert analysis.reasoning == "Good score because..."
        
    def test_job_analysis_to_dict(self):
        """Test converting JobAnalysis to dictionary."""
        timestamp = datetime.now()
        analysis = JobAnalysis(
            job_id="test123",
            summary="Test summary",
            score=7,
            proposal_script="Test script",
            analysis_timestamp=timestamp
        )
        
        result = analysis.to_dict()
        
        assert result["job_id"] == "test123"
        assert result["summary"] == "Test summary"
        assert result["score"] == 7
        assert result["proposal_script"] == "Test script"
        assert result["analysis_timestamp"] == timestamp.isoformat()


class TestJobAnalyzer:
    """Test the JobAnalyzer class."""
    
    @patch('src.ai.job_analyzer.OpenAI')
    @patch('src.ai.job_analyzer.settings')
    def test_job_analyzer_initialization(self, mock_settings, mock_openai):
        """Test JobAnalyzer initialization."""
        mock_settings.OPENAI_API_KEY.get_secret_value.return_value = "test-key"
        mock_settings.OPENAI_MODEL = "gpt-4o-mini"
        mock_settings.OPENAI_TEMPERATURE = 0.3
        mock_settings.OPENAI_MAX_TOKENS = 1000
        
        analyzer = JobAnalyzer()
        
        assert analyzer.model == "gpt-4o-mini"
        assert analyzer.temperature == 0.3
        assert analyzer.max_tokens == 1000
        mock_openai.assert_called_once_with(api_key="test-key")
    
    @patch('src.ai.job_analyzer.settings')
    def test_should_notify_above_threshold(self, mock_settings):
        """Test should_notify returns True for scores above threshold."""
        mock_settings.MIN_NOTIFICATION_SCORE = 7
        
        with patch('src.ai.job_analyzer.OpenAI'):
            analyzer = JobAnalyzer()
            
        analysis = JobAnalysis(
            job_id="test",
            summary="test",
            score=8,
            proposal_script="test",
            analysis_timestamp=datetime.now()
        )
        
        assert analyzer.should_notify(analysis) is True
    
    @patch('src.ai.job_analyzer.settings')
    def test_should_notify_below_threshold(self, mock_settings):
        """Test should_notify returns False for scores below threshold."""
        mock_settings.MIN_NOTIFICATION_SCORE = 7
        
        with patch('src.ai.job_analyzer.OpenAI'):
            analyzer = JobAnalyzer()
        
        analysis = JobAnalysis(
            job_id="test",
            summary="test",
            score=5,
            proposal_script="test",
            analysis_timestamp=datetime.now()
        )
        
        assert analyzer.should_notify(analysis) is False
    
    def test_parse_analysis_response(self):
        """Test parsing AI response into components."""
        with patch('src.ai.job_analyzer.OpenAI'), \
             patch('src.ai.job_analyzer.settings'):
            analyzer = JobAnalyzer()
        
        response = """
        SUMMARY:
        This is a WordPress development job requiring custom plugin creation.
        
        SCORE:
        8
        
        PROPOSAL_SCRIPT:
        Hi there! I'm excited about your WordPress project. I have 5 years of experience...
        
        REASONING:
        High score due to clear requirements and good budget.
        """
        
        summary, score, script, reasoning = analyzer._parse_analysis_response(response)
        
        assert "WordPress development job" in summary
        assert score == 8
        assert "Hi there!" in script
        assert "High score" in reasoning
    
    def test_parse_analysis_response_with_defaults(self):
        """Test parsing malformed AI response falls back to defaults."""
        with patch('src.ai.job_analyzer.OpenAI'), \
             patch('src.ai.job_analyzer.settings'):
            analyzer = JobAnalyzer()
        
        response = "Invalid response format"
        
        summary, score, script, reasoning = analyzer._parse_analysis_response(response)
        
        assert summary == "Job analysis summary not available"
        assert score == 5  # default score
        assert script == "Proposal script not generated"
        assert reasoning == "Scoring reasoning not provided"
    
    def test_build_analysis_prompt(self):
        """Test building analysis prompt from job data."""
        with patch('src.ai.job_analyzer.OpenAI'), \
             patch('src.ai.job_analyzer.settings'):
            analyzer = JobAnalyzer()
        
        job = {
            "title": "WordPress Developer Needed",
            "description": "Need help with custom plugin",
            "hourlyBudgetMin": {"displayValue": "$50"},
            "hourlyBudgetMax": {"displayValue": "$75"},
            "client": {
                "totalReviews": 25,
                "totalSpent": {"displayValue": "$5,000"},
                "totalHires": 12,
                "verificationStatus": "VERIFIED"
            },
            "skills": [{"name": "WordPress"}, {"name": "PHP"}]
        }
        
        prompt = analyzer._build_analysis_prompt(job)
        
        assert "WordPress Developer Needed" in prompt
        assert "Need help with custom plugin" in prompt
        assert "Hourly: $50 - $75" in prompt
        assert "25 reviews" in prompt
        assert "WordPress, PHP" in prompt
    
    @patch('src.ai.job_analyzer.OpenAI')
    @patch('src.ai.job_analyzer.settings')
    def test_analyze_job_success(self, mock_settings, mock_openai):
        """Test successful job analysis."""
        # Setup mocks
        mock_settings.OPENAI_API_KEY.get_secret_value.return_value = "test-key"
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
        SUMMARY:
        Great WordPress job with clear requirements.
        
        SCORE:
        8
        
        PROPOSAL_SCRIPT:
        I'd love to help with your WordPress project!
        
        REASONING:
        Good client history and fair budget.
        """
        mock_client.chat.completions.create.return_value = mock_response
        
        analyzer = JobAnalyzer()
        
        job = {
            "id": "test123",
            "title": "WordPress Developer",
            "description": "Need WordPress help"
        }
        
        result = analyzer.analyze_job(job)
        
        assert result is not None
        assert result.job_id == "test123"
        assert result.score == 8
        assert "Great WordPress job" in result.summary
        assert "I'd love to help" in result.proposal_script
    
    @patch('src.ai.job_analyzer.OpenAI')
    @patch('src.ai.job_analyzer.settings')
    def test_analyze_job_api_error(self, mock_settings, mock_openai):
        """Test job analysis with API error."""
        mock_settings.OPENAI_API_KEY.get_secret_value.return_value = "test-key"
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        # Mock API error
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        analyzer = JobAnalyzer()
        
        job = {"id": "test123", "title": "Test Job"}
        
        result = analyzer.analyze_job(job)
        
        assert result is None