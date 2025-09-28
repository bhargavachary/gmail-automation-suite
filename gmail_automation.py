#!/usr/bin/env python3
"""
Gmail Automation Suite v3.0 - Main Entry Point

This is the main entry point for the Gmail Automation Suite.
All core functionality has been moved to the src/ directory for better organization.
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the main function from the reorganized codebase
from gmail_automation import main

if __name__ == "__main__":
    sys.exit(main())