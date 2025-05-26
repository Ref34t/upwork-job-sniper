"""Test real Upwork API connection."""
import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def check_environment():
    """Check if required environment variables are set."""
    required_vars = [
        'UPWORK_API_KEY',
        'UPWORK_API_SECRET',
        'UPWORK_ACCESS_TOKEN',
        'UPWORK_ACCESS_TOKEN_REFRESH',
        'UPWORK_ORGANIZATION_ID'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error("Missing required environment variables: %s", ", ".join(missing_vars))
        logger.info("Please add them to your .env file and try again.")
        return False
    
    logger.info("All required environment variables are set.")
    return True

async def test_upwork_connection():
    """Test the Upwork API connection."""
    from src.api.upwork_graphql import UpworkGraphQLClient, UpworkAPIError, UpworkAuthenticationError
    
    try:
        logger.info("Initializing Upwork GraphQL client...")
        client = UpworkGraphQLClient()
        
        # Test the connection by getting organization info
        logger.info("Fetching organization information...")
        result = client.get_organization()
        
        if not result:
            logger.error("No organization data returned")
            return False
            
        logger.info("✅ Successfully connected to Upwork API!")
        logger.info("Organization Info: %s", result)
        return True
        
    except UpworkAuthenticationError as e:
        logger.error("❌ Authentication failed: %s", str(e))
        logger.info("Please check your access token and refresh token.")
        return False
    except UpworkAPIError as e:
        logger.error("❌ API Error: %s", str(e))
        return False
    except Exception as e:
        logger.exception("❌ Unexpected error:")
        return False

if __name__ == "__main__":
    print("🔍 Testing Upwork API connection...")
    
    # Check environment first
    if not check_environment():
        sys.exit(1)
    
    # Run the test
    import asyncio
    success = asyncio.run(test_upwork_connection())
    
    if not success:
        print("❌ Connection test failed. Please check the logs above for details.")
        sys.exit(1)
        
    print("✅ Connection test completed successfully!")
