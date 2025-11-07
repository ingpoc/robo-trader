#!/usr/bin/env python3
"""
Wrapper script to run the MCP server with proper Python path setup.
"""
import sys
import os
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Set environment variables
os.environ["PYTHONPATH"] = str(src_path)
os.environ["ROBO_TRADER_PROJECT_ROOT"] = str(Path(__file__).parent.parent)

# Import and run the server module
if __name__ == "__main__":
    from server import main
    import asyncio
    asyncio.run(main())