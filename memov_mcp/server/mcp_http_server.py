#!/usr/bin/env python3
"""
HTTP MCP Server for Memov - For URL-based MCP integration (e.g., Cursor)
"""

import argparse
import logging

import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route

from .mcp_server import mcp

LOGGER = logging.getLogger(__name__)


class MCPHTTPServer:
    """HTTP wrapper for MCP server"""

    def __init__(self, project_path: str = "."):
        self.project_path = project_path
        self.mcp_server = mcp

    async def handle_mcp_request(self, request):
        """Handle MCP requests over HTTP"""
        try:
            # Get request body
            data = await request.json()

            # Handle MCP protocol messages
            method = data.get("method", "")
            params = data.get("params", {})

            LOGGER.info(f"Received MCP request: {data}")

            if method == "initialize":
                return JSONResponse(
                    {
                        "jsonrpc": "2.0",
                        "id": data.get("id"),
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {"tools": {}},
                            "serverInfo": {"name": "Memov MCP Server", "version": "1.0.0"},
                        },
                    }
                )

            elif method == "tools/list":
                # Return available tools
                tools = []
                for tool_name, tool_obj in self.mcp_server._tool_manager._tools.items():
                    tools.append(
                        {
                            "name": tool_name,
                            "description": tool_obj.description or f"Memov tool: {tool_name}",
                            "inputSchema": tool_obj.parameters
                            or {"type": "object", "properties": {}, "required": []},
                        }
                    )

                return JSONResponse(
                    {"jsonrpc": "2.0", "id": data.get("id"), "result": {"tools": tools}}
                )

            elif method == "tools/call":
                # Execute tool
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})

                if tool_name in self.mcp_server._tool_manager._tools:
                    try:
                        # Add default project_path if not provided
                        if "project_path" not in tool_args:
                            tool_args["project_path"] = self.project_path

                        tool_obj = self.mcp_server._tool_manager._tools[tool_name]
                        result = tool_obj.fn(**tool_args)
                        return JSONResponse(
                            {
                                "jsonrpc": "2.0",
                                "id": data.get("id"),
                                "result": {"content": [{"type": "text", "text": str(result)}]},
                            }
                        )
                    except Exception as e:
                        return JSONResponse(
                            {
                                "jsonrpc": "2.0",
                                "id": data.get("id"),
                                "error": {
                                    "code": -32603,
                                    "message": f"Tool execution failed: {str(e)}",
                                },
                            }
                        )
                else:
                    return JSONResponse(
                        {
                            "jsonrpc": "2.0",
                            "id": data.get("id"),
                            "error": {"code": -32601, "message": f"Tool not found: {tool_name}"},
                        }
                    )

            else:
                return JSONResponse(
                    {
                        "jsonrpc": "2.0",
                        "id": data.get("id"),
                        "error": {"code": -32601, "message": f"Method not found: {method}"},
                    }
                )

        except Exception as e:
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": data.get("id", None),
                    "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                }
            )

    async def health_check(self, request):
        """Health check endpoint"""
        return JSONResponse(
            {
                "status": "healthy",
                "server": "Memov MCP HTTP Server",
                "project_path": self.project_path,
            }
        )

    def create_app(self):
        """Create Starlette application"""
        routes = [
            Route("/mcp", self.handle_mcp_request, methods=["POST"]),
            Route("/health", self.health_check, methods=["GET"]),
        ]

        app = Starlette(routes=routes)

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        return app


def main():
    """Main entry point for HTTP MCP server"""
    parser = argparse.ArgumentParser(description="Memov MCP HTTP Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to run server on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    parser.add_argument("project_path", nargs="?", default=".", help="Project path for Memov")

    args = parser.parse_args()

    # Create server
    server = MCPHTTPServer(args.project_path)
    app = server.create_app()

    print(f"🚀 Starting Memov MCP HTTP Server")
    print(f"📍 URL: http://{args.host}:{args.port}/mcp")
    print(f"📁 Project: {args.project_path}")
    print(f"🏥 Health: http://{args.host}:{args.port}/health")

    # Run server
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
