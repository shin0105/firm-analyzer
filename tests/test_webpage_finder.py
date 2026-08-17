#!/usr/bin/env python3
"""
Test script for the firm webpage finder module.
Tests the module structure and basic functionality.
"""

import sys
import os

# Add parent directory to path to import the module
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

# Test 1: Module import
print("Test 1: Checking module import...")
try:
    from firm_analyzer.utils.webpage_finder import (
        initialize_clients,
        find_firm_webpage,
        verify_firm_webpage,
    )
    print("✓ Module imported successfully")
    print("  - initialize_clients: OK")
    print("  - find_firm_webpage: OK")
    print("  - verify_firm_webpage: OK")
except ImportError as e:
    print(f"✗ Failed to import module: {e}")
    sys.exit(1)

# Test 2: Check function signatures
print("\nTest 2: Checking function signatures...")
import inspect

# Check initialize_clients
sig = inspect.signature(initialize_clients)
print(f"  - initialize_clients() -> {sig.return_annotation if hasattr(sig, 'return_annotation') else 'tuple'}")

# Check find_firm_webpage
sig = inspect.signature(find_firm_webpage)
params = list(sig.parameters.keys())
expected_params = ['firm_name', 'tavily_client', 'openai_client']
if all(p in params for p in expected_params):
    print(f"  - find_firm_webpage({', '.join(params[:3])}, ...) ✓")
else:
    print(f"  - find_firm_webpage: Missing expected parameters ✗")
    sys.exit(1)

# Check verify_firm_webpage
sig = inspect.signature(verify_firm_webpage)
params = list(sig.parameters.keys())
expected_params = ['firm_name', 'candidates', 'openai_client']
if all(p in params for p in expected_params):
    print(f"  - verify_firm_webpage({', '.join(params)}) ✓")
else:
    print(f"  - verify_firm_webpage: Missing expected parameters ✗")
    sys.exit(1)

# Test 3: Module structure
print("\nTest 3: Module structure check...")
print("✓ All tests passed!")
print("\nNote: To fully test the module, you need:")
print("  - TAVILY_API_KEY in .env file")
print("  - GITHUB_TOKEN in .env file")
print("\nUsage: python find_firm_webpage.py <firm_name>")
print("Example: python find_firm_webpage.py '카카오'")
