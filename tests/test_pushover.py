#!/usr/bin/env python3
"""Test Pushover notification service."""
import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.notifications.pushover import PushoverNotifier

def main():
    """Test sending a Pushover notification."""
    # Load environment variables
    load_dotenv()
    
    # Get Pushover credentials from environment
    api_token = os.getenv("PUSHOVER_API_TOKEN")
    user_key = os.getenv("PUSHOVER_USER_KEY")
    
    if not api_token or not user_key:
        print("Error: Missing Pushover API token or user key in .env file")
        return
    
    print(f"Testing Pushover notification with token: {api_token[:5]}...")
    print(f"Sending to user: {user_key}")
    
    # Initialize the notifier
    notifier = PushoverNotifier(api_token=api_token, user_key=user_key)
    
    # Send a test message
    success = notifier.send_notification(
        title="✅ Upwork Job Sniper Test",
        message="This is a test notification from Upwork Job Sniper. If you see this, Pushover is working correctly!",
        priority=1,
        sound="magic"
    )
    
    if success:
        print("✅ Test notification sent successfully!")
    else:
        print("❌ Failed to send test notification")

if __name__ == "__main__":
    main()
