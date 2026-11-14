# Firm Webpage Finder Module

## Overview

The webpage finder (`src/firm_analyzer/utils/webpage_finder.py`, command `firm-find-webpage`) automatically finds and verifies firms' official webpages using Tavily search and LLM-based content verification.

## Features

- **Tavily Search Integration**: Uses Tavily's advanced search to find potential company webpages
- **LLM Verification**: Uses the selected LLM provider (OpenAI, Claude, Gemini or GitHub Models) to verify that found URLs are legitimate company webpages
- **Confidence Scoring**: Returns confidence levels (high/medium/low) for found webpages
- **Reasoning**: Provides explanations for why a particular URL was selected

## How It Works

1. **Search Phase**: Searches for the firm's official website using Tavily with a query like `"{firm_name} 공식 홈페이지 official website"`

2. **Candidate Extraction**: Extracts up to 5 candidate URLs with their titles and content snippets

3. **LLM Verification**: Asks the selected LLM to analyze each candidate and determine which URL is most likely the official company webpage, considering:
   - Domain relevance (company name in domain)
   - Title and content matching
   - Professional appearance
   - Language preference (Korean for Korean companies)

4. **Result**: Returns the most likely webpage URL with a confidence score and reasoning

## Usage

### Standalone

```bash
uv run firm-find-webpage "카카오"

# Verify with a specific AI
uv run firm-find-webpage "카카오" --provider claude
```

`uv run python scripts/run_webpage_finder.py "카카오"` works the same way.

### Integration in Scripts

```python
from firm_analyzer.utils.webpage_finder import find_firm_webpage, initialize_clients

# Initialize the Tavily client and the selected LLM provider.
# Pass a provider id (e.g. "claude") to override LLM_PROVIDER.
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

### In firm-summarize

The webpage finder runs inside `firm-summarize` for every firm, with the same provider and model as the summary. Enable/disable it in `config.yml`:

```yaml
search:
  find_webpage: true   # false turns it off
```

## Output Files

When a firm is processed with webpage finding enabled and a webpage is found, its result folder gets:

- `webpage.json`: Contains the webpage URL, confidence level, and reasoning
- `summary.md`: Includes the webpage URL and confidence level in its header

## Requirements

- `TAVILY_API_KEY`: Required for Tavily search
- A key for the selected LLM provider — `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
  `GEMINI_API_KEY`, or `GITHUB_TOKEN`. The standalone command and
  `initialize_clients()` pick the provider from `--provider` (or the argument),
  then `LLM_PROVIDER`, then `openai`; they do not read `app.llm_provider` in
  `config.yml`. Inside `firm-summarize`, the summary's provider is used.

## Testing

```bash
uv sync --extra dev   # once, installs pytest
uv run pytest tests/test_webpage_finder.py
```

## Error Handling

The module handles errors gracefully:
- If search fails, returns `None`
- If no candidates are found, returns `None`
- If LLM verification fails, or the LLM finds no suitable page, returns `None`
- Errors are logged but don't stop the processing pipeline

## Example Output

```json
{
  "url": "https://www.kakao.com",
  "confidence": "high",
  "reasoning": "도메인이 회사명과 정확히 일치하며, 제목과 내용이 카카오의 공식 홈페이지임을 명확히 나타냅니다."
}
```
