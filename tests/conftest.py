"""
pytest configuration file
Adds parent directory to sys.path so tests can import tool and util modules
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
