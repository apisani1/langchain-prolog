#!/usr/bin/env python3
import re
import sys
from pathlib import Path


try:
    import tomllib  # Part of the standard library on Python 3.11+
except ImportError:
    import tomli as tomllib  # For Python < 3.11


def update_files(new_version: str, dry_run: bool = False) -> None:
    """Update version variables in specified files based on pyproject.toml configuration."""

    def replace_version(match: re.Match) -> str:
        """Preserve the original format while updating the version."""
        key = match.group(1)  # version_key
        space1 = match.group(2)  # whitespace before separator
        separator = match.group(3)  # : or =
        space2 = match.group(4)  # whitespace after separator
        open_quote = match.group(5)  # opening quote (", ', or empty)
        close_quote = match.group(7)  # closing quote (", ', or empty)

        return f"{key}{space1}{separator}{space2}{open_quote}{new_version}{close_quote}"

    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        print("Error: pyproject.toml not found.")
        sys.exit(1)

    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    try:
        version_variables = data["tool"]["semantic_release"]["version_variable"]
    except KeyError:
        print("Error: [tool.semantic_release].version_variable not found.")
        sys.exit(1)

    for entry in version_variables:
        file_path, var_name = entry.split(":")
        path = Path(file_path)
        if not path.exists():
            print(f"Warning: {file_path} not found, skipping.")
            continue

        content = path.read_text()
        pattern = rf'({re.escape(var_name)})(\s*)([:=])(\s*)(["\']?)([^"\'<>\s\n]+)(["\']?)'
        new_content, found = re.subn(pattern, replace_version, content, count=1)
        if not found:
            print(f"Warning: Pattern for {var_name} not found in {file_path}, skipping.")
            continue

        if dry_run:
            new_line = replace_version(re.search(pattern, new_content))  # type: ignore
            print(f"DRYRUN: {file_path} would be updated to {new_line}")
        else:
            path.write_text(new_content)
            print(f"UPDATED: {file_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: update_versions.py <version> [--dry-run]")
        sys.exit(1)

    version = sys.argv[1]
    dry = "--dry-run" in sys.argv
    update_files(version, dry)
