"""
OAuth2 token management for Upwork API.
"""
import os
import base64
from typing import Tuple, Optional, Dict, Any
import requests
from dotenv import load_dotenv, set_key
from pathlib import Path

# Load environment variables
load_dotenv()

def get_auth_header() -> str:
    """Generate the Basic Auth header for OAuth2 token requests."""
    client_id = os.getenv("UPWORK_API_KEY")
    client_secret = os.getenv("UPWORK_API_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError("Missing UPWORK_API_KEY or UPWORK_API_SECRET in environment variables")
    
    auth_string = f"{client_id}:{client_secret}"
    auth_bytes = auth_string.encode('ascii')
    return base64.b64encode(auth_bytes).decode('ascii')

def refresh_access_token() -> bool:
    """
    Refresh the OAuth2 access token using the refresh token.
    
    Returns:
        bool: True if token was refreshed successfully, False otherwise
    """
    refresh_token = os.getenv("UPWORK_ACCESS_TOKEN_REFRESH")
    if not refresh_token:
        print("Error: No refresh token found in environment variables")
        return False

    token_url = "https://www.upwork.com/api/v3/oauth2/token"
    headers = {
        "Authorization": f"Basic {get_auth_header()}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    # Get client_id for the request
    client_id = os.getenv("UPWORK_API_KEY")
    
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id
    }

    try:
        response = requests.post(token_url, headers=headers, data=data, timeout=30)
        response.raise_for_status()
        
        token_data = response.json()
        
        # Update .env file with new tokens
        env_path = Path(__file__).parent.parent.parent / ".env"
        set_key(env_path, "UPWORK_ACCESS_TOKEN", token_data["access_token"])
        set_key(env_path, "UPWORK_ACCESS_TOKEN_REFRESH", token_data["refresh_token"])
        
        # Update environment variables for current session
        os.environ["UPWORK_ACCESS_TOKEN"] = token_data["access_token"]
        os.environ["UPWORK_ACCESS_TOKEN_REFRESH"] = token_data["refresh_token"]
        
        print("✅ Successfully refreshed access token")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to refresh access token: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Status code: {e.response.status_code}")
            print(f"Response: {e.response.text}")
        return False
