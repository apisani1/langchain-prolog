"""Version management script."""
import logging
import re
import subprocess
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ReleaseType(Enum):
    """Types of releases."""
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
    if not match:
        logger.error("Could not find version in pyproject.toml")
        raise ValueError("Version not found in pyproject.toml")
    return match.group(1)

def bump_version(
    release_type: ReleaseType,
    pre_release: Optional[str] = None
) -> str:
    """Bump version according to semver."""
    current = get_current_version()
    logger.debug(f"Current version: {current}")

    # Parse current version
    match = re.match(r"(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z]+)\.(\d+))?", current)
    if not match:
        logger.error(f"Invalid version format: {current}")
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

    logger.debug(f"New version: {version}")
    return version

def update_files(new_version: str) -> None:
    """Update version in all project files."""
    logger.info(f"Updating files with new version: {new_version}")

    # Update pyproject.toml
    pyproject = Path("pyproject.toml")
    content = pyproject.read_text()
    content = re.sub(
        r'version = "[^"]+"',
        f'version = "{new_version}"',
        content
    )
    pyproject.write_text(content)
    logger.debug("Updated pyproject.toml")

    # Update docs/conf.py
    conf = Path("docs/conf.py")
    if conf.exists():
        content = conf.read_text()
        content = re.sub(
            r'release = "[^"]+"',
            f'release = "{new_version}"',
            content
        )
        conf.write_text(content)
        logger.debug("Updated docs/conf.py")

def create_release(
    release_type: ReleaseType,
    changes: list[str],
    pre_release: Optional[str] = None,
) -> None:
    """Create a new release.

    Args:
        release_type: Type of release (major, minor, patch)
        changes: List of changes for the changelog
        pre_release: Optional pre-release identifier (alpha, beta, rc)

    Raises:
        ValueError: If working directory is not clean
        RuntimeError: If any git command fails
    """
    try:
        # Ensure working directory is clean
        logger.info("Checking working directory status...")
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout.strip():
            logger.error("Working directory is not clean")
            raise ValueError(
                "Working directory is not clean. Please commit or stash changes first."
            )

        # Get new version
        new_version = bump_version(release_type, pre_release)
        logger.info(f"Creating new version: {new_version}")

        # Update files
        update_files(new_version)

        # Create changelog entry
        date = datetime.now().strftime("%Y-%m-%d")

        # Determine change type and scope
        if release_type == ReleaseType.MAJOR:
            change_type = "feat"
            scope = "breaking"
        elif release_type == ReleaseType.MINOR:
            change_type = "feat"
            scope = "minor"
        else:
            change_type = "fix"
            scope = "patch"

        # Create commit message in conventional format
        commit_msg = []

        # Add header
        if pre_release:
            commit_msg.append(f"{change_type}({scope})!: pre-release {new_version}")
        else:
            commit_msg.append(f"{change_type}({scope}): release version {new_version}")

        # Add blank line
        commit_msg.append("")

        # Add description
        commit_msg.append(f"Release {new_version} - {date}")
        commit_msg.append("")

        # Add changes
        commit_msg.append("Changes:")
        for change in changes:
            commit_msg.append(f"* {change}")

        # Add footer
        commit_msg.append("")
        if pre_release:
            commit_msg.append(f"Pre-release: {pre_release}")
        commit_msg.append(f"Release-Date: {date}")

        # Join message parts
        commit_message = "\n".join(commit_msg)

        # Stage changes
        logger.info("Staging changes...")
        subprocess.run(["git", "add", "."], check=True)

        # Commit changes
        logger.info("Committing changes...")
        subprocess.run(
            ["git", "commit", "-m", commit_message],
            check=True
        )

        # Create tag
        tag = f"v{new_version}"
        logger.info(f"Creating tag: {tag}")

        # Create annotated tag with release notes
        tag_message = [
            f"Release {new_version}",
            "",
            "Changes:",
            *[f"* {change}" for change in changes]
        ]
        if pre_release:
            tag_message.append("")
            tag_message.append(f"Pre-release: {pre_release}")

        subprocess.run(
            ["git", "tag", "-a", tag, "-m", "\n".join(tag_message)],
            check=True
        )

        # Update CHANGELOG.md
        logger.info("Updating CHANGELOG.md...")
        changelog = Path("CHANGELOG.md")
        if changelog.exists():
            current_content = changelog.read_text()
            # Find the position after the first heading
            if "\n## " in current_content:
                header, rest = current_content.split("\n## ", 1)
                new_content = (
                    f"{header}\n"
                    f"## [{new_version}] - {date}\n\n"
                    "### Changes\n"
                    f"{chr(10).join(f'* {change}' for change in changes)}\n\n"
                    f"## {rest}"
                )
            else:
                new_content = (
                    f"{current_content}\n\n"
                    f"## [{new_version}] - {date}\n\n"
                    "### Changes\n"
                    f"{chr(10).join(f'* {change}' for change in changes)}\n"
                )
        else:
            new_content = (
                "# Changelog\n\n"
                f"## [{new_version}] - {date}\n\n"
                "### Changes\n"
                f"{chr(10).join(f'* {change}' for change in changes)}\n"
            )

        changelog.write_text(new_content)

        # Print success message
        logger.info(f"Successfully created release {new_version}")
        logger.info("To complete the release:")
        logger.info("1. Review the changes")
        logger.info("2. Run: git push && git push --tags")

    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {e}")
        rollback()
        raise RuntimeError(f"Failed to create release: {e}")
    except Exception as e:
        logger.error(f"Error creating release: {e}")
        rollback()
        raise

def rollback() -> None:
    """Rollback changes if something goes wrong."""
    logger.info("Rolling back changes...")

    try:
        # Reset to last commit
        subprocess.run(["git", "reset", "--hard", "HEAD"], check=True)
        logger.debug("Reset to HEAD")

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
            logger.debug(f"Deleted tag: {last_tag}")

        logger.info("Rollback complete")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error during rollback: {e}")
        logger.error("Manual intervention may be required")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage releases")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Create release command
    release_parser = subparsers.add_parser('create', help='Create a new release')
    release_parser.add_argument(
        "type",
        choices=[t.value for t in ReleaseType],
        help="Type of release"
    )
    release_parser.add_argument(
        "--pre-release",
        choices=["alpha", "beta", "rc"],
        help="Create a pre-release"
    )
    release_parser.add_argument(
        "--changes",
        nargs="+",
        required=True,
        help="List of changes for changelog"
    )

    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback last release')

    # Debug option for both commands
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)

    if args.command == 'create':
        create_release(
            ReleaseType(args.type),
            args.changes,
            args.pre_release
        )
    elif args.command == 'rollback':
        rollback()
    else:
        parser.print_help()
