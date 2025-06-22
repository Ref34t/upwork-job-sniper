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

**AI Analysis (`src/ai/job_analyzer.py`)**
- `JobAnalyzer`: OpenAI-powered job analysis and scoring
- Generates job summaries, relevance scores (0-10), and proposal scripts
- Configurable scoring thresholds for intelligent notifications
- Uses GPT-4o-mini by default with customizable temperature and tokens

**Notifications (`src/notifications/pushover.py`)**
- `PushoverNotifier`: Sends rich mobile notifications via Pushover API
- Multi-device support with HTML formatting and deep linking
- Includes AI insights: scores, summaries, and proposal scripts
- Dynamic priority levels based on AI score (emergency for 9+ scores)

**Token Management (`src/utils/token_manager.py`)**
- `TokenManager`: Handles OAuth2 token lifecycle and refresh
- Secure credential storage and Base64 authentication

### Data Flow

1. **Configuration Loading**: Environment variables → Pydantic settings validation
2. **Authentication**: OAuth2 token refresh → Upwork API access
3. **Job Search**: GraphQL query → filtered job results
4. **Processing**: Deduplication → AI analysis → scoring → selective notification
5. **AI Analysis**: Job data → OpenAI → summary + score + proposal script
6. **Persistence**: JSON storage for seen jobs tracking

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
src/ai/                # AI job analysis and scoring
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
- AI analysis generates summaries, scores (0-10), and proposal scripts
- Intelligent filtering: only jobs scoring 7+ trigger notifications by default
- Rich job formatting includes client information, budget, and AI insights

### AI Integration
- OpenAI GPT-4o-mini model for job analysis and scoring
- Configurable prompts, temperature (0.3), and token limits (1000)
- Automatic proposal script generation for high-scoring jobs
- Dynamic notification priority based on AI score (emergency for 9+)

### Configuration
- Search parameters configurable via environment variables
- Default search: "wordpress" jobs with $30+ hourly rate and $500+ budget
- AI analysis can be disabled with `ENABLE_AI_ANALYSIS=false`
- Notification threshold adjustable with `MIN_NOTIFICATION_SCORE` (default: 7)