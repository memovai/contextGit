#!/usr/bin/env python3
"""
Mov CLI - Command line interface for managing Memov MCP servers
"""

import datetime
import json
import socket
import subprocess
import time
from pathlib import Path
from typing import Annotated, Any, Optional

import psutil
import typer

from mem_mcp_server import CONFIG_DIR


class ServerCLI:
    """CLI manager for Mem MCP servers"""

    def __init__(self):
        self.config_dir = CONFIG_DIR
        self.pid_file = self.config_dir / "servers.json"
        self.config_dir.mkdir(exist_ok=True)

    def load_servers(self) -> dict:
        """Load running servers from PID file"""
        if not self.pid_file.exists():
            return {}

        try:
            with open(self.pid_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def save_servers(self, servers: dict) -> None:
        """Save running servers to PID file"""
        with open(self.pid_file, "w") as f:
            json.dump(servers, f, indent=2)

    def start_server(self, workspace: str, port: int = 8000, host: str = "127.0.0.1") -> bool:
        """Start a new MCP server in background"""
        workspace_path = Path(workspace).resolve()

        if not workspace_path.exists():
            typer.echo(f"❌ Error: Workspace path '{workspace}' does not exist", err=True)
            return False

        if not workspace_path.is_dir():
            typer.echo(f"❌ Error: Workspace path '{workspace}' is not a directory", err=True)
            return False

        # Check if port is already in use
        if self.is_port_in_use(host, port):
            typer.echo(f"❌ Error: IP {host}:{port} is already in use", err=True)
            return False

        # Check if server is already running
        alive_servers = self.status(verbose=False)
        if str(workspace_path) in alive_servers:
            typer.echo(
                f"⚠️  Server already running on ip {host}:{port} for workspace {workspace}",
                err=True,
            )
            return False

        # Start server in background
        try:
            # Load existing servers and create server key
            servers = self.load_servers()
            server_key = str(workspace_path)

            # Start the server process using uvx
            process = subprocess.Popen(
                [
                    "uv",
                    "run",
                    "mem-mcp-launcher",
                    "http",
                    str(workspace_path),
                    "--port",
                    str(port),
                    "--host",
                    host,
                    "--port",
                    str(port),
                    "--factory",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
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
                    "start_timestamp": datetime.datetime.now().timestamp(),
                    "start_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "running",
                }
                self.save_servers(servers)

                typer.echo(f"✅ Started Mov server")
                typer.echo(f"   📁 Workspace: {workspace_path}")
                typer.echo(f"   🌐 URL: http://{host}:{port}/mcp")
                typer.echo(f"   🏥 Health: http://{host}:{port}/health")
                typer.echo(f"   🆔 PID: {process.pid}")
                return True
            else:
                # Process failed to start
                stdout, stderr = process.communicate()
                typer.echo(f"❌ Failed to start server:")
                typer.echo(f"   Output: {stdout.decode()}")
                typer.echo(f"   Error: {stderr.decode()}")
                return False

        except Exception as e:
            typer.echo(f"❌ Error starting server: {e}")
            return False

    def stop_server(
        self, workspace: Optional[str] = None, port: Optional[int] = None, all_servers: bool = False
    ):
        """Stop running server(s)"""
        servers = self.load_servers()

        if all_servers:
            # Stop all servers
            if not servers:
                typer.echo("ℹ️  No servers running")
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

    def stop_single_server(self, server_key: str, server_info: dict) -> bool:
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

    def status(self, verbose: bool = True) -> dict[str, dict[str, Any]]:
        """Show status of all servers"""
        servers = self.load_servers()

        if not servers:
            if verbose:
                typer.echo("ℹ️  No servers running")
            return servers

        if verbose:
            typer.echo("🔄 Mov Server Status:")
            typer.echo("-" * 80)

        running_count = 0
        server_to_delete = []
        for server_key, server_info in servers.items():
            pid = server_info["pid"]
            workspace = server_info["workspace"]
            port = server_info["port"]
            host = server_info["host"]
            start_timestamp = server_info["start_timestamp"]
            start_time = server_info["start_time"]

            if psutil.pid_exists(pid):
                process = psutil.Process(pid)
                uptime = time.time() - start_timestamp
                uptime_str = datetime.timedelta(seconds=int(uptime))
                running_count += 1

                if verbose:
                    typer.echo(f"✅ Running (PID: {pid})")
                    typer.echo(f"   📁 Workspace: {workspace}")
                    typer.echo(f"   🌐 URL: http://{host}:{port}/mcp")
                    typer.echo(f"   ⏱️ Start time: {start_time}")
                    typer.echo(f"   ⏱️ Uptime: {uptime_str}")
                    typer.echo(f"   💾 Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB")
                    typer.echo()
            else:
                if verbose:
                    typer.echo(f"❌ Dead (PID: {pid})")
                    typer.echo(f"   📁 Workspace: {workspace}")
                    typer.echo(f"   🌐 Port: {port}")
                    typer.echo()
                server_to_delete.append(server_key)  # Mark for deletion

        if verbose:
            typer.echo(f"📊 Summary: {running_count}/{len(servers)} servers running")

        # Clean up dead servers and their config
        for server_key in server_to_delete:
            del servers[server_key]
        self.save_servers(servers)

        return servers

    def is_port_in_use(self, host: str, port: int) -> bool:
        """Check if port is already in use"""
        # TODO: change to check http://ip:port/health
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex((host, port)) == 0


app = typer.Typer(
    help="Mem MCP Server Manager - Manage MCP servers for workspace monitoring",
    rich_markup_mode="rich",
)
cli = ServerCLI()


@app.command(help="Start a new MCP server")
def start(
    workspace: Annotated[str, typer.Option(help="Workspace directory to monitor")],
    port: Annotated[int, typer.Option(help="Port to run server on")] = 8000,
    host: Annotated[str, typer.Option(help="Host to bind to")] = "127.0.0.1",
):
    """Start a new server"""
    cli.start_server(workspace, port, host)


@app.command(help="Stop running server(s)")
def stop(
    workspace: Annotated[Optional[str], typer.Option(help="Workspace directory")] = None,
    port: Annotated[Optional[int], typer.Option(help="Port number")] = None,
    all_servers: Annotated[bool, typer.Option("--all", help="Stop all running servers")] = False,
):
    """Stop server(s)"""

    # Must specify at least one option
    if not workspace and not port and not all_servers:
        typer.echo("❌ Error: Must specify at least one option: --workspace, --port, or --all", err=True)
        raise typer.Exit(1)

    # If --all is specified, ignore other options
    if all_servers and (workspace or port):
        typer.echo("⚠️  Warning: --all flag specified, ignoring other options")

    cli.stop_server(workspace, port, all_servers)


@app.command(help="Show status of all running servers")
def status():
    """Show server status"""
    cli.status()


def main() -> None:
    """Main CLI entry point using Typer"""
    app()


if __name__ == "__main__":
    main()
