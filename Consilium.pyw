"""
Consilium - Double-click to launch.
.pyw extension runs without console window on Windows.
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Run the launcher
from launcher import main
main()
