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
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from memov.core.manager import MemovManager, MemStatus

LOGGER = logging.getLogger(__name__)


class MemMCPTools:
    # Initialize FastMCP server
    mcp = FastMCP("Memov MCP Server")

    # Global context storage for user prompts and working directory
    _project_path = None
    _user_context = {
        "current_prompt": None,
        "current_response": None,
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

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_req: Request) -> PlainTextResponse:
        return PlainTextResponse("OK")

    # Core MCP tools for intelligent memov integration
    @staticmethod
    @mcp.tool()
    def snap(
        user_prompt: str, original_response: str, agent_plan: list[str], files_changed: str = ""
    ) -> str:
        """Record every user interaction - MUST be called at the end of EVERY response.

        **CRITICAL: Call this tool for EVERY user interaction, no exceptions!**

        This tool ensures complete interaction history by recording:
        - User prompts (questions, requests, commands)
        - Agent responses (answers, explanations, code changes)
        - Files changed (if any)

        **When to call (ALWAYS):**
        - User asked a question → Call with files_changed=""
        - User requested code changes → Call with files_changed="file1.py,file2.js"
        - User just chatting → Call with files_changed=""
        - Operation failed → Still call to record what happened
        - Read-only operations (viewing, searching) → Call with files_changed=""

        **When NOT to call:**
        - After rename operations - `mem rename` already handles the recording
        - After remove operations - `mem remove` already handles the recording

        **Intelligent Workflow:**
        1. **Auto-initialize** - Creates memov repository if it doesn't exist
        2. **For interactions without file changes** - Records prompt and response only
        3. **For interactions with file changes:**
           - Status check - Analyzes current file states (untracked, modified, clean)
           - New files → `mem track` (auto-commits with prompt)
           - Modified files → `mem snap` (records changes with prompt)

        Args:
            user_prompt: The user's exact original prompt/request
            original_response: The exact original full response from the AI agent
                Note:
                    - Make sure to include the entire response, including any code blocks or explanations.

                Example:
                    Chat content:
                        [User Prompt]: Change the print statement in hello.py to "Hello World"
                        [AI Response]: I can see that the file currently shows "Hello Earth" but you mentioned the edits were undone. Let me check the current content of the file to see what needs to be changed. I can see the file currently has "Hello Earth". I'll change it back to "Hello World" as requested.
                        ```
                        Made changes.
                        ```
                        I've successfully changed "Hello Earth" back to "Hello World" in both the comment and the print statement in your hello.py file. The script will now output "Hello World" when run.
                    original_response:
                        I can see that the file currently shows "Hello Earth" but you mentioned the edits were undone. Let me check the current content of the file to see what needs to be changed. I can see the file currently has "Hello Earth". I'll change it back to "Hello World" as requested.
                        ```
                        Made changes.
                        ```
                        I've successfully changed "Hello Earth" back to "Hello World" in both the comment and the print statement in your hello.py file. The script will now output "Hello World" when run.
            agent_plan: High-level summary of the major changes, organized by file
                Notes:
                    - Each step should describe ONE significant modification to a specific file
                    - Format: "[file]: [what changed]"
                    - Aim for 2-5 high-level steps that map to distinct logical changes
                    - Focus on WHAT was changed in each file, not HOW the change was made
                    - Group all related changes to the same file into one step when they serve the same purpose

                Format:
                    [
                        "<filename>: <concise description of what changed>",
                        "<filename>: <concise description of what changed>",
                        ...
                    ]

                Good Examples (file-focused, concise):
                    Example 1 - Multiple files changed:
                        [User Prompt]: Add error handling and logging to the API endpoint
                        agent_plan:
                        [
                            "api/routes.py: Added try-catch error handling and logging integration",
                            "utils/logger.py: Created configure_logging() helper function"
                        ]

                    Example 2 - Multiple files for feature:
                        [User Prompt]: Refactor database connection to use connection pooling
                        agent_plan:
                        [
                            "db/connection.py: Refactored to use connection pool instead of direct connections",
                            "db/pool.py: Implemented ConnectionPool class with acquire/release methods",
                            "config/settings.py: Added connection pool configuration parameters"
                        ]

                    Example 3 - Simple single file change:
                        [User Prompt]: Fix typo in error message
                        agent_plan:
                        [
                            "handlers/auth.py: Fixed typo in error message"
                        ]

                    Example 4 - New files created:
                        [User Prompt]: Create a user authentication module
                        agent_plan:
                        [
                            "auth/login.py: Created login handler with JWT token generation",
                            "auth/middleware.py: Created authentication middleware",
                            "tests/test_auth.py: Added test cases for login and middleware"
                        ]

                Bad Examples (too vague, too granular, or missing file):
                    ❌ "Updated the code" (no file specified)
                    ❌ "api/routes.py: Made changes" (too vague, what changed?)
                    ❌ "Added a line" (no file, no context)
                    ❌ "Fixed the bug" (no file specified)
                    ❌ "api/routes.py: Added import, created variable, wrote if statement, added return, saved file" (too granular - should be one logical change)
                    ❌ "Added error handling in handle_request(), error_handler(), and validate_input() functions" (no file specified)

                Key Principles:
                    - Always start with the file path
                    - Describe the logical change, not implementation details
                    - One file, one logical purpose = one step
                    - Be concise but specific about what changed

            files_changed: Comma-separated relative path list of files that were modified/created/deleted
                          (e.g. "file1.py,module1/file2.py"), or empty string "" if no files changed

        Returns:
            Detailed result of the complete workflow execution
        """
        try:
            LOGGER.info(
                f"snap called with: files_changed='{files_changed}', project_path='{MemMCPTools._project_path}'"
            )
            LOGGER.info(
                f"Using prompt: {user_prompt}, response: {original_response}, plan: {agent_plan}"
            )

            if MemMCPTools._project_path is None:
                raise ValueError(f"Project path is not set.")

            if not os.path.exists(MemMCPTools._project_path):
                raise ValueError(f"Project path '{MemMCPTools._project_path}' does not exist.")

            # Concatenate the agent plan into the original response for full context
            agent_plan_dict = {
                "plan" + str(i + 1): plan_step for i, plan_step in enumerate(agent_plan)
            }
            full_response = (
                "[Agent Plan]:\n"
                + '"planning_strategy": '
                + str(agent_plan_dict)
                + "\n\n[Agent Response]:\n"
                + original_response
            )

            # Prepare the variables
            memov_manager = MemovManager(project_path=MemMCPTools._project_path)

            # Step 1: Check if Memov is initialized
            if (check_status := memov_manager.check()) is MemStatus.SUCCESS:
                LOGGER.info("Memov is initialized.")
            else:
                LOGGER.warning(f"Memov is not initialized, return {check_status}.")
                if (init_status := memov_manager.init()) is not MemStatus.SUCCESS:
                    LOGGER.error(f"Failed to initialize Memov: {init_status}")
                    return f"[ERROR] Failed to initialize Memov: {init_status}"

            # Step 2: Handle two cases - with or without file changes
            if not files_changed or files_changed.strip() == "":
                # Case 1: No file changes - just record the interaction without snapshotting files
                # We don't call snapshot() here because that would commit all tracked files,
                # including any manual changes the user made
                LOGGER.info("No files changed, skipping snapshot (prompt-only interaction)")

                # TODO: In the future, we could record prompt-only interactions using git notes
                # or a separate metadata system, without creating commits

                result_parts = [
                    "[SUCCESS] Interaction recorded (no file changes, no snapshot created)"
                ]
                result_parts.append(f"Prompt: {user_prompt}")
                result_parts.append(f"Response: {len(full_response)} characters")
                result = "\n".join(result_parts)
                LOGGER.info(f"Interaction recorded successfully: {result}")
                return result

            else:
                # Case 2: Has file changes - track/snap files
                LOGGER.info(f"Processing file changes: {files_changed}")

                # Check file status
                ret_status, current_file_status = memov_manager.status()
                if ret_status is not MemStatus.SUCCESS:
                    LOGGER.error(f"Failed to check file status: {ret_status}")
                    return f"[ERROR] Failed to check file status: {ret_status}"

                # Build set of AI-changed files (from files_changed parameter)
                ai_changed_files = set()
                for file_changed in files_changed.split(","):
                    file_changed = file_changed.strip()
                    if file_changed:
                        file_path = Path(MemMCPTools._project_path) / file_changed
                        ai_changed_files.add(file_path.resolve())

                # Detect manual edits: modified files that are NOT in AI-changed list
                manual_edit_files = []
                project_path_resolved = Path(MemMCPTools._project_path).resolve()
                for modified_file in current_file_status["modified"]:
                    # modified_file is already a Path object with absolute path (resolved)
                    if modified_file.resolve() not in ai_changed_files:
                        # Use relative path (relative to project_path) for snapshot
                        try:
                            rel_path = str(modified_file.relative_to(project_path_resolved))
                            manual_edit_files.append(rel_path)
                        except ValueError:
                            # File is outside project path, use absolute path
                            LOGGER.warning(f"File {modified_file} is outside project path")
                            manual_edit_files.append(str(modified_file))

                # Step 1: Capture manual edits first (if any)
                if manual_edit_files:
                    LOGGER.info(f"Detected manual edits: {manual_edit_files}")
                    manual_snap_status = memov_manager.snapshot(
                        file_paths=manual_edit_files,
                        prompt="Manual edits detected before AI operation",
                        response=f"User manually edited: {', '.join([Path(f).name for f in manual_edit_files])}",
                        by_user=True,
                    )
                    if manual_snap_status is not MemStatus.SUCCESS:
                        LOGGER.error(f"Failed to snapshot manual edits: {manual_snap_status}")
                        return f"[ERROR] Failed to snapshot manual edits: {manual_snap_status}"
                    LOGGER.info(f"Captured manual edits in separate commit")

                # Step 2: Process AI changes
                # Separate AI-changed files into untracked and modified
                files_to_track = []
                files_to_snap = []
                files_processed = []

                for file_changed in files_changed.split(","):
                    file_changed = file_changed.strip()
                    if not file_changed:
                        continue

                    file_changed_Path = Path(MemMCPTools._project_path) / file_changed

                    # Check if file is untracked
                    is_untracked = False
                    for untracked_file in current_file_status["untracked"]:
                        if file_changed_Path.samefile(untracked_file):
                            is_untracked = True
                            break

                    if is_untracked:
                        files_to_track.append(str(file_changed_Path))
                        files_processed.append(f"{file_changed} (tracked)")
                    else:
                        files_to_snap.append(str(file_changed_Path))
                        files_processed.append(f"{file_changed} (snapped)")

                # Track all untracked files at once
                if files_to_track:
                    LOGGER.info(f"Tracking new files: {files_to_track}")
                    track_status = memov_manager.track(
                        files_to_track,
                        prompt=user_prompt,
                        response=full_response,
                        by_user=False,
                    )
                    if track_status is not MemStatus.SUCCESS:
                        LOGGER.error(f"Failed to track files: {track_status}")
                        return f"[ERROR] Failed to track files: {track_status}"

                # Snap all AI-modified files at once (fine-grained snapshot)
                if files_to_snap:
                    LOGGER.info(f"Snapping AI-modified files: {files_to_snap}")
                    snap_status = memov_manager.snapshot(
                        file_paths=files_to_snap,
                        prompt=user_prompt,
                        response=full_response,
                        by_user=False,
                    )
                    if snap_status is not MemStatus.SUCCESS:
                        LOGGER.error(f"Failed to snap files: {snap_status}")
                        return f"[ERROR] Failed to snap files: {snap_status}"

                # Build detailed result message
                result_parts = ["[SUCCESS] Changes recorded successfully"]
                if manual_edit_files:
                    result_parts.append(
                        f"Manual edits captured: {', '.join([Path(f).name for f in manual_edit_files])}"
                    )
                result_parts.append(f"Prompt: {user_prompt}")
                result_parts.append(f"Response: {len(full_response)} characters")
                result_parts.append(f"AI changes: {', '.join(files_processed)}")
                result = "\n".join(result_parts)
                LOGGER.info(f"Operation completed successfully: {result}")
                return result

        except Exception as e:
            error_msg = f"[ERROR] Error in snap: {str(e)}"
            LOGGER.error(error_msg, exc_info=True)
            return error_msg


def main():
    """Main entry point for the MCP server"""
    import asyncio

    mem_mcp_tools = MemMCPTools("D:/Projects/temp")
    asyncio.run(mem_mcp_tools.mcp.call_tool("mem_snap", {"files_changed": "123.py"}))


if __name__ == "__main__":
    main()
