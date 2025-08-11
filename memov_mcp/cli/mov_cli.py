#!/usr/bin/env python3
"""
Mov CLI - Command line interface for managing Memov MCP servers
"""

import argparse
import importlib.util
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional

import psutil


class MovCLI:
    """Mov CLI manager for MCP servers"""

    def __init__(self):
        self.config_dir = Path.home() / ".mov"
        self.pid_file = self.config_dir / "servers.json"
        self.config_dir.mkdir(exist_ok=True)

    def load_servers(self) -> Dict:
        """Load running servers from PID file"""
        if self.pid_file.exists():
            try:
                with open(self.pid_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def save_servers(self, servers: Dict):
        """Save running servers to PID file"""
        with open(self.pid_file, "w") as f:
            json.dump(servers, f, indent=2)

    def get_server_key(self, workspace: str, port: int) -> str:
        """Generate unique server key"""
        return f"{workspace}:{port}"

    def start_server(self, workspace: str, port: int, host: str = "127.0.0.1") -> bool:
        """Start a new MCP server in background"""
        workspace_path = Path(workspace).resolve()

        if not workspace_path.exists():
            print(f"❌ Error: Workspace path '{workspace}' does not exist")
            return False

        if not workspace_path.is_dir():
            print(f"❌ Error: Workspace path '{workspace}' is not a directory")
            return False

        # Check if server is already running
        servers = self.load_servers()
        server_key = self.get_server_key(str(workspace_path), port)

        if server_key in servers:
            pid = servers[server_key]["pid"]
            if psutil.pid_exists(pid):
                print(f"⚠️  Server already running on port {port} for workspace {workspace}")
                return False
            else:
                # Clean up stale entry
                del servers[server_key]

        # Check if port is already in use
        if self.is_port_in_use(port):
            print(f"❌ Error: Port {port} is already in use")
            return False

        # Start server in background
        try:
            # Find the Memov MCP package
            mov_spec = importlib.util.find_spec("memov_mcp")
            if mov_spec is None:
                print("❌ Error: Memov MCP package not found. Please install it first.")
                return False
            script_dir = Path(mov_spec.origin).parent

            # Start the server process using poetry script
            process = subprocess.Popen(
                [
                    "poetry",
                    "run",
                    "start-mcp",
                    "http",
                    str(workspace_path),
                    "--port",
                    str(port),
                    "--host",
                    host,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=script_dir,
                text=True,
            )

            # Wait a moment to see if it starts successfully
            time.sleep(2)

            if process.poll() is None:  # Process is still running
                # Save server info
                servers[server_key] = {
                    "pid": process.pid,
                    "workspace": str(workspace_path),
                    "port": port,
                    "host": host,
                    "start_time": time.time(),
                    "status": "running",
                }
                self.save_servers(servers)

                print(f"✅ Started Mov server")
                print(f"   📁 Workspace: {workspace_path}")
                print(f"   🌐 URL: http://{host}:{port}/mcp")
                print(f"   🏥 Health: http://{host}:{port}/health")
                print(f"   🆔 PID: {process.pid}")
                return True
            else:
                # Process failed to start
                stdout, stderr = process.communicate()
                print(f"❌ Failed to start server:")
                if stderr:
                    print(f"   Error: {stderr.decode()}")
                return False

        except Exception as e:
            print(f"❌ Error starting server: {e}")
            return False

    def stop_server(
        self, workspace: Optional[str] = None, port: Optional[int] = None, all: bool = False
    ):
        """Stop running server(s)"""
        servers = self.load_servers()

        if all:
            # Stop all servers
            if not servers:
                print("ℹ️  No servers running")
                return

            stopped_count = 0
            for server_key, server_info in servers.items():
                if self.stop_single_server(server_key, server_info):
                    stopped_count += 1

            if stopped_count > 0:
                print(f"✅ Stopped {stopped_count} server(s)")
            else:
                print("ℹ️  No servers were running")
            return

        # Stop specific server
        if workspace and port:
            workspace_path = Path(workspace).resolve()
            server_key = self.get_server_key(str(workspace_path), port)
            if server_key in servers:
                if self.stop_single_server(server_key, servers[server_key]):
                    print(f"✅ Stopped server for workspace {workspace} on port {port}")
                else:
                    print(f"ℹ️  Server for workspace {workspace} on port {port} was not running")
            else:
                print(f"ℹ️  No server found for workspace {workspace} on port {port}")
            return
        elif workspace:
            # Stop all servers for this workspace
            workspace_path = Path(workspace).resolve()
            workspace_str = str(workspace_path)
            stopped_count = 0
            for server_key, server_info in list(servers.items()):
                if server_info["workspace"] == workspace_str:
                    if self.stop_single_server(server_key, server_info):
                        stopped_count += 1

            if stopped_count > 0:
                print(f"✅ Stopped {stopped_count} server(s) for workspace {workspace}")
            else:
                print(f"ℹ️  No servers running for workspace {workspace}")
            return
        elif port:
            # Stop all servers on this port
            stopped_count = 0
            for server_key, server_info in list(servers.items()):
                if server_info["port"] == port:
                    if self.stop_single_server(server_key, server_info):
                        stopped_count += 1

            if stopped_count > 0:
                print(f"✅ Stopped {stopped_count} server(s) on port {port}")
            else:
                print(f"ℹ️  No servers running on port {port}")
            return
        else:
            print("❌ Error: Must specify workspace, port, or use --all")
            return

    def stop_single_server(self, server_key: str, server_info: Dict) -> bool:
        """Stop a single server"""

        def del_server_key():
            """Delete server key from config"""
            servers = self.load_servers()
            if server_key in servers:
                del servers[server_key]
                self.save_servers(servers)

        pid = server_info["pid"]

        try:
            process = psutil.Process(pid)
            children = process.children(recursive=True)
            for child in children:
                child.terminate()
            process.terminate()

            # process.wait(timeout=5)
            gone, alive = psutil.wait_procs([process] + children, timeout=5)

            for p in alive:
                p.kill()

            # Remove from config
            del_server_key()
            return True
        except psutil.NoSuchProcess:
            # Process already dead
            del_server_key()
            return False
        except Exception as e:
            print(f"❌ Error stopping server {pid}: {e}")
            return False

    def status(self):
        """Show status of all servers"""
        servers = self.load_servers()

        if not servers:
            print("ℹ️  No servers running")
            return

        print("🔄 Mov Server Status:")
        print("-" * 80)

        running_count = 0
        for server_key, server_info in servers.items():
            pid = server_info["pid"]
            workspace = server_info["workspace"]
            port = server_info["port"]
            host = server_info["host"]
            start_time = server_info["start_time"]

            if psutil.pid_exists(pid):
                process = psutil.Process(pid)
                uptime = time.time() - start_time
                uptime_str = self.format_uptime(uptime)

                print(f"✅ Running (PID: {pid})")
                print(f"   📁 Workspace: {workspace}")
                print(f"   🌐 URL: http://{host}:{port}/mcp")
                print(f"   ⏱️  Uptime: {uptime_str}")
                print(f"   💾 Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB")
                print()
                running_count += 1
            else:
                print(f"❌ Dead (PID: {pid})")
                print(f"   📁 Workspace: {workspace}")
                print(f"   🌐 Port: {port}")
                print()

        print(f"📊 Summary: {running_count}/{len(servers)} servers running")

    def format_uptime(self, seconds: float) -> str:
        """Format uptime in human readable format"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes}m {int(seconds % 60)}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"

    def is_port_in_use(self, port: int) -> bool:
        """Check if port is already in use"""
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex(("127.0.0.1", port)) == 0


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Mov - Memov MCP Server Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start a server
  mov start --workspace /path/to/project --port 8080

  # Stop a specific server
  mov stop --workspace /path/to/project --port 8080

  # Stop all servers
  mov stop --all

  # Show status
  mov status
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start a new server")
    start_parser.add_argument("--workspace", required=True, help="Workspace directory to monitor")
    start_parser.add_argument("--port", type=int, required=True, help="Port to run server on")
    start_parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)"
    )

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop server(s)")
    stop_parser.add_argument("--workspace", help="Workspace directory")
    stop_parser.add_argument("--port", type=int, help="Port number")
    stop_parser.add_argument("--all", action="store_true", help="Stop all servers")

    # Status command
    subparsers.add_parser("status", help="Show server status")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = MovCLI()

    if args.command == "start":
        cli.start_server(args.workspace, args.port, args.host)
    elif args.command == "stop":
        cli.stop_server(args.workspace, args.port, args.all)
    elif args.command == "status":
        cli.status()


if __name__ == "__main__":
    main()
