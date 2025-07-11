#!/usr/bin/env python3
"""
Main entry point for YouTube Shorts Trend Analysis CLI
"""

import sys
import os
import asyncio

# Add src directory to Python path for proper imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.cli import main

if __name__ == "__main__":
    asyncio.run(main())