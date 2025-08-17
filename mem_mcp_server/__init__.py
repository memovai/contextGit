"""
Memov MCP Server - AI-assisted version control with automatic prompt recording
"""

from pathlib import Path

from .cli.server_cli import ServerCLI
from .server.mcp_server import mcp

CONFIG_DIR = Path.home() / ".mem_mcp_server"

__all__ = ["ServerCLI", "mcp"]
