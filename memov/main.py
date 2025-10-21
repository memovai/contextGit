import logging
import os
import sys
from typing import List, Optional

import typer
from typing_extensions import Annotated

from memov.core.manager import MemovManager, MemStatus
from memov.utils.logging_utils import setup_logging

# Common type aliases
LocOption = Annotated[
    str,
    typer.Option("--loc", help="Specify the project directory path (default: current directory)"),
]
PromptOption = Annotated[
    Optional[str],
    typer.Option(
        "-p", "--prompt", help="Descriptive prompt explaining the purpose of this operation"
    ),
]
ResponseOption = Annotated[
    Optional[str],
    typer.Option(
        "-r", "--response", help="AI or user response to the prompt (optional documentation)"
    ),
]
ByUserOption = Annotated[
    bool,
    typer.Option(
        "-u", "--by_user", help="Mark this operation as performed by a human user (vs AI)"
    ),
]


# Create Typer app
app = typer.Typer(
    name="memov",
    help="memov - AI-assisted version control on top of Git. Track, snapshot, and manage your project evolution.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    add_completion=False,  # Disable shell completion for now
)


def get_manager(loc: str, skip_mem_check: bool = False) -> MemovManager:
    """Get MemovManager instance, and config the logging."""
    # Configure logging
    setup_logging(loc)

    # Validate and return MemovManager instance
    loc = os.path.abspath(loc)
    manager = MemovManager(project_path=loc)

    status = manager.check(only_basic_check=skip_mem_check)
    if status is not MemStatus.SUCCESS:
        sys.exit(1)

    return manager


@app.command()
def init(loc: LocOption = ".") -> None:
    """Initialize memov repository in the specified location."""
    manager = get_manager(loc, skip_mem_check=True)
    manager.init()


@app.command()
def track(
    loc: LocOption = ".",
    file_paths: Annotated[
        Optional[List[str]], typer.Argument(help="List of file paths to track")
    ] = None,
    prompt: PromptOption = None,
    response: ResponseOption = None,
    by_user: ByUserOption = False,
) -> None:
    """Track files in the project directory for version control."""
    manager = get_manager(loc)
    manager.track(file_paths, prompt, response, by_user)


@app.command()
def snap(
    files: Annotated[
        Optional[List[str]],
        typer.Option(
            "--files",
            help="Specific files to snapshot (comma-separated or multiple --files flags). If not specified, snapshots all tracked files.",
        ),
    ] = None,
    loc: LocOption = ".",
    prompt: PromptOption = None,
    response: ResponseOption = None,
    by_user: ByUserOption = False,
) -> None:
    """Create a snapshot of the current project state."""
    manager = get_manager(loc)
    manager.snapshot(file_paths=files, prompt=prompt, response=response, by_user=by_user)


@app.command()
def rename(
    old_path: Annotated[str, typer.Argument(help="Current path of the file to rename")],
    new_path: Annotated[str, typer.Argument(help="New path for the file")],
    loc: LocOption = ".",
    prompt: PromptOption = None,
    response: ResponseOption = None,
    by_user: ByUserOption = False,
) -> None:
    """Rename a tracked file and record the operation."""
    manager = get_manager(loc)
    manager.rename(old_path, new_path, prompt, response, by_user)


@app.command()
def remove(
    file_path: Annotated[str, typer.Argument(help="Path of the file to remove from tracking")],
    loc: LocOption = ".",
    prompt: PromptOption = None,
    response: ResponseOption = None,
    by_user: ByUserOption = False,
) -> None:
    """Remove a tracked file from the project and record the operation."""
    manager = get_manager(loc)
    manager.remove(file_path, prompt, response, by_user)


@app.command()
def history(loc: LocOption = ".") -> None:
    """Show history of snapshots and operations."""
    manager = get_manager(loc)
    manager.history()


@app.command()
def show(
    snapshot_id: Annotated[str, typer.Argument(help="ID/hash of the snapshot to display")],
    loc: LocOption = ".",
) -> None:
    """Show detailed information about a specific snapshot."""
    manager = get_manager(loc)
    manager.show(snapshot_id)


@app.command()
def jump(
    snapshot_id: Annotated[str, typer.Argument(help="ID/hash of the snapshot to jump to")],
    loc: LocOption = ".",
) -> None:
    """Jump to a specific snapshot, restoring the project state."""
    manager = get_manager(loc)
    manager.jump(snapshot_id)


@app.command()
def status(loc: LocOption = ".") -> None:
    """Show status of working directory compared to the latest snapshot."""
    manager = get_manager(loc)
    manager.status()


@app.command()
def amend(
    commit_hash: Annotated[str, typer.Argument(help="Commit hash to add notes to")],
    loc: LocOption = ".",
    prompt: PromptOption = None,
    response: ResponseOption = None,
    by_user: ByUserOption = False,
) -> None:
    """Add or update prompt/response notes for a specific commit."""
    manager = get_manager(loc)
    manager.amend_commit_message(commit_hash, prompt, response, by_user)


@app.command()
def version() -> None:
    """Show version information."""
    manager = get_manager(loc=".", skip_mem_check=True)
    manager.version()


def main() -> None:
    """Main entry point for the memov command line interface."""
    try:
        app()
    except KeyboardInterrupt:
        logging.info("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        logging.debug("Full traceback:", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
