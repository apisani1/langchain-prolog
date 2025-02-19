"""Version management script."""
import re
import subprocess
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

class ReleaseType(Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    ALPHA = "alpha"
    BETA = "beta"
    RC = "rc"

def get_current_version() -> str:
    """Get current version from pyproject.toml."""
    pyproject = Path("pyproject.toml")
    content = pyproject.read_text()
    match = re.search(r'version = "([^"]+)"', content)
    return match.group(1) if match else "0.0.0"

def bump_version(
    release_type: ReleaseType,
    pre_release: Optional[str] = None
) -> str:
    """Bump version according to semver."""
    current = get_current_version()

    # Parse current version
    match = re.match(r"(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z]+)\.(\d+))?", current)
    if not match:
        raise ValueError(f"Invalid version format: {current}")

    major, minor, patch = map(int, match.groups()[:3])

    # Handle version bump
    if release_type == ReleaseType.MAJOR:
        major += 1
        minor = patch = 0
    elif release_type == ReleaseType.MINOR:
        minor += 1
        patch = 0
    elif release_type == ReleaseType.PATCH:
        patch += 1

    # Build new version
    version = f"{major}.{minor}.{patch}"

    # Add pre-release if specified
    if pre_release:
        version = f"{version}-{pre_release}.1"

    return version

def update_files(new_version: str) -> None:
    """Update version in all project files."""
    # Update pyproject.toml
    pyproject = Path("pyproject.toml")
    content = pyproject.read_text()
    content = re.sub(
        r'version = "[^"]+"',
        f'version = "{new_version}"',
        content
    )
    pyproject.write_text(content)

    # Update docs/conf.py
    conf = Path("docs/conf.py")
    content = conf.read_text()
    content = re.sub(
        r'release = "[^"]+"',
        f'release = "{new_version}"',
        content
    )
    conf.write_text(content)

def create_changelog_entry(version: str, changes: list[str]) -> None:
    """Create or update CHANGELOG.md."""
    changelog = Path("CHANGELOG.md")
    date = datetime.now().strftime("%Y-%m-%d")

    new_entry = f"\n## [{version}] - {date}\n"
    for change in changes:
        new_entry += f"- {change}\n"

    if changelog.exists():
        content = changelog.read_text()
        # Insert after first heading
        parts = content.split("\n## ", 1)
        content = parts[0] + new_entry + "\n## " + parts[1]
    else:
        content = "# Changelog\n" + new_entry

    changelog.write_text(content)

def create_release(
    release_type: ReleaseType,
    changes: list[str],
    pre_release: Optional[str] = None,
) -> None:
    """Create a new release."""
    try:
        # Ensure working directory is clean
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            raise ValueError("Working directory is not clean")

        # Get new version
        new_version = bump_version(release_type, pre_release)

        # Update files
        update_files(new_version)
        create_changelog_entry(new_version, changes)

        # Commit changes
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(
            ["git", "commit", "-m", f"chore: bump version to {new_version}"],
            check=True
        )

        # Create tag
        tag = f"v{new_version}"
        subprocess.run(["git", "tag", "-a", tag, "-m", f"Release {tag}"], check=True)

        print(f"Created release {new_version}")
        print("Run 'git push && git push --tags' to trigger release workflow")

    except Exception as e:
        print(f"Error creating release: {e}")
        rollback()

def rollback() -> None:
    """Rollback changes if something goes wrong."""
    print("Rolling back changes...")

    # Reset to last commit
    subprocess.run(["git", "reset", "--hard", "HEAD"], check=True)

    # Get last tag
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        last_tag = result.stdout.strip()
        # Delete tag if it was just created
        subprocess.run(["git", "tag", "-d", last_tag], check=True)

    print("Rollback complete")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage releases")
    parser.add_argument(
        "type",
        choices=[t.value for t in ReleaseType],
        help="Type of release"
    )
    parser.add_argument(
        "--pre-release",
        choices=["alpha", "beta", "rc"],
        help="Create a pre-release"
    )
    parser.add_argument(
        "--changes",
        nargs="+",
        required=True,
        help="List of changes for changelog"
    )

    args = parser.parse_args()
    create_release(
        ReleaseType(args.type),
        args.changes,
        args.pre_release
    )
