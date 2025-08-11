"""
Memov MCP Server - AI-assisted version control with automatic prompt recording
"""

__version__ = "1.0.0"
__author__ = "Memov Team"
__email__ = "contact@memov.dev"

from .cli.mov_cli import MovCLI
from .server.mcp_server import mcp

__all__ = ["MovCLI", "mcp"]
