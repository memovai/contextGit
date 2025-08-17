"""
Memov MCP Server - AI-assisted version control with automatic prompt recording
"""
from .cli.server_cli import ServerCLI
from .server.mcp_server import mcp

__all__ = ["ServerCLI", "mcp"]
