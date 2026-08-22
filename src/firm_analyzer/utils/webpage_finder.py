#!/usr/bin/env python3
"""
Firm Webpage Finder Module

This module uses Tavily search to find the actual firm's webpage and validates
the content using LLM to ensure it matches the firm name.
"""

import json
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from tavily import TavilyClient

from firm_analyzer.llm import LLMError, LLMProvider, get_provider

# Load environment variables
load_dotenv()


def initialize_clients(provider: Optional[str] = None):
    """Initialize the Tavily client and the selected LLM provider."""
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY not found in environment variables.")

    tavily_client = TavilyClient(api_key=tavily_api_key)
    llm = get_provider(provider)
    llm.api_key()  # Surface a missing key now rather than mid-search.

    return tavily_client, llm


def find_firm_webpage(
    firm_name: str,
    tavily_client: TavilyClient,
    llm: LLMProvider,
    max_candidates: int = 5,
) -> Optional[Dict[str, Any]]:
    """
    Find and verify the actual firm webpage.

    Args:
        firm_name: The name of the firm to search for
        tavily_client: Initialized Tavily client
        llm: An LLM provider from firm_analyzer.llm
        max_candidates: Maximum number of URLs to check (default: 5)

    Returns:
        Dictionary containing:
        - url: The verified firm webpage URL
        - confidence: Confidence score (high/medium/low)
        - reasoning: Why this URL was selected
        Or None if no suitable webpage was found
    """
    print(f"  -> Searching for webpage of {firm_name}...")
    
    # Step 1: Search for the firm's official website using Tavily
    try:
        search_query = f"{firm_name} 공식 홈페이지 official website"
        search_response = tavily_client.search(
            query=search_query,
            search_depth="advanced",
            max_results=max_candidates,
        )
    except Exception as e:
        print(f"  -> Error searching for webpage: {e}")
        return None
    
    results = search_response.get("results", [])
    if not results:
        print(f"  -> No search results found for {firm_name}")
        return None
    
    # Step 2: Extract candidate URLs
    candidates = []
    for result in results[:max_candidates]:
        url = result.get("url", "")
        title = result.get("title", "")
        content = result.get("content", "")
        
        if url and (title or content):
            candidates.append({
                "url": url,
                "title": title,
                "content": content
            })
    
    if not candidates:
        print(f"  -> No valid candidate URLs found for {firm_name}")
        return None
    
    # Step 3: Use LLM to verify which URL is the actual firm webpage
    return verify_firm_webpage(firm_name, candidates, llm)


def verify_firm_webpage(
    firm_name: str,
    candidates: list,
    llm: LLMProvider,
) -> Optional[Dict[str, Any]]:
    """
    Use the LLM to verify which candidate URL is the actual firm webpage.

    Args:
        firm_name: The name of the firm
        candidates: List of candidate URLs with their titles and content
        llm: An LLM provider from firm_analyzer.llm

    Returns:
        Dictionary with url, confidence, and reasoning, or None if verification fails
    """
    # Build prompt for LLM verification
    prompt = f"""
You are an expert at identifying official company webpages. Analyze the following search results for the firm '{firm_name}' and determine which URL is most likely the official company webpage.

Firm Name: {firm_name}

Candidate URLs:
{json.dumps(candidates, ensure_ascii=False, indent=2)}

Instructions:
1. Analyze each URL, title, and content snippet
2. Determine which URL is most likely the official company webpage
3. Consider factors like:
   - Domain relevance (company name in domain)
   - Title and content matching the company name
   - Professional appearance and authenticity
   - Korean vs international sites (prefer Korean for Korean companies)
4. Assign a confidence level: high, medium, or low

Return your response in the following JSON format:
{{
  "url": "The most likely official webpage URL",
  "confidence": "high/medium/low",
  "reasoning": "Brief explanation of why this URL was selected (in Korean)"
}}

If none of the URLs appear to be a legitimate company webpage, return:
{{
  "url": null,
  "confidence": "none",
  "reasoning": "Explanation of why no suitable webpage was found (in Korean)"
}}
"""
    
    try:
        result = llm.complete_json(
            prompt,
            system=(
                "You are an expert at identifying official company webpages. "
                "Always respond in JSON format."
            ),
            max_output_tokens=2000,
        )
    except LLMError as e:
        print(f"  -> Error verifying webpage with LLM: {e}")
        return None

    if not isinstance(result, dict):
        print("  -> Unexpected LLM response shape for webpage verification")
        return None

    # Validate the result
    if result.get("url"):
        confidence = result.get("confidence", "unknown")
        reasoning = result.get("reasoning", "No reasoning provided")
        print(f"  -> Found webpage with {confidence} confidence: {result['url']}")
        print(f"  -> Reasoning: {reasoning}")
        return result

    print(f"  -> No suitable webpage found: {result.get('reasoning', 'Unknown reason')}")
    return None


def main():
    """Example usage of the firm webpage finder."""
    import argparse
    import sys

    from firm_analyzer.llm import PROVIDER_IDS

    parser = argparse.ArgumentParser(
        description="Find and verify a firm's official webpage."
    )
    parser.add_argument("firm_name", help="Firm name to search for, e.g. '카카오'")
    parser.add_argument(
        "--provider",
        choices=PROVIDER_IDS,
        default=None,
        help="LLM provider to use for verification",
    )
    args = parser.parse_args()

    # Initialize clients
    try:
        tavily_client, llm = initialize_clients(args.provider)
    except (ValueError, LLMError) as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Verifying with {llm.label} ({llm.model})")

    # Find webpage
    result = find_firm_webpage(args.firm_name, tavily_client, llm)

    if result:
        print("\n" + "="*60)
        print("✓ Found firm webpage!")
        print("="*60)
        print(f"URL: {result['url']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Reasoning: {result['reasoning']}")
    else:
        print("\n" + "="*60)
        print("✗ Could not find firm webpage")
        print("="*60)


if __name__ == "__main__":
    main()
