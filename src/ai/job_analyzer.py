"""AI-powered job analysis using OpenAI GPT models."""

import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import openai
from openai import OpenAI

try:
    from config.settings import settings
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from config.settings import settings

logger = logging.getLogger(__name__)

@dataclass
class JobAnalysis:
    """Data class for job analysis results."""
    job_id: str
    summary: str
    score: int
    proposal_script: str
    analysis_timestamp: datetime
    reasoning: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "job_id": self.job_id,
            "summary": self.summary,
            "score": self.score,
            "proposal_script": self.proposal_script,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
            "reasoning": self.reasoning
        }

class JobAnalyzer:
    """AI-powered job analyzer using OpenAI."""
    
    def __init__(self):
        """Initialize the job analyzer."""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY.get_secret_value())
        self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
        self.temperature = getattr(settings, 'OPENAI_TEMPERATURE', 0.3)
        self.max_tokens = getattr(settings, 'OPENAI_MAX_TOKENS', 1000)
        
        logger.info(f"JobAnalyzer initialized with model: {self.model}")
    
    def analyze_job(self, job: Dict[str, Any]) -> Optional[JobAnalysis]:
        """
        Analyze a job posting using AI.
        
        Args:
            job: Job data dictionary from Upwork API
            
        Returns:
            JobAnalysis object with summary, score, and proposal script
        """
        try:
            job_id = job.get('id', 'unknown')
            logger.info(f"Analyzing job {job_id} with AI")
            
            # Build the prompt
            prompt = self._build_analysis_prompt(job)
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert freelancer and proposal writer who helps evaluate Upwork job postings."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Parse the response
            analysis_text = response.choices[0].message.content.strip()
            summary, score, proposal_script, reasoning = self._parse_analysis_response(analysis_text)
            
            analysis = JobAnalysis(
                job_id=job_id,
                summary=summary,
                score=score,
                proposal_script=proposal_script,
                analysis_timestamp=datetime.now(),
                reasoning=reasoning
            )
            
            logger.info(f"Job {job_id} analyzed - Score: {score}/10")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze job {job.get('id', 'unknown')}: {e}", exc_info=True)
            return None
    
    def _build_analysis_prompt(self, job: Dict[str, Any]) -> str:
        """Build the analysis prompt from job data."""
        # Extract job information safely
        title = job.get('title', 'N/A')
        description = job.get('description', 'N/A')
        
        # Extract budget information
        hourly_min = job.get('hourlyBudgetMin', {}) or {}
        hourly_max = job.get('hourlyBudgetMax', {}) or {}
        amount = job.get('amount', {}) or {}
        
        budget_info = "Not specified"
        if hourly_min.get('displayValue') and hourly_max.get('displayValue'):
            budget_info = f"Hourly: {hourly_min.get('displayValue')} - {hourly_max.get('displayValue')}"
        elif amount.get('displayValue'):
            budget_info = f"Fixed: {amount.get('displayValue')}"
        
        # Extract client information
        client = job.get('client', {}) or {}
        client_reviews = client.get('totalReviews', 0)
        client_spent = (client.get('totalSpent') or {}).get('displayValue', 'N/A')
        client_hires = client.get('totalHires', 'N/A')
        verification_status = client.get('verificationStatus', 'N/A')
        
        # Extract skills
        skills = job.get('skills', []) or []
        skills_text = ', '.join([skill.get('name', '') for skill in skills if skill.get('name')])
        
        prompt = f"""You are an expert proposal writer analyzing a job posting.

Job Post:
---
Title: {title}
Description: {description}
Budget: {budget_info}
Skills Required: {skills_text}
Client Info: {client_reviews} reviews, Spent: {client_spent}, Hires: {client_hires}, Verification: {verification_status}
---

Please provide your analysis in the following format:

SUMMARY:
[Write a concise 2-3 sentence summary of what the job entails]

SCORE:
[Provide a score from 0-10 based on job quality, budget reasonableness, client reliability, and project clarity. Consider: clear requirements, fair budget, good client history, interesting work]

PROPOSAL_SCRIPT:
[Write a compelling 30-second video proposal script that would win this job. Be specific about relevant experience and value proposition]

REASONING:
[Briefly explain why you gave this score, highlighting key factors that influenced your decision]"""

        return prompt
    
    def _parse_analysis_response(self, response: str) -> Tuple[str, int, str, str]:
        """Parse the AI response into components."""
        try:
            lines = response.strip().split('\n')
            summary = ""
            score = 5  # default score
            proposal_script = ""
            reasoning = ""
            
            current_section = None
            
            for line in lines:
                line = line.strip()
                if line.upper().startswith('SUMMARY:'):
                    current_section = 'summary'
                    summary = line[8:].strip()
                elif line.upper().startswith('SCORE:'):
                    current_section = 'score'
                    score_text = line[6:].strip()
                    # Extract number from score text
                    import re
                    score_match = re.search(r'(\d+)', score_text)
                    if score_match:
                        score = min(10, max(0, int(score_match.group(1))))
                elif line.upper().startswith('PROPOSAL_SCRIPT:'):
                    current_section = 'proposal'
                    proposal_script = line[16:].strip()
                elif line.upper().startswith('REASONING:'):
                    current_section = 'reasoning'
                    reasoning = line[10:].strip()
                elif line and current_section:
                    # Continue building the current section
                    if current_section == 'summary':
                        summary += " " + line
                    elif current_section == 'proposal':
                        proposal_script += " " + line
                    elif current_section == 'reasoning':
                        reasoning += " " + line
            
            # Clean up text
            summary = summary.strip()
            proposal_script = proposal_script.strip()
            reasoning = reasoning.strip()
            
            # Fallbacks
            if not summary:
                summary = "Job analysis summary not available"
            if not proposal_script:
                proposal_script = "Proposal script not generated"
            if not reasoning:
                reasoning = "Scoring reasoning not provided"
                
            return summary, score, proposal_script, reasoning
            
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            return "Failed to parse job summary", 5, "Failed to generate proposal script", "Analysis parsing failed"
    
    def should_notify(self, analysis: JobAnalysis) -> bool:
        """Determine if a job should trigger a notification based on score."""
        min_score = getattr(settings, 'MIN_NOTIFICATION_SCORE', 7)
        return analysis.score >= min_score