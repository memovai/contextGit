"""
Unified MCP server launcher for Memov
Supports both stdio and HTTP modes
"""

import logging
import os
import time
from typing import Annotated

import typer

from mem_mcp_server.globals import CONFIG_DIR
from mem_mcp_server.server.mcp_server import MemMCPTools

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
LOGGER = logging.getLogger(__name__)


def mcp_launcher(
    mode: Annotated[str, typer.Argument(help="Server mode: stdio or http")],
    project_path: Annotated[
        str, typer.Argument(help="Path to the project directory to monitor (required)")
    ],
    port: Annotated[int, typer.Option(help="Port for HTTP server")] = 8000,
    host: Annotated[str, typer.Option(help="Host for HTTP server")] = "127.0.0.1",
):
    """Main launcher for MCP servers"""

    # Validate mode
    if mode not in ["stdio", "http"]:
        typer.echo(f"Error: mode must be either 'stdio' or 'http', got '{mode}'", err=True)
        raise typer.Exit(1)

    # Validate project path
    if not os.path.exists(project_path):
        typer.echo(f"Error: Project path '{project_path}' does not exist.", err=True)
        raise typer.Exit(1)

    if not os.path.isdir(project_path):
        typer.echo(f"Error: Project path '{project_path}' is not a directory.", err=True)
        raise typer.Exit(1)

    # Set up logging to file
    log_path = CONFIG_DIR / "logs" / f"mcp_{time.strftime('%Y%m%d_%H%M%S')}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    new_file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    new_file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s:%(lineno)s - %(message)s")
    )
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(new_file_handler)

    LOGGER.info(f"Starting Memov MCP Server")
    LOGGER.info(f"Project: {os.path.abspath(project_path)}")
    LOGGER.info(f"Mode: {mode}")

    if mode == "stdio":
        LOGGER.info(f"Protocol: stdio (for Claude Desktop)")
        LOGGER.info(f"Usage: Configure Claude Desktop with this script path")
        LOGGER.info(f"")

        mem_mcp_tools = MemMCPTools(project_path)
        mem_mcp_tools.run()

    elif mode == "http":
        LOGGER.info(f"Protocol: HTTP")
        LOGGER.info(f"URL: http://{host}:{port}/mcp")
        LOGGER.info(f"Health: http://{host}:{port}/health")
        LOGGER.info(f"")

        mem_mcp_tools = MemMCPTools(project_path)
        mem_mcp_tools.run(transport="streamable-http")


def main():
    """Main entry point for the MCP launcher script."""
    typer.run(mcp_launcher)


if __name__ == "__main__":
    main()
