import io
import json
import logging
import os
import tarfile
import traceback
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Optional

import pathspec

from memov.core.git import GitManager
from memov.utils.print_utils import Color
from memov.utils.string_utils import short_msg

LOGGER = logging.getLogger(__name__)


class MemStatus(Enum):
    """Mem operation status."""

    SUCCESS = "success"
    PROJECT_NOT_FOUND = "project_not_found"
    BARE_REPO_NOT_FOUND = "bare_repo_not_found"
    FAILED_TO_COMMIT = "failed_to_commit"
    UNKNOWN_ERROR = "unknown_error"


class MemovManager:
    def __init__(
        self,
        project_path: str,
        default_name: Optional[str] = None,
        default_email: Optional[str] = None,
    ) -> None:
        """Initialize the MemovManager."""
        self.project_path = project_path
        self.default_name = default_name
        self.default_email = default_email

        # Memov config paths
        self.mem_root_path = os.path.join(self.project_path, ".mem")
        self.bare_repo_path = os.path.join(self.mem_root_path, "memov.git")
        self.branches_config_path = os.path.join(self.mem_root_path, "branches.json")
        self.memignore_path = os.path.join(self.project_path, ".memignore")

    def check(self, only_basic_check: bool = False) -> MemStatus:
        """Check some basic conditions for the memov repo."""
        # Check project path
        if not os.path.exists(self.project_path):
            LOGGER.error(f"Project path {self.project_path} does not exist.")
            return MemStatus.PROJECT_NOT_FOUND

        # If only basic check is required, return early
        if only_basic_check:
            LOGGER.debug("Only basic check is required, skipping further checks.")
            return MemStatus.SUCCESS

        # Check the bare repo
        if not os.path.exists(self.bare_repo_path):
            LOGGER.error(
                f"Memov bare repo {self.bare_repo_path} does not exist.\nPlease run `mem -h` to see the help message."
            )
            return MemStatus.BARE_REPO_NOT_FOUND

        return MemStatus.SUCCESS

    def version(self) -> str:
        """Show version information."""
        # Read version from pyproject.toml or package metadata
        import importlib.metadata

        try:
            version = importlib.metadata.version("memov")
            LOGGER.info(f"memov version {version}")
        except importlib.metadata.PackageNotFoundError:
            version = "unknown"
            LOGGER.info("memov version unknown (development)")

        return version

    def init(self) -> MemStatus:
        """Initialize a memov repo if it doesn't exist."""
        try:
            # Initialize .mem directory
            os.makedirs(self.mem_root_path, exist_ok=True)
            if not os.path.exists(self.bare_repo_path):
                GitManager.create_bare_repo(self.bare_repo_path)

            # Ensure .memignore exists and is tracked
            if not os.path.exists(self.memignore_path):
                with open(self.memignore_path, "w") as f:
                    f.write("# Add files/directories to ignore from memov tracking\n")
                    f.write("# Ignore all hidden files (starting with .)\n")
                    f.write(".*\n")
                self.track(
                    [self.memignore_path],
                    prompt="Initialize .memignore",
                    response="Created default .memignore file",
                )

            return MemStatus.SUCCESS
        except Exception as e:
            LOGGER.error(f"Error initializing memov project: {e}")
            return MemStatus.UNKNOWN_ERROR

    def track(
        self,
        file_paths: list[str],
        prompt: Optional[str] = None,
        response: Optional[str] = None,
        by_user: bool = False,
    ) -> MemStatus:
        """Track files in the memov repo, generating a commit to record the operation."""
        try:
            # Return early if no file paths are provided
            if not file_paths:
                LOGGER.error("No files to track.")
                return MemStatus.SUCCESS

            # Get the head commit of the memov repo
            head_commit = GitManager.get_commit_id_by_ref(
                self.bare_repo_path, "refs/memov/HEAD", verbose=False
            )
            if not head_commit:  # If HEAD commit does not exist, try to get the main branch commit
                head_commit = GitManager.get_commit_id_by_ref(
                    self.bare_repo_path, "main", verbose=False
                )
            if not head_commit:  # If still no commit, set to None
                head_commit = None

            # Get all currently tracked files in the memov repo
            tracked_file_rel_paths, tracked_file_abs_paths = [], []

            if head_commit:
                tracked_file_rel_paths, tracked_file_abs_paths = GitManager.get_files_by_commit(
                    self.bare_repo_path, head_commit
                )

            # Only track new files that are not already tracked
            new_files = self._filter_new_files(file_paths, tracked_file_rel_paths)

            if len(new_files) == 0:
                LOGGER.warning(
                    "No new files to track. All provided files are already tracked or ignored."
                )
                return MemStatus.SUCCESS

            # Build tree_entries, including all tracked_files and new files
            all_files = {}
            for rel_file, abs_path in zip(tracked_file_rel_paths, tracked_file_abs_paths):
                all_files[rel_file] = abs_path
            for rel_file, abs_path in new_files:
                all_files[rel_file] = abs_path

            commit_msg = "Track files\n\n"
            commit_msg += f"Files: {', '.join([rel_file for rel_file, _ in new_files])}\n"
            commit_msg += (
                f"Prompt: {prompt}\nResponse: {response}\nSource: {'User' if by_user else 'AI'}"
            )

            commit_hash = self._commit(commit_msg, all_files)
            if not commit_hash:
                LOGGER.error("Failed to commit tracked files.")
                return MemStatus.FAILED_TO_COMMIT

            LOGGER.info(
                f"Tracked file(s) in memov repo and committed: {[abs_path for _, abs_path in new_files]}"
            )

            return MemStatus.SUCCESS
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            filename, lineno, func, code = tb[-1]  # last frame
            LOGGER.error(f"Error tracking files in memov repo: {e}, {filename}:{lineno} - {code}")
            return MemStatus.UNKNOWN_ERROR

    def snapshot(
        self, prompt: Optional[str] = None, response: Optional[str] = None, by_user: bool = False
    ) -> MemStatus:
        """Create a snapshot of the current project state in the memov repo, generating a commit to record the operation."""
        try:
            # Get all tracked files in the memov repo and their previous blob hashes
            tracked_file_rel_paths, tracked_file_abs_paths = [], []
            head_commit = GitManager.get_commit_id_by_ref(
                self.bare_repo_path, "refs/memov/HEAD", verbose=False
            )
            if head_commit:
                tracked_file_rel_paths, tracked_file_abs_paths = GitManager.get_files_by_commit(
                    self.bare_repo_path, head_commit
                )

            # Return early if no tracked files are found
            if len(tracked_file_rel_paths) == 0:
                LOGGER.warning("No tracked files to snapshot. Please track files first.")
                return MemStatus.SUCCESS

            # Filter out new files that are not tracked or should be ignored
            new_files = self._filter_new_files([self.project_path], tracked_file_rel_paths)

            # If there are untracked files, warn the user
            if len(new_files) != 0:
                LOGGER.warning(
                    f"{Color.RED}Untracked files present: {new_files}. They will not be included in the snapshot.{Color.RESET}"
                )

            # Commit to the bare repo
            commit_msg = "Create snapshot\n\n"
            commit_msg += (
                f"Prompt: {prompt}\nResponse: {response}\nSource: {'User' if by_user else 'AI'}"
            )
            commit_file_paths = {}
            for rel_path, abs_path in zip(tracked_file_rel_paths, tracked_file_abs_paths):
                commit_file_paths[rel_path] = abs_path

            self._commit(commit_msg, commit_file_paths)
            LOGGER.info("Snapshot created in memov repo.")

            return MemStatus.SUCCESS
        except Exception as e:
            LOGGER.error(f"Error creating snapshot in memov repo: {e}")
            return MemStatus.UNKNOWN_ERROR

    def rename(
        self,
        old_file_path: str,
        new_file_path: str,
        prompt: Optional[str] = None,
        response: Optional[str] = None,
        by_user: bool = False,
    ) -> None:
        """Rename a tracked file in the memov repo, and generate a commit to record the operation. Supports branches."""
        try:
            old_abs_path = os.path.abspath(old_file_path)
            new_abs_path = os.path.abspath(new_file_path)
            old_rel_path = os.path.relpath(old_abs_path, self.project_path)
            old_file_existed = os.path.exists(old_abs_path)
            new_file_existed = os.path.exists(new_abs_path)

            # Return early if both paths are existing
            if old_file_existed and new_file_existed:
                LOGGER.error(f"New file path {new_abs_path} already exists.")
                return

            # Return early if both paths are not existing
            if not old_file_existed and not new_file_existed:
                LOGGER.error(
                    f"Neither old file path {old_file_path} nor new file path {new_file_path} exists."
                )
                return

            # Return early if the file is tracked on the current branch
            head_commit = GitManager.get_commit_id_by_ref(
                self.bare_repo_path, "refs/memov/HEAD", verbose=False
            )
            tracked_files = []
            if head_commit:
                tracked_files, _ = GitManager.get_files_by_commit(self.bare_repo_path, head_commit)

            if old_rel_path not in tracked_files:
                LOGGER.warning(
                    f"{Color.RED}File {old_rel_path} is not tracked, cannot rename.{Color.RESET}"
                )
                return

            # If the old file exists, rename it to the new file path
            if old_file_existed:
                os.rename(old_abs_path, new_abs_path)
                commit_msg = "Rename file\n\n"
            else:
                commit_msg = "Rename file (already renamed by user)\n\n"
            commit_msg += f"Files: {old_rel_path} -> {new_file_path}\n"
            commit_msg += (
                f"Prompt: {prompt}\nResponse: {response}\nSource: {'User' if by_user else 'AI'}"
            )

            # Commit the rename in the memov repo
            file_list = self._filter_new_files([self.project_path], tracked_file_rel_paths=None)
            file_list = {rel_path: abs_path for rel_path, abs_path in file_list}
            self._commit(commit_msg, file_list)

            LOGGER.info(
                f"Renamed file in memov repo from {old_file_path} to {new_file_path} and committed."
            )
        except Exception as e:
            LOGGER.error(f"Error renaming file in memov repo: {e}")

    def remove(
        self,
        file_path: str,
        prompt: Optional[str] = None,
        response: Optional[str] = None,
        by_user: bool = False,
    ) -> None:
        """Remove a tracked file from the memov repo, and generate a commit to record the operation."""
        try:
            target_abs_path = os.path.abspath(file_path)
            target_rel_path = os.path.relpath(target_abs_path, self.project_path)

            # Check if the file is tracked on the current branch
            head_commit = GitManager.get_commit_id_by_ref(
                self.bare_repo_path, "refs/memov/HEAD", verbose=False
            )
            tracked_files = []
            if head_commit:
                tracked_files, _ = GitManager.get_files_by_commit(self.bare_repo_path, head_commit)

            if target_rel_path not in tracked_files:
                logging.warning(
                    f"{Color.RED}File {file_path} is not tracked, nothing to remove.{Color.RESET}"
                )
                return

            # If the file exists, remove it from the working directory
            if os.path.exists(target_abs_path):
                if (
                    input(f"Are you sure you want to remove {target_abs_path}? (y/N): ")
                    .strip()
                    .lower()
                    != "y"
                ):
                    LOGGER.info("File removal cancelled by user.")
                    return
                os.remove(target_abs_path)
                commit_msg = "Remove file\n\n"
            else:
                commit_msg = "Remove file (already missing)\n\n"

            commit_msg += f"Files: {target_rel_path}\n"
            commit_msg += (
                f"Prompt: {prompt}\nResponse: {response}\nSource: {'User' if by_user else 'AI'}"
            )

            # Commit the removal in the memov repo
            # Get current tracked files and exclude the removed file
            tracked_file_rel_paths, tracked_file_abs_paths = [], []
            if head_commit:
                tracked_file_rel_paths, tracked_file_abs_paths = GitManager.get_files_by_commit(
                    self.bare_repo_path, head_commit
                )

            # Build file list excluding the removed file
            file_list = {}
            for rel_path, abs_path in zip(tracked_file_rel_paths, tracked_file_abs_paths):
                if rel_path != target_rel_path and os.path.exists(abs_path):
                    file_list[rel_path] = abs_path

            self._commit(commit_msg, file_list)

            LOGGER.info(
                f"Removed file from working directory: {target_abs_path} and committed in memov repo."
            )
        except Exception as e:
            LOGGER.error(f"Error removing file from memov repo: {e}")

    def history(self) -> None:
        """Show the history of all branches in the memov bare repo, with table header and wider prompt/resp columns."""
        try:
            # Load branches from the memov repo
            branches = self._load_branches()
            if branches is None:
                LOGGER.error(
                    "No branches found in the memov repo. Please initialize or track files first."
                )
                return

            # Get the head commit of the memov repo and the branches' commit hashes
            head_commit = GitManager.get_commit_id_by_ref(
                self.bare_repo_path, "refs/memov/HEAD", verbose=False
            )
            commit_to_branch = defaultdict(list)
            for name, commit_hash in branches["branches"].items():
                commit_to_branch[commit_hash].append(name)

            # Print the header with new format including Operation column
            logging.info(
                f"{'Operation'.ljust(10)} {'Branch'.ljust(20)} {'Commit'.ljust(8)} {'Prompt'.ljust(15)} {'Resp'.ljust(15)}"
            )
            logging.info("-" * 70)

            # Get commit history for each branch and print the details
            seen = set()
            for commit_hash in branches["branches"].values():
                commit_history = GitManager.get_commit_history(self.bare_repo_path, commit_hash)

                for hash_id in commit_history:
                    if hash_id in seen:
                        continue
                    seen.add(hash_id)

                    # Get the commit message and extract operation type
                    message = GitManager.get_commit_message(self.bare_repo_path, hash_id)
                    operation_type = self._extract_operation_type(message)

                    # Get prompt and response from commit message first
                    prompt = response = ""
                    for line in message.splitlines():
                        if line.startswith("Prompt:"):
                            prompt = line[len("Prompt:") :].strip()
                        elif line.startswith("Response:"):
                            response = line[len("Response:") :].strip()

                    # Check if there's a git note for this commit (priority over commit message)
                    note_content = GitManager.get_commit_note(self.bare_repo_path, hash_id)
                    if note_content:
                        # Parse the note content for updated prompt/response
                        for line in note_content.splitlines():
                            if line.startswith("Prompt:"):
                                prompt = line[len("Prompt:") :].strip()
                            elif line.startswith("Response:"):
                                response = line[len("Response:") :].strip()

                    # Get the branch marker and format the output
                    marker = "*" if hash_id == head_commit else " "
                    branch_names = ",".join(commit_to_branch.get(hash_id, []))
                    branch_str = f"[{branch_names}]" if branch_names else ""
                    hash7 = hash_id[:7]

                    # Format prompt and response, handle None values
                    prompt_display = short_msg(prompt) if prompt and prompt != "None" else "None"
                    response_display = (
                        short_msg(response) if response and response != "None" else "None"
                    )

                    logging.info(
                        f"{operation_type.ljust(10)} {marker} {branch_str.ljust(18)} {hash7.ljust(8)} {prompt_display.ljust(15)} {response_display.ljust(15)}"
                    )
        except Exception as e:
            LOGGER.error(f"Error showing history in memov repo: {e}")

    def jump(self, commit_hash: str) -> None:
        """Jump to a specific snapshot in the memov repo (only move HEAD, do not change branches)."""
        try:
            # Get all files that have ever been tracked
            all_tracked_files = set()
            branches = self._load_branches()
            for branch_tip in branches["branches"].values():
                rev_list = GitManager.get_commit_history(self.bare_repo_path, branch_tip)
                for commit in rev_list:
                    _, file_abs_paths = GitManager.get_files_by_commit(self.bare_repo_path, commit)
                    all_tracked_files.update(file_abs_paths)

            # Remove files that are not in the snapshot
            snapshot_files, _ = GitManager.get_files_by_commit(self.bare_repo_path, commit_hash)
            for file_path in all_tracked_files:
                if file_path not in snapshot_files and os.path.exists(file_path):
                    os.remove(file_path)

            # Use archive to export the snapshot content to the workspace
            archive = GitManager.git_archive(self.bare_repo_path, commit_hash)
            if archive is None:
                LOGGER.error(f"Failed to create archive for commit {commit_hash}.")
                return

            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
                tar.extractall(self.project_path)

            # Update branch config
            self._update_branch(commit_hash, reset_current_branch=True)
            LOGGER.info(
                f"Jumped to commit {commit_hash} in memov repo (HEAD updated, branches unchanged)."
            )
        except Exception as e:
            LOGGER.error(f"Error jumping to commit in memov repo: {e}")

    def show(self, commit_id: str) -> None:
        """Show details of a specific snapshot in the memov bare repo, similar to git show."""
        try:
            GitManager.git_show(self.bare_repo_path, commit_id)

            tracked_file_rel_paths, _ = GitManager.get_files_by_commit(
                self.bare_repo_path, commit_id
            )
            LOGGER.info(f"\nTracked files in snapshot {commit_id}:")
            for rel_path in tracked_file_rel_paths:
                LOGGER.info(f"  {rel_path}")

        except Exception as e:
            LOGGER.error(f"Error showing snapshot {commit_id} in bare repo: {e}")

    def status(self) -> tuple[MemStatus, dict[str, list[Path]]]:
        """Show status of working directory compared to HEAD snapshot, and display current HEAD commit and branch."""
        try:
            # Get the current HEAD commit and branch
            head_commit = GitManager.get_commit_id_by_ref(
                self.bare_repo_path, "refs/memov/HEAD", verbose=False
            )
            if head_commit is None:
                head_commit = GitManager.get_commit_id_by_ref(
                    self.bare_repo_path, "main", verbose=False
                )

            branches = self._load_branches()
            current_branch = branches.get("current") if branches else None

            LOGGER.info(f"Current HEAD commit: {head_commit}")
            LOGGER.info(f"Current branch: {current_branch}")

            # Get the tracked files and worktree files
            tracked_files_and_blobs = GitManager.get_files_and_blobs_by_commit(
                self.bare_repo_path, head_commit, self.project_path
            )
            # Exclude files based on .memignore, but tracked files will still be shown if they exist
            workspace_files = self._filter_new_files(
                [self.project_path], tracked_file_rel_paths=None, exclude_memignore=True
            )
            worktree_files_and_blobs = {}
            for rel_path, abs_path in workspace_files:
                blob_hash = GitManager.write_blob(self.bare_repo_path, abs_path)
                worktree_files_and_blobs[Path(abs_path).resolve()] = blob_hash

            # Compare tracked files with workspace files
            all_files: set[Path] = set(
                list(tracked_files_and_blobs.keys()) + list(worktree_files_and_blobs.keys())
            )

            untracked_files = []
            deleted_files = []
            modified_files = []
            for f in sorted(all_files):
                if f not in tracked_files_and_blobs:
                    untracked_files.append(f)
                    LOGGER.info(f"{Color.RED}Untracked: {f}{Color.RESET}")
                elif f not in worktree_files_and_blobs:
                    deleted_files.append(f)
                    LOGGER.info(f"{Color.RED}Deleted:   {f}{Color.RESET}")
                elif tracked_files_and_blobs[f] != worktree_files_and_blobs[f]:
                    modified_files.append(f)
                    LOGGER.info(f"{Color.RED}Modified:  {f}{Color.RESET}")
                else:
                    LOGGER.info(f"{Color.GREEN}Clean:     {f}{Color.RESET}")

            return MemStatus.SUCCESS, {
                "untracked": untracked_files,
                "deleted": deleted_files,
                "modified": modified_files,
            }

        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            filename, lineno, func, code = tb[-1]  # last frame
            LOGGER.error(f"Error showing status: {code}, {e}")
            return MemStatus.UNKNOWN_ERROR, {}

    def amend_commit_message(
        self,
        commit_hash: str,
        prompt: Optional[str] = None,
        response: Optional[str] = None,
        by_user: bool = False,
    ) -> None:
        """
        Attach prompt/response to the commit as a git note (does not rewrite history).
        """
        try:
            # Compose the note content
            note_lines = []
            if prompt is not None:
                note_lines.append(f"Prompt: {prompt}")
            if response is not None:
                note_lines.append(f"Response: {response}")
            note_lines.append(f"Source: {'User' if by_user else 'AI'}")
            if not (prompt or response):
                LOGGER.error("No prompt or response provided to amend.")
                return
            note_msg = "\n".join(note_lines)
            # Attach the note using GitManager
            success, error_msg = GitManager.amend_commit_message(
                self.bare_repo_path, commit_hash, note_msg
            )
            if success:
                LOGGER.info(f"Added note to commit {commit_hash}.")
            else:
                LOGGER.error(f"Failed to add note to commit {commit_hash}: {error_msg}")
        except Exception as e:
            LOGGER.error(f"Error adding note to commit: {e}")

    def _commit(self, commit_msg: str, file_paths: dict[str, str]) -> str:
        """Commit changes to the memov repo with the given commit message and file paths."""
        try:
            # Validate and fix branches before committing
            self._validate_and_fix_branches()

            # Check the git user config(name and email)
            GitManager.ensure_git_user_config(
                self.bare_repo_path, self.default_name, self.default_email
            )

            # Write blob to bare repo and get commit hash
            commit_hash = GitManager.write_blob_to_bare_repo(
                self.bare_repo_path, file_paths, commit_msg
            )

            # Update the branch metadata with the new commit
            self._update_branch(commit_hash)
            LOGGER.debug(f"Committed changes in memov repo: {commit_msg}")
            return commit_hash
        except Exception as e:
            LOGGER.error(f"Error committing changes in memov repo: {e}")
            return ""

    def _filter_new_files(
        self,
        file_paths: list[str],
        tracked_file_rel_paths: Optional[list[str]] = None,
        exclude_memignore: bool = True,
    ) -> list[tuple[str, str]]:
        """Filter out files that are already tracked or should be ignored.

        Args:
            file_paths (list[str]): The list of file paths to check.
            tracked_file_rel_paths (list[str] | None): The list of tracked file paths. If None, all files are considered new.
            exclude_memignore (bool): Whether to exclude files that match .memignore rules.
        """
        memignore_pspec = self._load_memignore()

        def filter(file_rel_path: str) -> bool:
            """Check if the file should be ignored"""

            # Never filter out .memignore itself
            if file_rel_path == ".memignore":
                return False

            # Filter out files that match .memignore rules
            if exclude_memignore and memignore_pspec.match_file(file_rel_path):
                return True

            # Filter out files that are already tracked if tracked_file_rel_paths is provided
            if tracked_file_rel_paths is not None and file_rel_path in tracked_file_rel_paths:
                return True

            return False

        new_files = []
        for file_path in file_paths:
            abs_path = os.path.abspath(file_path)

            # Check if the file path is valid
            if not os.path.exists(abs_path):
                LOGGER.error(f"File {abs_path} does not exist.")
                continue

            # If the file is a directory, walk through it
            if os.path.isdir(abs_path):
                for root, dirs, files in os.walk(abs_path):
                    rel_root = os.path.relpath(root, self.project_path)

                    # Don't filter the current directory itself
                    if (
                        rel_root != "."
                        and exclude_memignore
                        and memignore_pspec.match_file(rel_root)
                    ):
                        continue

                    if ".mem" in dirs:
                        dirs.remove(".mem")
                    if ".git" in dirs:
                        dirs.remove(".git")

                    for file in files:
                        rel_file = os.path.relpath(os.path.join(root, file), self.project_path)
                        if filter(rel_file):
                            continue

                        new_files.append((rel_file, os.path.join(root, file)))

            # If the file is a regular file, check if it should be tracked
            elif os.path.isfile(abs_path):
                rel_file = os.path.relpath(abs_path, self.project_path)
                if filter(rel_file):
                    continue

                new_files.append((rel_file, abs_path))

            # If the path is neither a file nor a directory, log an error
            else:
                LOGGER.error(f"Path {abs_path} is neither a file nor a directory.")
                return []

        return new_files

    def _load_branches(self) -> Optional[dict]:
        """Load branches configuration from the branches config file."""
        if not os.path.exists(self.branches_config_path):
            return None

        with open(self.branches_config_path, "r") as f:
            return json.load(f)

    def _save_branches(self, data) -> None:
        """Save branches configuration to the branches config file."""
        with open(self.branches_config_path, "w") as f:
            json.dump(data, f, indent=2)

    def _next_develop_branch(self, branches: dict[str, str]) -> str:
        """Find the next available develop branch name based on existing branches."""
        i = 0
        while f"develop/{i}" in branches:
            i += 1
        return f"develop/{i}"

    def _load_memignore(self) -> pathspec.PathSpec:
        """Load .memignore rules and return a pathspec.PathSpec object"""
        patterns = []
        if os.path.exists(self.memignore_path):
            with open(self.memignore_path, "r") as f:
                patterns = [
                    line.strip() for line in f if line.strip() and not line.strip().startswith("#")
                ]
        # Exclude .mem and .git directories by default
        patterns.append(".mem/")
        patterns.append(".git/")
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)

    def _validate_and_fix_branches(self) -> None:
        """Validate and fix abnormal states in branches.json"""
        branches = self._load_branches()
        if not branches:
            return

        head_commit = GitManager.get_commit_id_by_ref(
            self.bare_repo_path, "refs/memov/HEAD", verbose=False
        )

        fixed = False

        # Fix empty branch commit hashes
        for name, commit_hash in branches["branches"].items():
            if not commit_hash:  # Empty string or None
                if name == "main" and head_commit:
                    branches["branches"][name] = head_commit
                    LOGGER.info(f"Fixed empty {name} branch with current HEAD {head_commit}")
                    fixed = True

        # Ensure current points to a valid branch
        current = branches.get("current")
        if current and current not in branches["branches"]:
            branches["current"] = "main"  # Default back to main
            LOGGER.warning(f"Fixed invalid current branch, reset to main")
            fixed = True

        if fixed:
            self._save_branches(branches)

    def _update_branch(self, new_commit: str, reset_current_branch: bool = False) -> None:
        """Automatically create or update a branch in the memov repo based on the new commit."""
        branches = self._load_branches()

        # First commit to create the default branch if it doesn't exist
        if branches is None:
            branches = {"current": "main", "branches": {"main": new_commit}}
            self._save_branches(branches)
            GitManager.update_ref(self.bare_repo_path, "refs/memov/HEAD", new_commit)
            return

        # If reset_current_branch is True, save current branch and reset
        if reset_current_branch:
            current_branch = branches.get("current")
            if current_branch and current_branch in branches["branches"]:
                head_commit = GitManager.get_commit_id_by_ref(
                    self.bare_repo_path, "refs/memov/HEAD", verbose=False
                )
                if head_commit:
                    branches["branches"][current_branch] = head_commit
            branches["current"] = None
        else:
            head_commit = GitManager.get_commit_id_by_ref(
                self.bare_repo_path, "refs/memov/HEAD", verbose=False
            )

            # Prioritize using current branch
            current_branch = branches.get("current")
            if current_branch and current_branch in branches["branches"]:
                # If current branch exists, update it directly
                branches["branches"][current_branch] = new_commit
                LOGGER.debug(f"Updated current branch {current_branch} to {new_commit}")
            else:
                # If no current branch, try to find matching branch
                updated = False
                for name, commit_hash in branches["branches"].items():
                    if head_commit == commit_hash:
                        branches["branches"][name] = new_commit
                        branches["current"] = name
                        updated = True
                        LOGGER.debug(f"Found matching branch {name}, updated to {new_commit}")
                        break

                # Only create new branch when no match is found
                if not updated:
                    # Check if it's main branch case (empty or invalid commit hash)
                    if "main" in branches["branches"] and not branches["branches"]["main"]:
                        branches["branches"]["main"] = new_commit
                        branches["current"] = "main"
                        LOGGER.debug(f"Fixed empty main branch, set to {new_commit}")
                    else:
                        new_branch = self._next_develop_branch(branches["branches"])
                        branches["branches"][new_branch] = new_commit
                        branches["current"] = new_branch
                        LOGGER.warning(f"Created new branch {new_branch} for commit {new_commit}")

        # Update the branches config file and the HEAD reference
        self._save_branches(branches)
        GitManager.update_ref(self.bare_repo_path, "refs/memov/HEAD", new_commit)

    def _extract_operation_type(self, commit_message: str) -> str:
        """Extract operation type from commit message first line."""
        if not commit_message:
            return "unknown"

        first_line = commit_message.splitlines()[0].lower()

        if "track" in first_line:
            return "track"
        elif "snapshot" in first_line or "snap" in first_line:
            return "snap"
        elif "rename" in first_line:
            return "rename"
        elif "remove" in first_line:
            return "remove"
        else:
            return "unknown"
