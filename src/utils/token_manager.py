"""Token management utilities for Upwork API."""
import os
import base64
import json
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
import requests
from dotenv import load_dotenv, set_key

class TokenManager:
    """Manages Upwork API token refresh and storage."""
    
    def __init__(self, env_path: str = '.env'):
        """Initialize the token manager with the path to the .env file."""
        self.env_path = Path(env_path)
        self.load_credentials()
        self.token_info = {}
    
    def load_credentials(self) -> None:
        """Load credentials from the .env file."""
        load_dotenv(self.env_path)
        self.client_id = os.getenv('UPWORK_API_KEY')
        self.client_secret = os.getenv('UPWORK_API_SECRET')
        self.access_token = os.getenv('UPWORK_ACCESS_TOKEN', '').strip("'\"")
        self.refresh_token = os.getenv('UPWORK_ACCESS_TOKEN_REFRESH', '').strip("'\"")
    
    def refresh_access_token(self) -> Tuple[bool, str]:
        """Refresh the access token using the refresh token."""
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            return False, "Missing required credentials"
        
        try:
            # Create Basic Auth header
            auth_string = f"{self.client_id}:{self.client_secret}"
            auth_bytes = auth_string.encode('ascii')
            base64_auth = base64.b64encode(auth_bytes).decode('ascii')
            
            # Prepare the request
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {base64_auth}'
            }
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': self.client_id
            }
            
            # Make the request
            response = requests.post(
                'https://www.upwork.com/api/v3/oauth2/token',
                headers=headers,
                data=data,
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.token_info = token_data
                
                # Update the .env file with new tokens
                set_key(
                    self.env_path,
                    'UPWORK_ACCESS_TOKEN',
                    f"'{token_data['access_token']}'"
                )
                
                # Only update refresh token if a new one is provided
                if 'refresh_token' in token_data:
                    set_key(
                        self.env_path,
                        'UPWORK_ACCESS_TOKEN_REFRESH',
                        f"'{token_data['refresh_token']}'"
                    )
                
                return True, "Token refreshed successfully"
            
            return False, f"Failed to refresh token: {response.text}"
            
        except Exception as e:
            return False, f"Error refreshing token: {str(e)}"
    
    def get_access_token(self) -> str:
        """Get the current access token, refreshing if necessary."""
        # For now, just return the current token
        # In a real implementation, you'd check if the token is expired
        return self.access_token

def get_token_manager() -> TokenManager:
    """Get a configured token manager instance."""
    return TokenManager()
