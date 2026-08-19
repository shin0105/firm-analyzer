# Firm Webpage Finder Module

## Overview

The `find_firm_webpage.py` module provides functionality to automatically find and verify firm official webpages using Tavily search and LLM-based content verification.

## Features

- **Tavily Search Integration**: Uses Tavily's advanced search to find potential company webpages
- **LLM Verification**: Employs GPT-4 to verify that found URLs are legitimate company webpages
- **Confidence Scoring**: Returns confidence levels (high/medium/low) for found webpages
- **Reasoning**: Provides explanations for why a particular URL was selected

## How It Works

1. **Search Phase**: Searches for the firm's official website using Tavily with a query like `"{firm_name} 공식 홈페이지 official website"`

2. **Candidate Extraction**: Extracts up to 5 candidate URLs with their titles and content snippets

3. **LLM Verification**: Uses GPT-4 to analyze each candidate and determine which URL is most likely the official company webpage, considering:
   - Domain relevance (company name in domain)
   - Title and content matching
   - Professional appearance
   - Language preference (Korean for Korean companies)

4. **Result**: Returns the most likely webpage URL with a confidence score and reasoning

## Usage

### Standalone

```bash
python scripts/run_webpage_finder.py "카카오"

# Verify with a specific AI
python scripts/run_webpage_finder.py "카카오" --provider claude
```

### Integration in Scripts

```python
from firm_analyzer.utils.webpage_finder import find_firm_webpage, initialize_clients

# Initialize the Tavily client and the selected LLM provider.
# Pass a provider id to override config.yml / LLM_PROVIDER.
tavily_client, llm = initialize_clients()

# Find webpage
result = find_firm_webpage(
    firm_name="카카오",
    tavily_client=tavily_client,
    llm=llm,
    max_candidates=5
)

if result:
    print(f"URL: {result['url']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Reasoning: {result['reasoning']}")
```

### In search_summarize.py

The webpage finder is automatically integrated into the main `search_summarize.py` and legacy `firm_summary/2_search_summarize.py` scripts.

Enable/disable in `config.json`:

```json
{
  "search": {
    "find_webpage": true
  }
}
```

## Output Files

When a firm is processed with webpage finding enabled, the following files are created:

- `webpage.json`: Contains the webpage URL, confidence level, and reasoning
- `summary.md`: Updated to include the webpage URL and confidence level

## Requirements

- `TAVILY_API_KEY`: Required for Tavily search
- A key for the selected LLM provider — `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
  `GEMINI_API_KEY`, or `GITHUB_TOKEN`. Choose the provider with `LLM_PROVIDER`,
  `app.llm_provider` in `config.yml`, or `--provider`.

## Testing

```bash
pytest tests/test_webpage_finder.py
```

## Error Handling

The module handles errors gracefully:
- If search fails, returns `None`
- If no candidates are found, returns `None`
- If LLM verification fails, returns `None`
- Errors are logged but don't stop the processing pipeline

## Example Output

```json
{
  "url": "https://www.kakao.com",
  "confidence": "high",
  "reasoning": "도메인이 회사명과 정확히 일치하며, 제목과 내용이 카카오의 공식 홈페이지임을 명확히 나타냅니다."
}
```
