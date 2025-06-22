#!/usr/bin/env python3
"""
Demo script showing AI job analysis functionality.

This script demonstrates how the JobAnalyzer works with sample job data.
Note: Requires OPENAI_API_KEY to be set in environment variables.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.ai.job_analyzer import JobAnalyzer, JobAnalysis
from config.settings import settings

def create_sample_job():
    """Create a sample job for testing."""
    return {
        "id": "demo_job_123",
        "title": "WordPress Developer Needed - Custom Plugin Development",
        "description": """
        We are looking for an experienced WordPress developer to create a custom plugin 
        for our e-commerce website. The plugin should integrate with WooCommerce and 
        provide advanced inventory management features.
        
        Requirements:
        - 3+ years WordPress development experience
        - Strong PHP and MySQL skills
        - Experience with WooCommerce
        - Knowledge of REST APIs
        - Clean, well-documented code
        
        This is a fixed-price project with potential for ongoing work.
        """,
        "hourlyBudgetMin": {"displayValue": "$50"},
        "hourlyBudgetMax": {"displayValue": "$75"},
        "amount": {"displayValue": "$2,500"},
        "client": {
            "totalReviews": 45,
            "totalSpent": {"displayValue": "$25,000"},
            "totalHires": 28,
            "verificationStatus": "VERIFIED",
            "totalFeedback": "4.8"
        },
        "skills": [
            {"name": "WordPress"},
            {"name": "PHP"},
            {"name": "WooCommerce"},
            {"name": "MySQL"},
            {"name": "REST API"}
        ],
        "createdDateTime": "2024-01-15T10:30:00Z",
        "totalApplicants": 8
    }

def demo_ai_analysis():
    """Demonstrate AI job analysis."""
    print("🤖 AI Job Analysis Demo")
    print("=" * 40)
    
    # Check if AI is enabled
    if not settings.ENABLE_AI_ANALYSIS:
        print("❌ AI analysis is disabled. Set ENABLE_AI_ANALYSIS=true to enable.")
        return
    
    try:
        # Initialize the analyzer
        print("🔧 Initializing JobAnalyzer...")
        analyzer = JobAnalyzer()
        print(f"✅ Using model: {analyzer.model}")
        print(f"📊 Notification threshold: {settings.MIN_NOTIFICATION_SCORE}/10")
        print()
        
        # Create sample job
        job = create_sample_job()
        print(f"📋 Analyzing job: {job['title']}")
        print()
        
        # Analyze the job
        print("🧠 Running AI analysis...")
        analysis = analyzer.analyze_job(job)
        
        if analysis:
            print("✅ Analysis completed!")
            print()
            
            # Display results
            print("📊 RESULTS:")
            print("-" * 20)
            print(f"🎯 Score: {analysis.score}/10")
            print(f"📝 Summary: {analysis.summary}")
            print()
            print(f"🎬 Proposal Script:")
            print(f"   {analysis.proposal_script}")
            print()
            print(f"💭 Reasoning: {analysis.reasoning}")
            print()
            
            # Check notification threshold
            should_notify = analyzer.should_notify(analysis)
            if should_notify:
                print(f"🔔 This job WOULD trigger a notification (score {analysis.score} >= {settings.MIN_NOTIFICATION_SCORE})")
            else:
                print(f"🔕 This job would NOT trigger a notification (score {analysis.score} < {settings.MIN_NOTIFICATION_SCORE})")
                
        else:
            print("❌ Analysis failed!")
            
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        print("💡 Make sure OPENAI_API_KEY is set in your .env file")

if __name__ == "__main__":
    demo_ai_analysis()