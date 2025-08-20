"""
Memov MCP Server - AI-assisted version control with automatic prompt recording

This MCP server provides intelligent memov integration that automatically:
- Records user prompts with file changes
- Handles new files vs modified files appropriately
- Provides seamless version control for AI-assisted development

Author: Memov Team
License: MIT
"""

import logging
import os
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from memov.core.manager import MemovManager, MemStatus
from starlette.requests import Request
from starlette.responses import PlainTextResponse

LOGGER = logging.getLogger(__name__)


class MemMCPTools:
    # Initialize FastMCP server
    mcp = FastMCP("Memov MCP Server")

    # Global context storage for user prompts and working directory
    _project_path = None
    _user_context = {
        "current_prompt": None,
        "timestamp": None,
        "session_id": None,
        # Indicates if the context has been cleaned, it should be reset after each interaction with the agent
        "context_cleaned": True,
    }

    def __init__(self, project_path: str) -> None:
        MemMCPTools._project_path = project_path

    def run(self, *args, **kwargs) -> None:
        """
        Run the MCP tools server.
        """
        LOGGER.info("Running MemMCPTools server...")
        # Start the FastMCP server
        MemMCPTools.mcp.run(*args, **kwargs)

    # Basic MCP tools
    @staticmethod
    @mcp.tool()
    def set_user_context(user_prompt: str, session_id: str | None = None) -> str:
        """
        Set the current user context for automatic tracking.

        **IMPORTANT: Call this tool FIRST when user makes any request.**

        **When to use this tool:**
        - At the beginning of any coding task
        - When user asks to modify, create, or delete files
        - When user requests new features or bug fixes
        - Before starting any development work

        **Example usage:**
        User: "Modify the content of 1.txt to become 2"
        → First call: set_user_context("Modify the content of 1.txt to become 2")
        → Then: perform the file modification
        → Finally: auto_mem_snap("1.txt")

        Args:
            user_prompt: The user's exact original prompt/request
            session_id: Optional session identifier

        Returns:
            Confirmation message
        """
        try:
            if MemMCPTools._project_path is None:
                raise ValueError(f"Project path is not set.")

            if not os.path.exists(MemMCPTools._project_path):
                raise ValueError(f"Project path '{MemMCPTools._project_path}' does not exist.")

            LOGGER.info(
                f"set_user_context called with: user_prompt='{user_prompt}', session_id='{session_id}'"
            )
            MemMCPTools._user_context["current_prompt"] = user_prompt
            MemMCPTools._user_context["timestamp"] = time.time()
            MemMCPTools._user_context["session_id"] = session_id or str(int(time.time()))
            MemMCPTools._user_context["context_cleaned"] = False

            result = (
                f"✅ User context set: {user_prompt[:100]}{'...' if len(user_prompt) > 100 else ''}"
            )
            LOGGER.info(f"set_user_context result: {result}")
            return result
        except Exception as e:
            LOGGER.error(f"Error in set_user_context: {e}", exc_info=True)
            return f"❌ Error setting user context: {str(e)}"

    @staticmethod
    @mcp.tool()
    def clean_user_context() -> str:
        """
        Clean the current user context after each interaction with the agent.

        **IMPORTANT: Call this tool AFTER completing any file modifications, code changes,
        or task completion to reset the user context.**

        **When to use this tool:**
        - After the user has completed their request
        - After recording changes using auto_mem_snap or similar tools
        - To ensure no stale context is carried over to the next interaction

        Returns:
            Confirmation message
        """
        try:
            LOGGER.info("clean_user_context called")
            MemMCPTools._user_context["current_prompt"] = None
            MemMCPTools._user_context["timestamp"] = None
            MemMCPTools._user_context["session_id"] = None
            MemMCPTools._user_context["context_cleaned"] = True

            result = "✅ User context cleaned successfully"
            LOGGER.info(f"clean_user_context result: {result}")
            return result
        except Exception as e:
            LOGGER.error(f"Error in clean_user_context: {e}", exc_info=True)
            return f"❌ Error cleaning user context: {str(e)}"

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_req: Request) -> PlainTextResponse:
        return PlainTextResponse("OK")

    # Core MCP tools for intelligent memov integration
    @staticmethod
    @mcp.tool()
    def mem_snap(files_changed: str) -> str:
        """Automatically create a mem snap using the stored user context with intelligent workflow.

        **IMPORTANT: Call this tool AFTER completing any file modifications, code changes,
        or task completion to automatically record the user's request and track changed files.**

        **Intelligent Workflow:**
        1. **Auto-initialize** - Creates memov repository if it doesn't exist
        2. **Status check** - Analyzes current file states (untracked, modified, clean)
        3. **Smart handling** -
        - **New files** → `mem track` (auto-commits with prompt)
        - **Modified files** → `mem snap` (records changes with prompt)
        4. **No conflicts** - Avoids redundant operations

        **When to use this tool:**
        - After modifying, creating, or deleting files
        - After completing user's coding requests
        - After making configuration changes
        - After completing any development task

        **When NOT to use this tool:**
        - For read-only operations (viewing files, searching)
        - For informational queries
        - Before making changes (use set_user_context first)
        - **After rename operations** - `mem rename` already handles the recording
        - **After remove operations** - `mem remove` already handles the recording

        Args:
            files_changed: Comma-separated relative path list of files that were modified/created/deleted (e.g. "file1.py,module1/file2.py")

        Returns:
            Detailed result of the complete workflow execution
        """
        try:
            LOGGER.info(
                f"auto_mem_snap called with: files_changed='{files_changed}', project_path='{MemMCPTools._project_path}'"
            )

            if (
                not MemMCPTools._user_context["current_prompt"]
                or MemMCPTools._user_context["context_cleaned"]
            ):
                result = "❌ No user context available. Please set user context first using set_user_context."
                LOGGER.warning(result)
                return result

            # Prepare the variables
            prompt = MemMCPTools._user_context["current_prompt"]
            memov_manager = MemovManager(project_path=MemMCPTools._project_path)
            LOGGER.info(f"Using prompt: {prompt}")

            # Step 1: Check if Memov is initialized
            if (check_status := memov_manager.check()) is MemStatus.SUCCESS:
                LOGGER.info("Memov is initialized.")
            else:
                LOGGER.warning(f"Memov is not initialized, return {check_status}.")
                if (init_status := memov_manager.init()) is not MemStatus.SUCCESS:
                    LOGGER.error(f"Failed to initialize Memov: {init_status}")
                    return f"❌ Failed to initialize Memov: {init_status}"

            # Step 2: Check file status
            ret_status, current_file_status = memov_manager.status()
            if ret_status is not MemStatus.SUCCESS:
                LOGGER.error(f"Failed to check file status: {ret_status}")
                return f"❌ Failed to check file status: {ret_status}"

            # Step 3: Snap files
            for file_changed in files_changed.split(","):
                file_changed_Path = Path(MemMCPTools._project_path) / file_changed.strip()

                for untracked_file in current_file_status["untracked"]:
                    if file_changed_Path.samefile(untracked_file):
                        track_status = memov_manager.track(
                            [str(file_changed_Path)], prompt=prompt, by_user=False
                        )
                        if track_status is not MemStatus.SUCCESS:
                            LOGGER.error(
                                f"Failed to track file {file_changed_Path}: {track_status}"
                            )
                            return f"❌ Failed to track file {file_changed_Path}: {track_status}"

                        break
                else:
                    snap_status = memov_manager.snapshot(
                        prompt=prompt, response=None, by_user=False
                    )
                    if snap_status is not MemStatus.SUCCESS:
                        LOGGER.error(
                            f"Failed to create snapshot for {file_changed_Path}: {snap_status}"
                        )
                        return (
                            f"❌ Failed to create snapshot for {file_changed_Path}: {snap_status}"
                        )

            # Build detailed result message
            result_parts = ["✅ Auto operation completed successfully"]
            result_parts.append(f"📝 Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
            result_parts.append(f"📂 File changed: {files_changed}")
            result = "\n".join(result_parts)
            LOGGER.info(f"Operation completed successfully: {result}")

            return result

        except Exception as e:
            error_msg = f"❌ Error creating auto snapshot: {str(e)}"
            LOGGER.error(error_msg, exc_info=True)
            return error_msg


def main():
    """Main entry point for the MCP server"""
    import asyncio

    mem_mcp_tools = MemMCPTools("D:/Projects/temp")
    asyncio.run(mem_mcp_tools.mcp.call_tool("set_user_context", {"user_prompt": "123"}))
    asyncio.run(mem_mcp_tools.mcp.call_tool("mem_snap", {"files_changed": "123.py"}))


if __name__ == "__main__":
    main()
