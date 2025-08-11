#!/usr/bin/env python3
"""
Unified MCP server launcher for Memov
Supports both stdio and HTTP modes
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
LOGGER = logging.getLogger(__name__)


def main():
    """Main launcher for MCP servers"""
    parser = argparse.ArgumentParser(
        description="Memov MCP Server Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start stdio server (for Claude Desktop)
  python start_mcp.py stdio /path/to/project

  # Start HTTP server (for Cursor)
  python start_mcp.py http /path/to/project --port 8080
        """,
    )

    parser.add_argument(
        "mode",
        choices=["stdio", "http"],
        help="Server mode: stdio (for Claude Desktop) or http (for Cursor/web)",
    )

    parser.add_argument(
        "project_path",
        help="Path to the project directory to monitor (required)",
    )

    parser.add_argument(
        "--port", type=int, default=8080, help="Port for HTTP server (default: 8080)"
    )

    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Host for HTTP server (default: 127.0.0.1)"
    )

    args = parser.parse_args()

    # Validate project path
    if not os.path.exists(args.project_path):
        print(f"Error: Project path '{args.project_path}' does not exist.")
        sys.exit(1)

    if not os.path.isdir(args.project_path):
        print(f"Error: Project path '{args.project_path}' is not a directory.")
        sys.exit(1)

    # Set environment variable for project path
    os.environ["MEMOV_DEFAULT_PROJECT"] = os.path.abspath(args.project_path)

    # Set up logging to file
    log_path = Path.home() / ".mov" / "logs" / f"mcp_{time.strftime('%Y%m%d_%H%M%S')}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    new_file_handler = logging.FileHandler(log_path, mode="a")
    new_file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s:%(lineno)s - %(message)s")
    )
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(new_file_handler)

    LOGGER.info(f"Starting Memov MCP Server")
    LOGGER.info(f"Project: {os.path.abspath(args.project_path)}")
    LOGGER.info(f"Mode: {args.mode}")

    if args.mode == "stdio":
        LOGGER.info(f"Protocol: stdio (for Claude Desktop)")
        LOGGER.info(f"Usage: Configure Claude Desktop with this script path")
        LOGGER.info(f"")
        # Import and run stdio server
        from .mcp_server import main as stdio_main

        stdio_main()

    elif args.mode == "http":
        LOGGER.info(f"Protocol: HTTP")
        LOGGER.info(f"URL: http://{args.host}:{args.port}/mcp")
        LOGGER.info(f"Health: http://{args.host}:{args.port}/health")
        LOGGER.info(f"")
        # Import and run HTTP server
        import uvicorn

        from .mcp_http_server import MCPHTTPServer

        server = MCPHTTPServer(args.project_path)
        app = server.create_app()
        uvicorn.run(app, host=args.host, port=args.port)


def cli_main():
    """CLI entry point"""
    main()


if __name__ == "__main__":
    cli_main()
