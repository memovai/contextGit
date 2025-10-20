<p align="center">
  <a href="https://github.com/memovai/memov">
    <img src="docs/images/memov-banner.png" width="800px" alt="MemoV - The Memory Layer for AI Coding Agents">
  </a>
</p>

# Memov - AI Coding Version Control

**AI coding version control on top of Git. Track not just what changed, but _why_ it changed.**

Memov extends coding agents with beyond-Git memory — auto-capturing **prompts**, **agent plans**, and **code changes** as bound context.
As your **coding partner**, it accelerates debugging, shares context in real time, reuses edits, prevents agentic infinite loops, and turns history into learning.

- 💬 [Join our Discord](https://discord.gg/YCN75dTh) and dive into smarter context engineering
- 🌐 [Visit memov.im](https://memov.im) to visualize your Mem history and supercharge existing GitHub repos

<div align="center">

[![Add to VS Code](https://img.shields.io/badge/Add%20to%20VS%20Code-007ACC?style=for-the-badge&logo=visual-studio-code&logoColor=white)](https://memov-vscode.vercel.app/)
[![Add to Cursor](https://img.shields.io/badge/Add%20to%20CURSOR-000000?style=for-the-badge&logo=visual-studio-code&logoColor=white)](https://memov-vscode.vercel.app/)

</div>

## Why Memov?

Traditional version control systems like Git are great at tracking code **changes**, but not the **reasoning** behind them. In an age of AI-assisted coding, developers interact with LLMs through prompts, generate responses, and iteratively refine their code — but Git only sees the final result.

**Memov fills this gap.** It versions:

- 🤖 The **prompt** you gave to the AI
- 📥 The **response** you received
- 🧾 The **actual diff** made to your code
- 🧩 The **source** (Agent or User)

## Features

### Core Memov CLI
- 📒 **Version prompts & responses**: Track the "why" behind code changes
- 🔄 **Snapshot workflow**: Create snapshots with or without file changes
- 🎯 **Smart file tracking**: Handles new files vs modified files intelligently
- 🕐 **History navigation**: Jump to any snapshot and inspect full context
- 🔍 **Status checking**: Compare working directory to latest snapshot

### MCP Server Integration
- 📒 **Context-bound memory**: Automatically track user prompts, agent plans, and code changes — independent of Git history
- 🐞 **Context-aware debugging**: Isolate faulty context and leverage it across LLMs for 5× faster fixing
- 🤝 **Team context sharing**: Real-time alignment with zero friction
- ♻️ **Change reuse**: Reapply past code edits by description to save tokens when iterating on a feature
- 🛑 **Loop guard**: Prevent runaway agent auto-generation by intervening and halting infinite loops
- 🔍 **History-driven optimization**: Use past records and failed generations as reference context to boost future outputs

## Quick Start

### Using the CLI

```bash
# Initialize memov in your project
mem init

# Track files with context
mem track file.py -p "Initial implementation" -r "Added core logic"

# Create a snapshot
mem snap -p "Refactored config parser" -r "Switched to YAML"

# View history
mem history

# Jump to a previous snapshot
mem jump <snapshot-id>
```

### Using with AI Coding Assistants

Install the MCP server for your IDE:

- **VS Code / Cursor**: See [docs/installation.md](docs/installation.md)
- **Claude Code**: `claude mcp add mem-mcp --scope project -- uvx --from git+https://github.com/memovai/memov.git mem-mcp-launcher stdio $(pwd)`

The MCP server automatically tracks your AI interactions!

## Installation

### For Users

Please see [docs/installation.md](docs/installation.md) for detailed installation instructions.

### For Contributors

Please see [docs/installation_for_dev.md](docs/installation_for_dev.md) for detailed installation instructions.

## Available Commands

### Core CLI (`mem`)
- `mem init` - Initialize memov repository
- `mem track` - Track files with context
- `mem snap` - Create snapshot
- `mem rename` - Rename files
- `mem remove` - Remove files
- `mem history` - View history
- `mem show` - Show snapshot details
- `mem jump` - Jump to snapshot
- `mem status` - Check status
- `mem amend` - Update commit notes

### MCP Server Tools

The MCP server provides these tools to AI coding assistants:

- `snap(user_prompt, original_response, agent_plan, files_changed)` - Automatically create mem snapshots with full context
- `GET /health` - Health check endpoint


## License

MIT License. See `LICENSE`.
