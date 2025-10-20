def short_msg(val: str) -> str:
    """Shorten the message to 15 characters, adding '...' if longer."""
    if not isinstance(val, str):
        raise TypeError(f"Expected str, got {type(val)}")

    if not val:
        return ""
    return val[:15] + ("..." if len(val) > 15 else "")


def clean_windows_git_lstree_output(output: str) -> str:
    """Clean up git ls-tree output for Windows compatibility."""
    if not isinstance(output, str):
        raise TypeError(f"Expected str, got {type(output)}")

    return output.strip('"').split("\\r")[0]  # Clean up the file path
