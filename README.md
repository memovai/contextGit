<p align="center">
  <a href="https://github.com/memovai/contextGit">
    <img src="docs/images/memov-banner.png" width="800px" alt="MemoV - The Memory Layer for AI Coding Agents">
  </a>
</p>

# Mem MCP Server

Mem extends coding agents with beyond-Git memory — auto-capturing **prompts**, **agent plans**, and **code changes** as bound context.
As your **coding partner**, it accelerates debugging, shares context in real time, reuses edits, prevents agentic infinite loops, and turns history into learning.

- 💬 [Join our Discord](https://discord.gg/YCN75dTh) and dive into smarter context engineering
- 🌐 [Visit memov.im](https://memov.im) to visualize your Mem history and supercharge existing GitHub repos


<div align="center">

[![Add to VS Code](https://img.shields.io/badge/Add%20to%20VS%20Code-007ACC?style=for-the-badge&logo=visual-studio-code&logoColor=white)](https://memov-vscode.vercel.app/)
[![Add to Cursor](https://img.shields.io/badge/Add%20to%20CURSOR-000000?style=for-the-badge&logo=visual-studio-code&logoColor=white)](https://memov-vscode.vercel.app/)

</div>

## Features

- 📒 **Context-bound memory**: Automatically track user prompts, agent plans, and code changes — independent of Git history
- 🐞 **Context-aware debugging**: Isolate faulty context and leverage it across LLMs for 5× faster fixing
- 🤝 **Team context sharing**: Real-time alignment with zero friction
- ♻️ **Change reuse**: Reapply past code edits by description to save tokens when iterating on a feature
- 🛑 **Loop guard**: Prevent runaway agent auto-generation by intervening and halting infinite loops
- 🔍 **History-driven optimization**: Use past records and failed generations as reference context to boost future outputs


## Installation

Please see [docs/installation.md](docs/installation.md) for detailed installation instructions.

## Installation for Contributors

Please see [docs/installation_for_dev.md](docs/installation_for_dev.md) for detailed installation instructions.

## MCP Tools

These are available to MCP clients through the server:

- `mem_snap(files_changed: str)`
  - Create a mem snapshot tied to the previously set user prompt. Handles untracked vs modified files intelligently. Argument is a comma-separated list of relative paths.

- `GET /health`
  - Returns "OK". Useful for IDE/agent readiness checks.


## License

MIT License. See `LICENSE`.
