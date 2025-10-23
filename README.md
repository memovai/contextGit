<p align="center">
  <a href="https://github.com/memovai/memov">
    <img src="docs/images/memov-banner.png" width="800px" alt="MemoV - The Memory Layer for AI Coding Agents">
  </a>
</p>

# Never forget a commit. Never touch your Git.

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Discord](https://img.shields.io/badge/Discord-Join%20Server-7289da?logo=discord&logoColor=white)](https://discord.gg/un54aD7Hug)
[![Twitter Follow](https://img.shields.io/twitter/follow/ssslvky?style=social)](https://x.com/ssslvky)

</div>

MemoV = Prompt + Context + CodeDiff

<p align="center">
  <img src="docs/images/readme.gif" alt="MemoV Demo" width="800px">
</p>

It gives AI coding agents a traceable memory layer beyond Git — auto-capturing **every prompt**, **agent plan**, and **code change** in a separate timeline. Work freely with AI, iterate fast, and keep your Git history clean. When you're ready, cherry-pick what matters for Git commits.

- 💬 [Join our Discord](https://discord.gg/un54aD7Hug) and dive into smarter context engineering
- 🌐 [Visit memov.ai](https://memov.ai) to visualize your coding memory and supercharge existing GitHub repos


<div align="center">

[![Add to VS Code](https://img.shields.io/badge/Add%20to%20VS%20Code-007ACC?style=for-the-badge&logo=visual-studio-code&logoColor=white)](https://memov-vscode.vercel.app/)
[![Add to Cursor](https://img.shields.io/badge/Add%20to%20CURSOR-000000?style=for-the-badge&logo=visual-studio-code&logoColor=white)](https://memov-vscode.vercel.app/)

</div>

## Features

- 📒 **Context-bound memory**: Automatically track user GitDiffs, prompts, and agent plans — independent of Git history
- 🐞 **Vibe debugging**: Isolate faulty context and leverage it across LLMs for 5× faster fixing
- 🤝 **Team context sharing**: Real-time alignment with zero friction
- ♻️ **Change reuse**: Reapply past code edits by description to save tokens when iterating on a feature
- 🔍 **History-driven optimization**: Use past records and failed generations as reference context to boost future outputs


## Installation

Please see [docs/installation.md](docs/installation.md) for detailed installation instructions.

## Installation for Contributors

Please see [docs/installation_for_dev.md](docs/installation_for_dev.md) for detailed installation instructions.

## How It Works

### Core: Git Plumbing Commands

MemoV doesn't reinvent version control — it **leverages Git's low-level plumbing commands** to create a separate, parallel timeline:

- **Bare repository** (`.mem/memov.git`): Stores all snapshots independently from your main Git repo
- **Git objects** (blobs, trees, commits): Uses the same proven data structures as Git
- **No working tree pollution**: Changes are committed directly to the bare repo without touching your workspace
- **Full history access**: Jump between any snapshot, diff changes, or cherry-pick edits

This means MemoV is:
- ✅ **Fast** - leverages Git's optimized object storage
- ✅ **Reliable** - built on Git's battle-tested foundation
- ✅ **Space-efficient** - deduplication through content-addressable storage
- ✅ **Completely separate** - zero interference with your Git workflow
- ✅ **Token-efficient** - no need to waste tokens asking agents to write commit messages or run git commands

### MCP Integration: Automatic Context Capture

The MCP server sits between your AI coding agent and MemoV, automatically capturing every interaction:

**1. Agent makes changes** → AI edits files in your workspace

**2. MCP `snap()` is called** → Automatically triggered after each AI response with:
   - `user_prompt`: What you asked for
   - `agent_plan`: What the AI decided to do (file-by-file summary)
   - `files_changed`: Which files were modified/created

**3. Smart file handling**:
   - **Manual edits detected?** → Captured first in a separate commit (marked as "User")
   - **New files?** → Tracked via `mem track` (adds to timeline)
   - **Modified tracked files?** → Snapshotted via `mem snap` (records diff)

**4. Result**: Every AI interaction becomes a commit with full context — prompt + plan + code changes bound together

**Example workflow**:
```
User: "Add error handling to the API"
  ↓
AI changes api/routes.py
  ↓
MCP snap() called automatically
  ↓
Commit created:
  - Prompt: "Add error handling to the API"
  - Plan: ["api/routes.py: Added try-catch wrapper and error logging"]
  - Diff: +15 lines in handle_request()
```

This creates a **traceable memory** where you can always see:
- What you asked for
- What the AI planned to do
- What actually changed in the code

**Why this saves tokens:**

Traditional approach:
```
You: "Add error handling"
Agent: *makes changes*
You: "Now commit these changes with a good message"
Agent: *reads files again, writes commit message, runs git commands*
```
❌ Wastes tokens on: re-reading files, generating commit messages, git operations

MemoV approach:
```
You: "Add error handling"
Agent: *makes changes*
MCP: *automatically captures everything*
```
✅ Zero extra tokens - context is captured instantly without agent involvement


## License

MIT License. See `LICENSE`.
