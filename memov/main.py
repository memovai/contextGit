import logging
import os
import sys
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from memov.core.manager import MemovManager, MemStatus
from memov.utils.logging_utils import setup_logging

console = Console()

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


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search query (prompt text or file path)")],
    loc: LocOption = ".",
    by_files: Annotated[
        bool,
        typer.Option(
            "--by-files",
            "-f",
            help="Search by file paths instead of prompt text",
        ),
    ] = False,
    operation_type: Annotated[
        Optional[str],
        typer.Option(
            "--type",
            "-t",
            help="Filter by operation type: track, snap, rename, remove",
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-n",
            help="Maximum number of results to return",
        ),
    ] = 10,
    show_distance: Annotated[
        bool,
        typer.Option(
            "--show-distance/--no-distance",
            "-d/-D",
            help="Show similarity distance scores (default: enabled for semantic search)",
        ),
    ] = True,
) -> None:
    """Search for commits using semantic search on prompts or file paths.

    Examples:
        # Search by prompt
        mem search "authentication bug fix"

        # Search by file paths
        mem search "src/auth.py" --by-files

        # Filter by operation type
        mem search "refactor" --type snap

        # Limit results and show distances
        mem search "database" --limit 5 --show-distance
    """
    manager = get_manager(loc)

    try:
        if by_files:
            # Search by file paths
            file_paths = [p.strip() for p in query.split(",")]
            results = manager.find_commits_by_files(file_paths)

            if not results:
                console.print(
                    f"[yellow]No commits found for files: {', '.join(file_paths)}[/yellow]"
                )
                return

            # Limit results
            results = results[:limit]
        else:
            # Search by prompt (semantic search)
            results = manager.find_similar_prompts(
                query_prompt=query, n_results=limit, operation_type=operation_type
            )

            if not results:
                console.print(f"[yellow]No similar prompts found for: {query}[/yellow]")
                return

        # Create rich table
        table = Table(title=f"Search Results for: {query}", show_header=True, header_style="bold")

        # Add columns
        table.add_column("Commit", style="cyan", no_wrap=True, width=8)
        table.add_column("Type", style="magenta", width=8)
        table.add_column("Source", style="blue", width=6)
        if show_distance and not by_files:
            table.add_column("Distance", style="yellow", width=8)
        table.add_column("Files", style="green", width=30)
        table.add_column("Text Preview", style="white", width=50)

        # Add rows
        for result in results:
            metadata = result.get("metadata", {})
            commit_hash = metadata.get("commit_hash", "unknown")[:8]
            op_type = metadata.get("operation_type", "unknown")
            source = metadata.get("source", "unknown")
            files = metadata.get("files", [])

            # Format files (stored as comma-separated string)
            if isinstance(files, str):
                # Files are stored as comma-separated string
                file_list = [f.strip() for f in files.split(",") if f.strip()]
                if len(file_list) > 2:
                    files_str = ", ".join(file_list[:2]) + f" (+{len(file_list) - 2} more)"
                else:
                    files_str = ", ".join(file_list) if file_list else "No files"
            elif isinstance(files, list):
                # Fallback for backwards compatibility
                files_str = ", ".join(files[:2])
                if len(files) > 2:
                    files_str += f" (+{len(files) - 2} more)"
            else:
                files_str = str(files)

            # Get text preview
            text = result.get("text", "")
            if len(text) > 50:
                text_preview = text[:47] + "..."
            else:
                text_preview = text

            # Build row
            row = [commit_hash, op_type, source]

            if show_distance and not by_files:
                distance = result.get("distance", 0.0)
                similarity = (1 - distance) * 100
                row.append(f"{similarity:.1f}%")

            row.extend([files_str, text_preview])
            table.add_row(*row)

        # Print table
        console.print()
        console.print(table)
        console.print()

        # Print statistics
        info = manager.get_vectordb_info()
        console.print(
            f"[dim]Searched {info.get('count', 0)} chunks in collection '{info.get('name', 'unknown')}'[/dim]"
        )

    except Exception as e:
        console.print(f"[red]Error during search: {e}[/red]")
        logging.error(f"Search error: {e}", exc_info=True)
        sys.exit(1)


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
