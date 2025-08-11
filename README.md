# Mov - Memov MCP Server Manager

A powerful command-line tool for managing Memov MCP (Model Context Protocol) servers in the background.

<div align="center">

[![Add to VS Code](https://img.shields.io/badge/Add%20to%20VS%20Code-007ACC?style=for-the-badge&logo=visual-studio-code&logoColor=white)](https://memov-vscode.vercel.app/)
[![Add to Cursor](https://img.shields.io/badge/Add%20to%20CURSOR-000000?style=for-the-badge&logo=visual-studio-code&logoColor=white)](https://memov-vscode.vercel.app/)

</div>

## Features

- 🚀 **Easy Server Management**: Start, stop, and monitor MCP servers with simple commands
- 📁 **Workspace Monitoring**: Monitor specific project directories for AI-assisted development
- 🔄 **Background Operation**: Servers run in the background, freeing up your terminal
- 📊 **Status Monitoring**: Real-time status with uptime, memory usage, and health checks
- 📋 **Log Management**: Comprehensive logging and log viewing capabilities
- 🎯 **Multiple Servers**: Run multiple servers for different workspaces simultaneously

## Installation

### Prerequisites

- Python 3.10 or higher
- Poetry (for dependency management)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd mem-mcp
```

2. Install dependencies:
```bash
poetry install
```

3. The `mov` command is now available via Poetry:
```bash
poetry run mov --help
```

## Quick Start

### Start a Server

Start monitoring a workspace directory:

```bash
poetry run mov start --workspace /path/to/your/project --port 8080
```

### Check Status

View all running servers:

```bash
poetry run mov status
```

### Stop a Server

Stop a specific server:

```bash
poetry run mov stop --workspace /path/to/your/project --port 8080
```

Stop all servers:

```bash
poetry run mov stop --all
```

## Command Reference

### `mov start`

Start a new MCP server in the background.

```bash
mov start --workspace <path> --port <port> [--host <host>]
```

**Options:**
- `--workspace`: Path to the project directory to monitor (required)
- `--port`: Port number to run the server on (required)
- `--host`: Host to bind to (default: 127.0.0.1)

**Example:**
```bash
poetry run mov start --workspace /home/user/my-project --port 8080
```

### `mov stop`

Stop running server(s).

```bash
mov stop [--workspace <path>] [--port <port>] [--all]
```

**Options:**
- `--workspace`: Stop all servers for this workspace
- `--port`: Stop all servers on this port
- `--all`: Stop all running servers

**Examples:**
```bash
# Stop specific server
poetry run mov stop --workspace /home/user/my-project --port 8080

# Stop all servers for a workspace
poetry run mov stop --workspace /home/user/my-project

# Stop all servers on a port
poetry run mov stop --port 8080

# Stop all servers
poetry run mov stop --all
```

### `mov status`

Show status of all running servers.

```bash
mov status
```

**Output includes:**
- Server status (running/dead)
- Workspace path
- MCP URL
- Uptime
- Memory usage
- Process ID


## Configuration

Mov stores its configuration and logs in `~/.mov/`:

```
~/.mov/
├── servers.json    # Server registry and status
└── logs/           # Server log files
    ├── project1_8080.log
    └── project2_8081.log
```

## Integration with AI Tools

### Cursor Integration

1. Start a Mov server:
```bash
poetry run mov start --workspace /path/to/project --port 8080
```

2. In Cursor, go to Settings → Extensions → MCP
3. Add a new MCP server with URL: `http://127.0.0.1:8080/mcp`

### Claude Desktop Integration

1. Start a Mov server:
```bash
poetry run mov start --workspace /path/to/project --port 8080
```

2. Configure Claude Desktop to use the MCP server URL

## Development

### Project Structure

```
mem-mcp/
├── memov_mcp/                      # Main package
│   ├── __init__.py
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── mov_cli.py              # Main CLI interface
│   │   └── mov_logger.py           # Log management
│   ├── server/
│   │   ├── __init__.py
│   │   ├── mcp_server.py           # Core MCP server implementation
│   │   ├── mcp_http_server.py      # HTTP wrapper for MCP server
│   │   └── start_mcp.py            # MCP server launcher
│   └── utils/
│       └── __init__.py
├── tests/                          # Test files
├── docs/                           # Documentation
├── pyproject.toml                  # Project configuration
└── README.md                       # This file
```

### Running Tests

```bash
poetry run pytest
```

### Code Formatting

```bash
poetry run black .
poetry run isort .
```

### Pre-commit Hooks

```bash
poetry run pre-commit run --all-files
```

## Troubleshooting

### Server Won't Start

1. Check if the port is already in use:
```bash
netstat -tulpn | grep :8080
```

2. Verify the workspace path exists and is accessible

3. Check logs for error messages:
```bash
poetry run mov logs --workspace /path/to/project --port 8080
```

### Server Shows as "Dead"

1. Check if the process is actually running:
```bash
ps aux | grep start_mcp.py
```

2. Restart the server:
```bash
poetry run mov stop --workspace /path/to/project --port 8080
poetry run mov start --workspace /path/to/project --port 8080
```

### Permission Issues

Ensure you have write permissions to:
- The workspace directory
- `~/.mov/` configuration directory

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section
- Review the logs for error messages
- Open an issue on GitHub
