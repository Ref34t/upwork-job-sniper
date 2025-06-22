# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
python main.py                    # Start the job monitoring service
```

### Code Quality & Linting
```bash
black .                          # Format code
isort .                          # Sort imports
mypy .                           # Type checking
```

### Testing
```bash
pytest                           # Run all tests
pytest tests/test_upwork_graphql.py  # Run specific test file
pytest -v --cov=src             # Run with coverage
```

### Package Management
```bash
uv pip install -r requirements.txt  # Install dependencies
uv pip install -e .             # Install in development mode
```

## Architecture Overview

### Core Components

**Main Application (`main.py`)**
- `UpworkJobSniper`: Main orchestration class that coordinates all services
- `JobTracker`: Handles job deduplication using persistent JSON storage
- Async main loop with 10-minute search intervals and graceful shutdown

**Configuration (`config/settings.py`)**
- Pydantic-based settings with automatic `.env` file loading
- Type-safe configuration with validation
- Required environment variables: `UPWORK_API_KEY`, `UPWORK_API_SECRET`, `UPWORK_ACCESS_TOKEN`, `UPWORK_ACCESS_TOKEN_REFRESH`, `UPWORK_ORGANIZATION_ID`, `OPENAI_API_KEY`
- Optional: `PUSHOVER_API_TOKEN`, `PUSHOVER_USER_KEY` for notifications

**Upwork Integration (`src/api/upwork_graphql.py`)**
- `UpworkGraphQLClient`: Handles OAuth2 authentication and GraphQL queries
- Automatic token refresh every 50 minutes
- Comprehensive error handling with custom exceptions (`UpworkAPIError`, `UpworkAuthenticationError`)
- Job search with filtering by query, hourly rate, and budget

**Notifications (`src/notifications/pushover.py`)**
- `PushoverNotifier`: Sends rich mobile notifications via Pushover API
- Multi-device support with HTML formatting and deep linking
- Configurable priority levels and notification sounds

**Token Management (`src/utils/token_manager.py`)**
- `TokenManager`: Handles OAuth2 token lifecycle and refresh
- Secure credential storage and Base64 authentication

### Data Flow

1. **Configuration Loading**: Environment variables → Pydantic settings validation
2. **Authentication**: OAuth2 token refresh → Upwork API access
3. **Job Search**: GraphQL query → filtered job results
4. **Processing**: Deduplication → new job detection → notification
5. **Persistence**: JSON storage for seen jobs tracking

### Key Patterns

**Error Handling**
- Custom exception hierarchy for different error types
- Comprehensive logging with file and console output
- Graceful degradation for non-critical failures

**Async Architecture**
- Non-blocking main loop with configurable delays
- Signal-based shutdown handling (SIGINT, SIGTERM)
- Async job processing with retry logic

**Configuration Management**
- Environment-based configuration with type safety
- Automatic directory creation for `data/` and `logs/`
- Nested configuration with delimiter support

## File Structure

```
main.py                 # Application entry point
config/settings.py      # Pydantic settings with env loading
src/api/               # External API integrations
src/notifications/     # Push notification services  
src/utils/             # Utility modules
data/                  # Runtime data (seen_jobs.json)
logs/                  # Application logs
tests/                 # Test suite with mocking
```

## Development Notes

### Testing Strategy
- Mock external API calls in tests
- Separate test files for each major component
- Real connection tests available but require valid credentials

### Token Management
- Upwork tokens auto-refresh every 50 minutes
- Refresh tokens stored securely in environment variables
- Base64 authentication for token endpoint

### Job Processing
- Jobs are deduplicated using persistent storage in `data/seen_jobs.json`
- Rich job formatting includes client information, budget, and rates
- Notifications sent only for new jobs matching criteria

### Configuration
- Search parameters configurable via environment variables
- Default search: "wordpress" jobs with $30+ hourly rate and $500+ budget
- Pushover notifications optional but recommended for real-time alerts