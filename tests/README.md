# Test Files

This directory contains test scripts for various components of the firm_websearch application.

## Available Tests

### test_url.py
Tests OpenAI API connection with GitHub Models endpoint.

### test_pdf_parser.py
Tests PDF parsing functionality for firm data extraction.

### test_kakao_geocoding.py
Tests Kakao Maps API for Korean address geocoding.

### test_webpage_finder.py
Tests webpage finder functionality for locating firm websites.

## Running Tests

```bash
# Run a specific test
python tests/test_url.py
python tests/test_kakao_geocoding.py
python tests/test_pdf_parser.py
python tests/test_webpage_finder.py
```

## Environment Variables Required

Make sure you have the following environment variables set (in `.env` file):

```
GITHUB_TOKEN=your_github_token
TAVILY_API_KEY=your_tavily_api_key
KAKAO_REST_API_KEY=your_kakao_rest_api_key  # Optional, for geocoding tests
```
