#!/usr/bin/env python3
import sys
from pathlib import Path

# Allow running from a checkout without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from firm_analyzer.web.app import main

if __name__ == "__main__":
    main()
