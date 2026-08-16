#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to path so src can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.firm_analyzer.core.supabase_sync import main

if __name__ == "__main__":
    main()
