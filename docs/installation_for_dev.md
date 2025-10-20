
## Installation for Contributors

### Prerequisites

- **Python 3.11+** - Required for all functionality
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** - Modern Python package and project manager

### Quick Setup

1. **Clone and install dependencies:**
   ```bash
   git clone git@github.com:memovai/memov.git
   cd memov
   uv sync
   ```

2. **Set up development tools:**
   ```bash
   uv pip install pre-commit
   uv run pre-commit install
   ```


## Available Commands

The project provides three main entry points:

| Command | Purpose | Module |
|---------|---------|---------|
| `mem` | Core CLI for memov operations | `memov.main:main` |
| `mem-mcp-server` | Server management CLI | `mem_mcp_server.cli.server_cli:main` |
| `mem-mcp-launcher` | Direct MCP runtime launcher | `mem_mcp_server.server.mcp_launcher:main` |

**Run commands without global installation:**
```bash
uv run mem --help
uv run mem-mcp-server --help
uv run mem-mcp-launcher --help
```

## Configuration and Logs

Default config directory: `~/.mem_mcp_server`

```
~/.mem_mcp_server/
└── logs/           # Server log files
```