# Upwork Job Sniper

## Overview
An automated system that monitors Upwork job posts using specific keywords, scores and summarizes relevant jobs, and sends mobile push notifications in real-time.

## Features
- Real-time job monitoring
- AI-powered job summarization
- Custom keyword filtering
- Push notifications for new jobs
- Web dashboard for job management

## Quick Start

### Prerequisites
- Python 3.8+
- Upwork API access
- OpenAI API key
- Pushover account and API keys

### Installation
```bash
# Clone the repository
git clone [repository-url]
cd upwork-sniper

# Install uv if you haven't already
curl -sSf https://astral.sh/uv/install.sh | sh

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Usage
```bash
# Start the application
python main.py
```

## Development

### Project Structure
```
upwork-sniper/
├── main.py                # Main application entry point
├── config/               # Configuration files
├── src/                  # Source code
│   ├── api/              # API clients
│   ├── core/             # Core functionality
│   ├── models/           # Data models
│   └── ui/               # User interface
├── tests/                # Test suite
├── .env                  # Environment variables
└── requirements.txt      # Project dependencies
```

### Development Workflow
1. Create a new branch for your feature
2. Make atomic commits with clear messages
3. Write tests for new functionality
4. Run linters and formatters
5. Submit a pull request for review

## Documentation
- [Project Roadmap](./roadmap.md)
- [API Documentation](./docs/API.md) (Coming Soon)
- [User Guide](./docs/USER_GUIDE.md) (Coming Soon)

## License
[Specify License]

## Contributing
Contributions are welcome! Please read our [contributing guidelines](./CONTRIBUTING.md) before submitting pull requests.
