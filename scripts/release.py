"""Release management script."""

import logging
import os
import pickle
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from enum import Enum
from itertools import chain
from pathlib import Path
from typing import (
    Iterator,
    Optional,
    Tuple,
)

from packaging.version import (
    InvalidVersion,
    Version,
)


logging.basicConfig(
    level=logging.CRITICAL,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class ReleaseType(Enum):
    """Types of releases following PEP 440."""

    MAJOR = "major"
    MINOR = "minor"
    MICRO = "micro"
    PRE = "pre"
    DEV = "dev"
    POST = "post"


StableRelease = {
    ReleaseType.MAJOR,
    ReleaseType.MINOR,
    ReleaseType.MICRO,
}


class PrereleaseType(Enum):
    """Types of prereleases following PEP 440."""

    ALPHA = "a"
    BETA = "b"
    RC = "rc"


PROJECT_FILE = "pyproject.toml"
CHANGELOG_FILE = "CHANGELOG.md"
BEFORE_LAST_RELEASE = ".before_last_release.pkl"

files_backup: Optional[Iterator[Tuple[str, str]]] = None


def create_release(
    release_type: ReleaseType,
    prerelease_type: Optional[PrereleaseType] = None,
    changes_message: Optional[str] = None,
    project_file: str = PROJECT_FILE,
    changelog_file: str = CHANGELOG_FILE,
) -> Version:
    """
    Create a new release, bumping version acording to release and pre-release type and updating project files
    containing the release version number and the changelog file. Creates a git commit and tag for the release.

    Args:
        release_type: Type of release using PEP 440 release types.
        prerelease_type: Optional pre-release type using PEP 440 prerelease types.
        changes_message: Optional string with descriptions of changes since last release for the changelog file
            If no message is provided, will use git commit messages since last release.
        project_file: Path to the project TOML file. Default: pyproject.toml.
        changelog_file: Path to the changelog markdown file. Default: CHANGELOG.md.

    Returns:
        The release version number as a packaging.version.Version object.

    Raises:
        FileNotFoundError: If the project TOML file does not exist.
        ValueError: If the release fails due to invalid input, state or no new commits since last release.
        RuntimeError: If a git or shell command fails.
        ImportError: If tomllib or tomli is not available for reading TOML files.
    """
    time_stamp = datetime.now().astimezone()
    try:
        # Ensure working directory is a git repository and is clean
        logger.info("Checking working directory git status...")
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
        if result.stdout.strip():
            logger.error("Not a git repository or working directory is not clean.")
            raise ValueError("Not a git repository or working directory is not clean.")

        # Verify that there are changes since the last release
        latest_tag = get_latest_release_tag()
        commit_messages = get_commits_since_tag(latest_tag)
        if not commit_messages:
            logger.error("No new commits since last release.")
            raise ValueError("No new commits since last release.")
        if not changes_message:
            changes_message = "\n".join(f"- {msg}" for msg in commit_messages)

        date = time_stamp.strftime("%Y-%m-%d")
        current_version = get_current_version(project_file)
        new_version = bump_version(current_version, release_type, prerelease_type)
        update_version_files(project_file, new_version)
        changelog_entry = update_changelog(changelog_file, date, new_version, changes_message)
        commit_message = create_commit(new_version, changelog_entry, release_type, prerelease_type)  # type: ignore
        create_tag(date, new_version, commit_message)
        save_state(time_stamp, current_version)

        return new_version

    except subprocess.CalledProcessError as e:
        logger.error(f"Git or shell command failed ({e}). Rolling back changes.")
        rollback(time_stamp)
        raise RuntimeError(f"Git or shell command failed: {e}")
    except Exception as e:
        logger.error(f"Failed to create release. Rolling back changes.")
        rollback(time_stamp)
        raise


def get_latest_release_tag() -> Optional[str]:
    """Find the latest release tag matching 'v<PyPI version>'."""
    tags = subprocess.check_output(["git", "tag"], text=True).splitlines()
    # Filter only version tags
    valid_tags = [tag for tag in tags if re.match(r"^v\d+\.\d+\.\d+([-.](?:a|b|rc|dev|post)\d*)?$", tag)]
    if not valid_tags:
        return None
    # Sort tags by version number (PEP 440 compliant sorting)
    valid_tags.sort(key=lambda tag: Version(tag[1:]), reverse=True)
    return valid_tags[0]


def get_commits_since_tag(tag: Optional[str]) -> list[str]:
    """Retrieve commit messages since the given tag."""
    range = f"{tag}..HEAD" if tag else "HEAD"
    commit_messages = subprocess.check_output(["git", "log", f"{range}", "--pretty=format:%s"], text=True).splitlines()
    return commit_messages


def get_current_version(project_file: str) -> Version:
    """Get current version from project file"""
    version_text = read_from_toml_file(project_file, "poetry", "version")
    if not version_text:
        logger.error(f"Could not find version in '{project_file}'. Please check the file format.")
        raise ValueError(f"Version not found in '{project_file}'. Please check the file format.")
    try:
        version = Version(version_text)
        logger.info(f"Current version found in '{project_file}': '{version}'")
        return version
    except InvalidVersion as e:
        logger.error(f"Invalid version found in '{project_file}': '{version_text}'")
        raise ValueError(f"Invalid version format in '{project_file}': '{version_text}'")


def read_from_toml_file(file_path: str, section: str, key: str) -> Optional[str]:
    """Reads a toml file to get the contents of a specific tool section and key."""
    try:
        import tomllib  # Part of the standard library on Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # For Python < 3.11
        except ImportError:
            logger.error("Neither tomllib nor tomli is available. Please install tomli package.")
            raise ImportError("Please install tomli package: pip install tomli")

    toml_file = Path(file_path)
    if not toml_file.exists():
        logger.error(f"'{file_path}' does not exist.")
        raise FileNotFoundError(f"'{file_path}' does not exist.")
    try:
        with open(toml_file, "rb") as f:
            toml_data = tomllib.load(f)
        value = toml_data.get("tool").get(section, {}).get(key)
        if not value:
            logger.warning(f"'{key}' field of section 'tool.{section}' not found in '{file_path}'.")
        return value
    except Exception as e:
        logger.error(f"Error reading '{key}' field of section 'tool.{section}' from {file_path}: {e}")
        raise


def bump_version(
    current_version: Version,
    release_type: ReleaseType,
    prerelease_type: Optional[PrereleaseType] = None,
) -> Version:
    """
    Bump a version according to semantic versioning rules.

    Args:
        current_version: The current version following PEP 440.
        release_type: The type of release to bump to.
        prerelease_type: The type of prerelease if applicable.

    Returns:
        The new version as a packaging.version.Version object.

    Raises:
        ValueError: If the bump is not valid or the arguments are incorrect.
    """
    try:
        major = current_version.release[0] if len(current_version.release) > 0 else 0
        minor = current_version.release[1] if len(current_version.release) > 1 else 0
        micro = current_version.release[2] if len(current_version.release) > 2 else 0

        # Used when specifying a release segment for a pre-release
        # For example, python release.py create major --pre rc
        prerelease_segment = f"{prerelease_type.value}1" if prerelease_type else ""

        if release_type in StableRelease and current_version.pre is not None:
            # To release a stable version from a pre-release just drop the pre-release segment
            # and ignore the release type requested
            new_version = f"{major}.{minor}.{micro}"
        elif release_type == ReleaseType.MAJOR:
            new_version = f"{major + 1}.0.0{prerelease_segment}"
        elif release_type == ReleaseType.MINOR:
            new_version = f"{major}.{minor + 1}.0{prerelease_segment}"
        elif release_type == ReleaseType.MICRO:
            new_version = f"{major}.{minor}.{micro + 1}{prerelease_segment}"
        elif release_type == ReleaseType.PRE:
            if current_version.pre is None:
                pre_type = PrereleaseType.RC if prerelease_type is None else prerelease_type
                new_version = f"{major}.{minor}.{micro + 1}{pre_type.value}1"
            else:
                current_pre_type, current_pre_num = current_version.pre
                if prerelease_type is None or prerelease_type == PrereleaseType(current_pre_type):
                    new_version = f"{major}.{minor}.{micro}{current_pre_type}{current_pre_num + 1}"
                else:
                    pre_hierarchy = {"a": 1, "b": 2, "rc": 3}
                    if pre_hierarchy.get(prerelease_type.value, 0) > pre_hierarchy.get(current_pre_type, 0):
                        new_version = f"{major}.{minor}.{micro}{prerelease_type.value}1"
                    else:
                        raise ValueError(
                            f"Cannot bump to prerelease '{prerelease_type.value}' from prerelease '{current_pre_type}'. "
                        )
        elif release_type == ReleaseType.DEV:
            current_pre__segment = (
                f"{current_version.pre[0]}{current_version.pre[1]}" if current_version.pre is not None else ""
            )
            new_dev_number = current_version.dev + 1 if current_version.dev is not None else 1
            new_version = f"{major}.{minor}.{micro}{current_pre__segment}-dev{new_dev_number}"
        elif release_type == ReleaseType.POST:
            current_pre__segment = (
                f"{current_version.pre[0]}{current_version.pre[1]}" if current_version.pre is not None else ""
            )
            new_post_number = current_version.post + 1 if current_version.post is not None else 1
            new_version = f"{major}.{minor}.{micro}{current_pre__segment}-post{new_post_number}"
        else:
            raise ValueError(f"Release type '{release_type}' not recognized.")

        logging.info(f"Bumping from version {current_version} to {new_version}")
        return Version(new_version)

    except Exception as e:
        logger.error(
            f"Error bumping: {current_version}"
            f", release type: '{release_type.value}'"
            f", prerelease type: '{prerelease_type.value if prerelease_type else None}'"
        )
        raise


def update_version_files(project_file: str, new_version: Version) -> None:
    """Update version in all project files needed."""
    global files_backup

    logger.info(f"Updating files with new version: {new_version}")
    updated_files = []
    original_contents = []
    version_variables = read_from_toml_file(project_file, "semantic_release", "version_variable")
    if version_variables:
        for version_variable in version_variables:
            file_path, version_key = version_variable.split(":")
            print(f"-Updating '{version_key}' to {new_version} in '{file_path}'.")
            file = Path(file_path)
            if not file.exists():
                logger.warning(f"'{file_path}' does not exist, skipping.")
                continue
            content = file.read_text()
            new_content, found = re.subn(
                rf'{version_key} = "[^"]+"', f'{version_key} = "{new_version}"', content, count=1
            )
            if found:
                file.write_text(new_content)
                updated_files.append(file_path)
                original_contents.append(content)
                logger.info(f"Updated '{file_path}' to version {new_version}.")
            else:
                logger.warning(f"'{version_key}' not found in '{file_path}', skipping.")

    if files_backup:
        files_backup = chain(files_backup, zip(updated_files, original_contents))
    else:
        files_backup = zip(updated_files, original_contents)

    if project_file not in updated_files:
        logger.error(f"Failed to update version in  '{project_file}'.")
        raise ValueError(f"Failed to update version in '{project_file}'.")


def update_changelog(changelog_path: str, date: str, new_version: Version, changes: str) -> Optional[str]:
    """Update changelog file with changes since the last release."""
    global files_backup

    print(f"-Updating '{changelog_path}' to {new_version}.")
    try:
        changelog_entry = f"## [{new_version}] - {date}\n\n ### Changes\n"
        changelog_entry += changes + "\n\n"
        changelog_entry = open_in_editor("changelog entry", changelog_entry, "md")
        changelog_file = Path(changelog_path)
        if changelog_file.exists():
            current_content = changelog_file.read_text()
            # Find the position after the first heading
            if "\n## " in current_content:
                header, rest = current_content.split("\n## ", 1)
                new_content = f"{header}\n{changelog_entry}\n\n## {rest}"
            else:
                new_content = f"{current_content}\n\n{changelog_entry}\n"
        else:
            current_content = ""
            new_content = f"# Changelog\n\n{changelog_entry}\n"
        changelog_file.write_text(new_content)

        if files_backup:
            files_backup = chain(files_backup, zip([changelog_file], [current_content]))
        else:
            files_backup = zip([changelog_file], [current_content])

        return changelog_entry

    except Exception as e:
        logger.error(e)
        raise RuntimeError(f"Failed to update changelog: {e}")


def open_in_editor(context: str, text: str, extension: str) -> str:
    """Opens a text in VS Code for user editing."""
    print(f"-Opening {context} in VS Code for editing")
    # Create a temporary file for user editing
    with tempfile.NamedTemporaryFile(mode="w+", suffix=f".{extension}", delete=False) as tmp_file:
        tmp_file.write(text)
        tmp_file.flush()
        tmp_file_path = tmp_file.name
    subprocess.run(["code", "-w", tmp_file_path], check=True)
    # After editing, read back the user-edited content
    with open(tmp_file_path, "r") as edited_file:
        edited_text = edited_file.read()
    return edited_text


change_type = {
    ReleaseType.MAJOR: "feat",
    ReleaseType.MINOR: "feat",
    ReleaseType.MICRO: "fix",
    ReleaseType.PRE: "feat",
    ReleaseType.DEV: "feat",
    ReleaseType.POST: "chore",
}

scope = {
    ReleaseType.MAJOR: "breaking",
    ReleaseType.MINOR: "minor",
    ReleaseType.MICRO: "patch",
    ReleaseType.PRE: "prerelease",
    ReleaseType.DEV: "minor",
    ReleaseType.POST: "fix",
}

pre_release_prefix = {
    PrereleaseType.ALPHA: "alpha",
    PrereleaseType.BETA: "beta",
    PrereleaseType.RC: "rc",
}


def create_commit(
    new_version: Version,
    changes: str,
    release_type: ReleaseType,
    prerelease_type: Optional[PrereleaseType] = None,
) -> str:
    """Create a commit with the changes."""
    commit_msg = [f"release {new_version}: {change_type[release_type]}({scope[release_type]}) "]
    commit_msg += f"{pre_release_prefix[prerelease_type] if prerelease_type else ''}"
    commit_msg.append("")
    commit_msg.append("Changes")
    commit_msg.append("-" * 80)
    if "Changes" in changes:
        _, changes = changes.split("Changes", 1)
    commit_msg.append(changes.strip())
    commit_message = "\n".join(commit_msg)
    commit_message = open_in_editor("commit message", commit_message, "txt")
    print(f"-Creating release commit for version: {new_version}")
    logger.info("Staging changes...")
    subprocess.run(["git", "add", "."], check=True)
    logger.info("Committing changes...")
    subprocess.run(["git", "commit", "-m", commit_message], check=True)
    return commit_message


def create_tag(date: str, new_version: Version, changes: str) -> None:
    """Create a tag for the release."""
    tag = f"v{new_version}"
    logger.info(f"Creating tag: {tag}")
    if "Changes" in changes:
        _, changes = changes.split("Changes", 1)
    changes = f"{tag} - {date}\n{changes.strip()}"
    tag_message = open_in_editor("release note", changes, "txt")
    print(f"-Creating release tag for version: {new_version}")
    subprocess.run(["git", "tag", "-a", tag, "-m", tag_message], check=True)


def save_state(start_dt: datetime, current_version: Version) -> None:
    """Save the state to allow for rollover after release is succesful."""
    global files_backup

    try:
        with open(BEFORE_LAST_RELEASE, "wb") as f:
            pickle.dump((start_dt, current_version, files_backup), f)
        logger.info("Release state saved successfully to allow for rolloever.")
    except Exception as e:
        logger.error(f"Failed to save release state: {e}")
        raise RuntimeError(f"Failed to save release state: {e}")


def load_state() -> Tuple[datetime, Version, Optional[Iterator[Tuple[str, str]]]]:
    """Load the state to allow for rollback after release is succesful."""
    global files_backup

    try:
        with open(BEFORE_LAST_RELEASE, "rb") as f:
            start_dt, current_version, files_backup = pickle.load(f)
        logger.info("Release state loaded successfully to allow for rolloever.")
        return start_dt, current_version, files_backup
    except FileNotFoundError:
        logger.warning("No saved release found.")
        raise FileNotFoundError("No saved release found.")
    except Exception as e:
        logger.error(f"Failed to load release state: {e}")
        raise RuntimeError(f"Failed to load release state: {e}")


def rollback(start_dt: datetime) -> None:
    """Rollback changes if something goes wrong."""
    global files_backup

    logger.info("Rolling back changes...")
    try:
        # Check if last tag is after the script start
        last_tag = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"], text=True).strip()
        last_tag_commit_dt_str = subprocess.check_output(
            ["git", "log", "-1", "--format=%cd", "--date=iso-strict", last_tag], text=True
        ).strip()
        last_tag_commit_dt = datetime.fromisoformat(last_tag_commit_dt_str)
        if last_tag_commit_dt > start_dt:
            # Delete the last tag
            print(f"-Deleting tag: {last_tag}")
            subprocess.run(["git", "tag", "-d", last_tag], check=True)

        # Check if last commit is after the script start
        last_commit_dt_str = subprocess.check_output(
            ["git", "log", "-1", "--format=%cd", "--date=iso-strict"], text=True
        ).strip()
        last_commit_dt = datetime.fromisoformat(last_commit_dt_str)
        if last_commit_dt > start_dt:
            # Reset to previous commit
            print("-Deleting last commit")
            subprocess.run(["git", "reset", "--hard", "HEAD~1"], check=True)

        # Restore version files from backup
        if files_backup:
            for file_path, original_content in files_backup:
                file = Path(file_path)
                if file.exists():
                    print(f"-Restoring {file_path}")
                    file.write_text(original_content)

        logger.info("Rollback complete")

    except subprocess.CalledProcessError as e:
        logger.error(f"Error during rollback: {e}")
        logger.error("Manual intervention may be required")


if __name__ == "__main__":
    try:
        import argparse

        parser = argparse.ArgumentParser(description="Manage releases")
        subparsers = parser.add_subparsers(dest="command", help="Command to execute")

        # Create release command
        release_parser = subparsers.add_parser("create", help="Create a new release")
        release_parser.add_argument("type", choices=[t.value for t in ReleaseType], help="Type of release")
        release_parser.add_argument("--pre", choices=[t.value for t in PrereleaseType], help="Type of pre-release")
        release_parser.add_argument("--changes", nargs=1, help="Changes for changelog")

        # Rollback command
        rollback_parser = subparsers.add_parser("rollback", help="Rollback last release")

        # Logging verbose option for both commands
        parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

        args = parser.parse_args()

        # Set verbose logging level if requested
        if args.verbose:
            logger.setLevel(logging.INFO)

        if args.command == "create":
            new_version = create_release(
                ReleaseType(args.type),
                PrereleaseType(args.pre) if args.pre else None,
                changes_message=args.changes[0] if args.changes else None,
            )
            print(f"Successfully created release {new_version}")
            print("To complete the release:")
            print("1. Review the changes: CHANGLOG.md entry, latest commit and latest tag.")
            print("2. Run: git push && git push --tags")

        elif args.command == "rollback":
            print("Caution: This will rollback the last release and will delete your latest commit and tag.")
            answer = input("Are you sure you want to continue? (y/n): ")
            if answer.lower() != "y":
                print("Rollback cancelled.")
                sys.exit(0)
            start_dt, current_version, files_backup = load_state()
            rollback(start_dt)
            if os.path.exists(BEFORE_LAST_RELEASE):
                os.remove(BEFORE_LAST_RELEASE)
            print(f"Successfully rolled back to {current_version}")
            print("Please review the changes: CHANGLOG.md entry, version files, latest commit and latest tag.")
        else:
            parser.print_help()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
