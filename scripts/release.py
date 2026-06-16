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
from pathlib import Path
from typing import (
    List,
    Optional,
    Tuple,
)

from packaging.version import (
    InvalidVersion,
    Version,
)

try:
    from generate_project.skills import (
        manifest_path,
        write_manifest,
    )
except ImportError:
    # generate_project.skills only exists in the generator repo itself. In projects
    # generated from this template it is absent, so manifest regeneration becomes a
    # no-op and this script can be shared verbatim across both.
    manifest_path = None
    write_manifest = None

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
RELEASE_NOTES_FILE = "RELEASE_NOTES.md"
DEFAULT_RELEASE_DOCS_DIR = ".tmp_release_docs"
RELEASE_DOCS_FILES = {
    "commit": "commit.txt",
    "tag": "tag.txt",
    "changelog": "changelog.md",
    "release_notes": "release_notes.md",
}


class RollbackState:
    """Encapsulates file backup state for release rollback."""

    PICKLE_FILE = ".before_last_release.pkl"

    def __init__(self, start_dt: datetime, current_version: Version) -> None:
        self.start_dt = start_dt
        self.current_version = current_version
        self.files_backup: List[Tuple[str, Optional[str]]] = []

    def add_to_backup(self, entries: List[Tuple[str, Optional[str]]]) -> None:
        """Append file backup entries (path, original_content)."""
        self.files_backup.extend(entries)

    def save(self) -> None:
        """Pickle state to disk for later rollback."""
        try:
            with open(self.PICKLE_FILE, "wb") as f:
                pickle.dump(self, f)
            logger.info("Release state saved successfully to allow for rollover.")
        except OSError as e:
            raise RuntimeError(f"Failed to save release state: {e}") from e

    @classmethod
    def load(cls) -> "RollbackState":
        """Load previously saved state from disk."""
        try:
            with open(cls.PICKLE_FILE, "rb") as f:
                state = pickle.load(f)
            logger.info("Release state loaded successfully to allow for rollover.")
            return state
        except FileNotFoundError:
            raise
        except (OSError, pickle.UnpicklingError) as e:
            raise RuntimeError(f"Failed to load release state: {e}") from e

    def restore_files(self) -> None:
        """Restore backed-up files to their original content."""
        for file_path, original_content in self.files_backup:
            file = Path(file_path)
            if original_content is None:
                if file.exists():
                    print(f"-Deleting {file_path}")
                    file.unlink()
                continue
            print(f"-Restoring {file_path}")
            file.write_text(original_content)

    def cleanup(self) -> None:
        """Remove the pickle file after successful rollback."""
        if os.path.exists(self.PICKLE_FILE):
            os.remove(self.PICKLE_FILE)


def regenerate_asset_manifest(state: RollbackState) -> None:
    """Regenerate the bundled Claude asset manifest so every release ships a
    manifest in sync with the asset tree. Registered for rollback.

    No-op when ``generate_project.skills`` is unavailable (e.g. in projects
    generated from this template), so this script can be shared verbatim."""
    if manifest_path is None or write_manifest is None:
        return
    path = manifest_path()
    original = path.read_text() if path.exists() else None
    state.add_to_backup([(str(path), original)])
    write_manifest()
    if path.read_text() != original:
        print(f"-Regenerated stale asset manifest: {path}")
    else:
        print("-Asset manifest already up to date")


def create_release(
    release_type: ReleaseType,
    prerelease_type: Optional[PrereleaseType] = None,
    changes_message: Optional[str] = None,
    project_file: str = PROJECT_FILE,
    changelog_file: str = CHANGELOG_FILE,
    release_notes_file: str = RELEASE_NOTES_FILE,
    release_docs: Optional[str] = None,
    interactive: bool = True,
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
        release_notes_file: Path to the release notes markdown file. Default: RELEASE_NOTES.md.
        release_docs: Optional folder containing release artifact drafts.

    Returns:
        The release version number as a packaging.version.Version object.

    Raises:
        FileNotFoundError: If the project TOML file does not exist.
        ValueError: If the release fails due to invalid input, state or no new commits since last release.
        RuntimeError: If a git or shell command fails.
        ImportError: If tomllib or tomli is not available for reading TOML files.
    """
    time_stamp = datetime.now().astimezone()
    state: Optional[RollbackState] = None
    try:
        # Ensure working directory is a git repository and is clean
        logger.info("Checking working directory git status...")
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
        if result.stdout.strip():
            raise ValueError("Not a git repository or working directory is not clean.")

        # Verify that there are changes since the last release
        latest_tag = get_latest_release_tag()
        latest_tag_dt = get_release_tag_datetime(latest_tag) if latest_tag else None
        commit_messages = get_commits_since_tag(latest_tag)
        if not commit_messages:
            raise ValueError("No new commits since last release.")
        if changes_message:
            print("Warning: --changes is deprecated. Use --release-docs with commit.txt instead.")
        changes = changes_message or "\n".join(f"- {msg}" for msg in commit_messages)

        date = time_stamp.strftime("%Y-%m-%d")
        current_version = get_current_version(project_file)
        state = RollbackState(time_stamp, current_version)
        regenerate_asset_manifest(state)
        new_version = bump_version(current_version, release_type, prerelease_type, interactive)
        update_version_files(project_file, new_version, state)
        release_docs_path = Path(release_docs) if release_docs else None
        commit_doc = read_release_doc(release_docs_path, "commit", latest_tag, latest_tag_dt, interactive)
        commit_message = create_commit_message(new_version, changes, interactive, commit_doc)
        tag_doc = read_release_doc(release_docs_path, "tag", latest_tag, latest_tag_dt, interactive)
        tag_message = create_tag_message(date, new_version, commit_message, interactive, tag_doc)
        changelog_doc = read_release_doc(release_docs_path, "changelog", latest_tag, latest_tag_dt, interactive)
        changelog_entry = update_changelog(
            changelog_file, date, new_version, commit_message, state, interactive, changelog_doc
        )
        release_notes_doc = read_release_doc(
            release_docs_path, "release_notes", latest_tag, latest_tag_dt, interactive
        )
        create_release_notes(release_notes_file, new_version, changelog_entry, state, interactive, release_notes_doc)
        create_commit(new_version, commit_message)
        create_tag(new_version, tag_message)
        state.save()

        return new_version

    except subprocess.CalledProcessError as e:
        logger.error(f"Git or shell command failed ({e}). Rolling back changes.")
        rollback(state)
        raise RuntimeError(f"Git or shell command failed: {e}") from e
    except Exception as e:
        logger.error(f"Failed to create release: {e}. Rolling back changes.")
        rollback(state)
        raise


def get_latest_release_tag() -> Optional[str]:
    """Find the latest release tag matching 'v<PyPI version>'."""
    tags = subprocess.check_output(["git", "tag"], text=True).splitlines()
    # Filter only version tags
    valid_tags = [tag for tag in tags if re.match(r"^v\d+\.\d+\.\d+(?:[-.]?(?:a|alpha|b|beta|rc|dev|post)\d*)?$", tag)]
    if not valid_tags:
        return None
    # Sort tags by version number (PEP 440 compliant sorting)
    valid_tags.sort(key=lambda tag: Version(tag[1:]), reverse=True)
    return valid_tags[0]


def get_release_tag_datetime(tag: str) -> datetime:
    """Get the annotated tag datetime, falling back to the tagged commit datetime."""
    tag_dt = subprocess.check_output(
        ["git", "for-each-ref", f"refs/tags/{tag}", "--format=%(taggerdate:iso-strict)"],
        text=True,
    ).strip()
    if not tag_dt:
        tag_dt = subprocess.check_output(
            ["git", "log", "-1", "--format=%cd", "--date=iso-strict", tag],
            text=True,
        ).strip()
    return datetime.fromisoformat(tag_dt)


def get_commits_since_tag(tag: Optional[str]) -> list[str]:
    """Retrieve commit messages since the given tag."""
    range = f"{tag}..HEAD" if tag else "HEAD"
    commit_messages = subprocess.check_output(["git", "log", f"{range}", "--pretty=format:%s"], text=True).splitlines()
    return commit_messages


def read_release_doc(
    release_docs_path: Optional[Path],
    doc_key: str,
    latest_tag: Optional[str],
    latest_tag_dt: Optional[datetime],
    interactive: bool,
) -> Optional[str]:
    """Read a release documentation draft if it exists and is newer than the previous release tag."""
    if release_docs_path is None:
        return None

    doc_name = RELEASE_DOCS_FILES[doc_key]
    doc_path = release_docs_path / doc_name
    description = f"{doc_path} for {doc_key.replace('_', ' ')}"

    if not release_docs_path.is_dir():
        confirm_release_doc_fallback(f"{release_docs_path} does not exist.", interactive)
        return None
    if not doc_path.exists():
        confirm_release_doc_fallback(f"{description} is missing.", interactive)
        return None
    content = doc_path.read_text()
    if not content.strip():
        confirm_release_doc_fallback(f"{description} is empty.", interactive)
        return None
    if latest_tag_dt is not None:
        doc_mtime = datetime.fromtimestamp(doc_path.stat().st_mtime).astimezone()
        if doc_mtime < latest_tag_dt:
            confirm_release_doc_fallback(f"{description} is older than {latest_tag}.", interactive)
            return None
    return content


def confirm_release_doc_fallback(message: str, interactive: bool) -> None:
    """Confirm or warn before falling back from a missing, empty, or stale release doc."""
    fallback_message = f"{message} Falling back to generated release content."
    if not interactive:
        print(f"Warning: {fallback_message}")
        return None
    ask_user(f"{fallback_message}\nContinue?", ["Continue", "Cancel"])
    return None


def get_current_version(project_file: str) -> Version:
    """Get current version from project file"""
    # Try PEP 621 format first (project.version)
    version_text = read_from_toml_file(project_file, "project", "version")

    # Fall back to Poetry format (tool.poetry.version)
    if not version_text:
        version_text = read_from_toml_file(project_file, "poetry", "version")

    if not version_text:
        raise ValueError(f"Version not found in '{project_file}'. Please check the file format.")
    try:
        version = Version(version_text)
        logger.info(f"Current version found in '{project_file}': '{version}'")
        return version
    except InvalidVersion as e:
        raise ValueError(f"Invalid version format in '{project_file}': '{version_text}'") from e


def read_from_toml_file(file_path: str, section: str, key: str) -> Optional[str]:
    """Reads a toml file to get the contents of a specific tool section and key."""
    try:
        import tomllib  # Part of the standard library on Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # For Python < 3.11
        except ImportError:
            raise ImportError("Please install tomli package: pip install tomli")

    toml_file = Path(file_path)
    if not toml_file.exists():
        raise FileNotFoundError(f"'{file_path}' does not exist.")
    try:
        with open(toml_file, "rb") as f:
            toml_data = tomllib.load(f)
        # Support both PEP 621 format (project.version) and Poetry format (tool.poetry.version)
        if section == "project":
            # PEP 621 format: read from root level
            value = toml_data.get(section, {}).get(key)
        else:
            # Poetry format: read from tool section
            value = toml_data.get("tool", {}).get(section, {}).get(key)
        if not value:
            print(f"Warning: '{key}' field of section '{section}' not found in '{file_path}'.")
        return value
    except Exception as e:
        logger.error(f"Error reading '{key}' field of section 'tool.{section}' from {file_path}: {e}")
        raise


def get_stable_components(version: Version) -> Tuple[int, int, int]:
    major = version.release[0] if len(version.release) > 0 else 0
    minor = version.release[1] if len(version.release) > 1 else 0
    micro = version.release[2] if len(version.release) > 2 else 0
    return major, minor, micro


def bump_version(
    current_version: Version,
    release_type: ReleaseType,
    prerelease_type: Optional[PrereleaseType] = None,
    interactive: bool = True,
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

    def bump_to_dev() -> str:
        if prerelease_type is not None:
            raise ValueError("Cannot bump to dev release with a prerelease type specified.")
        major, minor, micro = get_stable_components(current_version)
        if current_version.dev is not None:
            # Already a dev release: just increment dev number
            current_pre_segment = (
                f"{current_version.pre[0]}{current_version.pre[1]}" if current_version.pre is not None else ""
            )
            return f"{major}.{minor}.{micro}{current_pre_segment}.dev{current_version.dev + 1}"
        if current_version.pre is not None:
            # From pre-release: dev1 of next pre-release number
            current_pre_type, current_pre_num = current_version.pre
            return f"{major}.{minor}.{micro}{current_pre_type}{current_pre_num + 1}.dev1"
        # From stable or post: dev of next component
        component = choose_component_for_dev()
        if component == "major":
            return f"{major + 1}.0.0.dev1"
        elif component == "minor":
            return f"{major}.{minor + 1}.0.dev1"
        return f"{major}.{minor}.{micro + 1}.dev1"

    def choose_component_for_dev() -> str:
        """
        Ask the user which component to bump for a dev release.
        """
        if not interactive:
            logger.info("Non-interactive mode: automatically choosing 'micro' for dev release.")
            return "micro"
        message = "Which component would you like to bump for the dev release?"
        return ask_user(message, ["Major", "Minor", "Micro", "Cancel"]).lower()

    def bump_to_pre() -> str:
        if current_version.pre is not None:
            # Already a pre-release: bump to the requested pre-release
            return bump_from_pre_to_pre()
        # Release type is PRE and not currently a pre-release: start a new pre-release sequence
        major, minor, micro = get_stable_components(current_version)
        pre_type = PrereleaseType.RC if prerelease_type is None else prerelease_type
        # Bump micro only if not coming from a lower dev version
        target_micro = micro + 1 if current_version.dev is None else micro
        return f"{major}.{minor}.{target_micro}{pre_type.value}1"

    def bump_from_pre_to_pre() -> str:
        major, minor, micro = get_stable_components(current_version)
        current_pre_type, current_pre_num = current_version.pre  # type: ignore
        if prerelease_type is None or prerelease_type == PrereleaseType(current_pre_type):
            # Same type of pre-release: bump the current pre-release number if not comming from dev
            target_pre = current_pre_num + 1 if current_version.dev is None else current_pre_num
            return f"{major}.{minor}.{micro}{current_pre_type}{target_pre}"
        pre_hierarchy = {"a": 1, "b": 2, "rc": 3}
        if pre_hierarchy.get(prerelease_type.value, 0) > pre_hierarchy.get(current_pre_type, 0):
            # Higher type of pre-release: start a new pre-release sequence
            return f"{major}.{minor}.{micro}{prerelease_type.value}1"
        raise ValueError(f"Cannot bump to prerelease '{prerelease_type.value}' from prerelease '{current_pre_type}'. ")

    def bump_to_micro() -> str:
        major, minor, micro = get_stable_components(current_version)
        if current_version.pre is None:
            # Not comming from a pre-release:
            # - bump the micro component if not comming from dev
            # - start a new pre-release sequence if requested
            target_micro = micro + 1 if current_version.dev is None else micro
            prerelease_segment = f"{prerelease_type.value}1" if prerelease_type else ""
            return f"{major}.{minor}.{target_micro}{prerelease_segment}"
        if prerelease_type is None:
            # Finalize the current pre-release line to stable
            return f"{major}.{minor}.{micro}"
        # From pre-release to pre-release request
        if current_version.dev is not None:
            # If comming from a dev release: drop the dev or move to higher type of pre-release
            return bump_from_pre_to_pre()
        # Moved to next micro base and start a new pre-release sequence
        return f"{major}.{minor}.{micro+1}{prerelease_type.value}1"

    def bump_to_minor() -> str:
        major, minor, micro = get_stable_components(current_version)
        if current_version.pre is None:
            # Not comming from a pre-release:
            # - bump the minor component if not comming from dev
            # - start a new pre-release sequence if requested
            target_minor = minor + 1 if current_version.dev is None or micro != 0 else minor
            prerelease_segment = f"{prerelease_type.value}1" if prerelease_type else ""
            return f"{major}.{target_minor}.0{prerelease_segment}"
        if prerelease_type is None:
            # Finalize the current pre-release line to stable
            confirm_finalize_from_prerelease(major, minor, micro)
            return f"{major}.{minor}.{micro}"
        # From pre-release to pre-relase request
        if current_version.dev is not None:
            # If comming from a dev release: drop the dev or move to higher type of pre-release
            return bump_from_pre_to_pre()
        # Moved to the next minor base and start a new pre-release sequence
        return f"{major}.{minor+1}.0{prerelease_type.value}1"

    def bump_to_major() -> str:
        major, minor, micro = get_stable_components(current_version)
        if current_version.pre is None:
            # Not comming from a pre-release:
            # - bump the major component if not comming from dev
            # - start a new pre-release sequence if requested
            target_major = major + 1 if current_version.dev is None or minor != 0 or micro != 0 else major
            prerelease_segment = f"{prerelease_type.value}1" if prerelease_type else ""
            return f"{target_major}.0.0{prerelease_segment}"
        if prerelease_type is None:
            # Finalize the current pre-release line to stable
            confirm_finalize_from_prerelease(major, minor, micro)
            return f"{major}.{minor}.{micro}"
        # From pre-release to pre-relase request
        if current_version.dev is not None:
            # If comming from a dev release: drop the dev or move to higher type of pre-release
            return bump_from_pre_to_pre()
        # Moved to the next major base and start a new pre-release sequence
        return f"{major + 1}.0.0{prerelease_type.value}1"

    def confirm_finalize_from_prerelease(major: int, minor: int, micro: int) -> None:
        """
        Confirm when bumping MINOR or MAJOR from a prerelease without specifying a new prerelease.
        """
        if not interactive:
            logger.info("Non-interactive mode: automatically finalizing prerelease.")
            return
        message = (
            f"Bumping {release_type.value} from prerelease {current_version} will finalize to "
            f"{major}.{minor}.{micro} instead of incrementing the {release_type.value} component.\n"
            "If you intended to increment, create an additional release with the same options"
        )
        ask_user(message, ["Continue", "Cancel"])

    def bump_to_post() -> str:
        if prerelease_type is not None:
            raise ValueError("Cannot bump to post release with a prerelease type specified.")
        if current_version.pre is not None:
            raise ValueError("Cannot create post release from a pre-release version.")
        if current_version.dev is not None:
            raise ValueError("Cannot create post release from a dev version.")
        major, minor, micro = get_stable_components(current_version)
        new_post_number = current_version.post + 1 if current_version.post is not None else 1
        return f"{major}.{minor}.{micro}.post{new_post_number}"

    bump_function = {
        ReleaseType.POST: bump_to_post,
        ReleaseType.MAJOR: bump_to_major,
        ReleaseType.MINOR: bump_to_minor,
        ReleaseType.MICRO: bump_to_micro,
        ReleaseType.PRE: bump_to_pre,
        ReleaseType.DEV: bump_to_dev,
    }

    if release_type not in ReleaseType:
        raise ValueError(f"Release type '{release_type}' not supported.")
    new_version = bump_function[release_type]()
    try:
        logger.info(f"Bumping from version {current_version} to {new_version}")
        return Version(new_version)
    except InvalidVersion:
        logger.error(
            f"Error bumping: {current_version}"
            f", release type: '{release_type.value}'"
            f", prerelease type: '{prerelease_type.value if prerelease_type else None}'"
            f", new version: '{new_version}'"
        )
        raise


def update_version_files(project_file: str, new_version: Version, state: RollbackState) -> None:
    """Update version in all project files needed."""

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
                print(f"Warning: '{file_path}' does not exist, skipping.")
                continue
            content = file.read_text()
            # Build pattern with capturing groups to preserve format
            pattern = rf'({re.escape(version_key)})(\s*)([:=])(\s*)(["\']?)([^"\'<>\s\n)]+)(["\']?)'

            def replace_version(match: re.Match) -> str:
                """Preserve the original format while updating the version."""
                key = match.group(1)  # version_key
                space1 = match.group(2)  # whitespace before separator
                separator = match.group(3)  # : or =
                space2 = match.group(4)  # whitespace after separator
                open_quote = match.group(5)  # opening quote (", ', or empty)
                close_quote = match.group(7)  # closing quote (", ', or empty)

                return f"{key}{space1}{separator}{space2}{open_quote}{new_version}{close_quote}"

            new_content, found = re.subn(pattern, replace_version, content, count=1)
            if found:
                file.write_text(new_content)
                updated_files.append(file_path)
                original_contents.append(content)
                logger.info(f"Updated '{file_path}' to version {new_version}.")
            else:
                print(f"Warning: '{version_key}' not found in '{file_path}', skipping.")

    state.add_to_backup(list(zip(updated_files, original_contents)))

    if project_file not in updated_files:
        raise ValueError(f"Failed to update version in '{project_file}'.")


def update_changelog(
    changelog_path: str,
    date: str,
    new_version: Version,
    commit_message: str,
    state: RollbackState,
    interactive: bool = True,
    initial_content: Optional[str] = None,
) -> str:
    """Update changelog file with changes since the last release."""

    logger.info(f"Updating '{changelog_path}' to {new_version}.")
    try:
        changelog_entry = initial_content or f"## [{new_version}] - {date}\n\n### Changes\n"
        if initial_content is None:
            changelog_entry += extract_changes_section(commit_message) + "\n\n"
        if interactive:
            changelog_entry = open_in_editor("changelog entry", changelog_entry, "md")
        changelog_file = Path(changelog_path)
        if changelog_file.exists():
            current_content = changelog_file.read_text()
            # Find the position after the first heading
            if "\n## " in current_content:
                header, rest = current_content.split("\n## ", 1)
                new_content = f"{header.rstrip()}\n\n{changelog_entry.strip()}\n\n## {rest}"
            else:
                new_content = f"{current_content.rstrip()}\n\n{changelog_entry.strip()}\n"
        else:
            current_content = ""
            new_content = f"# Changelog\n\n{changelog_entry.strip()}\n"
        changelog_file.write_text(new_content)

        state.add_to_backup([(str(changelog_file), current_content)])

        return changelog_entry

    except OSError as e:
        raise RuntimeError(f"Failed to update changelog: {e}") from e


def create_release_notes(
    release_notes_path: str,
    new_version: Version,
    changelog_entry: str,
    state: RollbackState,
    interactive: bool = True,
    initial_content: Optional[str] = None,
) -> str:
    """Write markdown release notes for the GitHub Release body."""

    logger.info(f"Updating '{release_notes_path}' to {new_version}.")
    try:
        release_notes = initial_content or changelog_entry.strip() + "\n"
        if interactive:
            release_notes = open_in_editor("release notes", release_notes, "md")
        release_notes_file = Path(release_notes_path)
        current_content = release_notes_file.read_text() if release_notes_file.exists() else None
        release_notes_file.write_text(release_notes)
        state.add_to_backup([(str(release_notes_file), current_content)])
        return release_notes
    except OSError as e:
        raise RuntimeError(f"Failed to update release notes: {e}") from e


def ask_user(message: str, choices: List[str], cancel: str = "Cancel") -> str:
    """Prompt user to choose an option and return the selected choice."""
    print(message)
    for index, choice in enumerate(choices, start=1):
        print(f"{index}. {choice}")
    while True:
        answer = input(f"Select an option (1 - {len(choices)}): ").strip()
        if answer.isdigit():
            selected = int(answer)
            if 1 <= selected <= len(choices):
                choice = choices[selected - 1]
                if choice.lower() == cancel.lower():
                    raise ValueError("Release cancelled by user.")
                return choice
        print("Invalid choice. Please try again.")


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


version_suffix = {
    "a": "alpha",
    "b": "beta",
    "rc": "rc",
}


def analyze_version_for_commit(version: Version) -> Tuple[str, str, str]:
    """
    Analyze version to determine commit message header components from the version structure.

    Returns:
        tuple: (change_type, scope, suffix)
    """
    # Determine version suffix
    suffix = ""
    if version.pre:
        suffix = version_suffix.get(version.pre[0], "")
    if version.post:
        suffix = f"post{'-' if suffix else ''}{suffix}"
    if version.dev:
        suffix = f"dev{'-' if suffix else ''}{suffix}"

    # Get stable version components
    major, minor, micro = get_stable_components(version)

    # Determine change_type and scope based on version structure
    if version.post is not None:
        # Post-release: always a patch-level chore
        change_type = "chore"
        scope = "patch"
    elif version.pre or version.dev:
        # Pre-release or dev release
        scope = "prerelease"
        if micro == 0 and (minor > 0 or major > 0):
            change_type = "feat"
        else:
            change_type = "fix"
    else:
        # Stable release
        if micro == 0 and minor == 0 and major > 0:
            change_type = "feat"
            scope = "breaking"
        elif micro == 0 and minor > 0:
            change_type = "feat"
            scope = "minor"
        else:
            change_type = "fix"
            scope = "patch"

    return change_type, scope, suffix


def extract_changes_section(message: str) -> str:
    """Extract the user-facing changes body from a release message."""
    if "Changes" in message:
        _, message = message.split("Changes", 1)
        lines = message.strip().splitlines()
        if lines and set(lines[0]) == {"-"}:
            lines = lines[1:]
        return "\n".join(lines).strip()
    return message.strip()


def create_commit_message(
    new_version: Version,
    changes: str,
    interactive: bool = True,
    initial_content: Optional[str] = None,
) -> str:
    """Create the plain text release commit message."""
    if initial_content is not None:
        commit_message = initial_content
    else:
        # Determine commit message components from the version itself
        change_type, scope, suffix = analyze_version_for_commit(new_version)

        header = f"release {new_version}: {change_type}({scope})"
        if suffix:
            header = f"{header} {suffix}"
        commit_msg = [header]
        commit_msg.append("")
        commit_msg.append("Changes")
        commit_msg.append("-" * 80)
        commit_msg.append(changes.strip())
        commit_message = "\n".join(commit_msg)
    if interactive:
        commit_message = open_in_editor("commit message", commit_message, "txt")
    return commit_message


def create_tag_message(
    date: str,
    new_version: Version,
    commit_message: str,
    interactive: bool = True,
    initial_content: Optional[str] = None,
) -> str:
    """Create the plain text release tag message."""
    tag_message = initial_content or f"Release v{new_version} - {date}\n\n{extract_changes_section(commit_message)}"
    if interactive:
        tag_message = open_in_editor("tag message", tag_message, "txt")
    return tag_message


def create_commit(
    new_version: Version,
    commit_message: str,
) -> None:
    """Create a commit with the release changes."""
    print(f"-Creating release commit for version: {new_version}")
    logger.info("Staging changes...")
    subprocess.run(["git", "add", "."], check=True)
    logger.info("Committing changes...")
    subprocess.run(["git", "commit", "-m", commit_message], check=True)


def create_tag(new_version: Version, tag_message: str) -> None:
    """Create a tag for the release."""
    tag = f"v{new_version}"
    logger.info(f"Creating tag: {tag}")
    logger.info(f"Creating release tag for version: {new_version}")
    subprocess.run(["git", "tag", "-a", tag, "-m", tag_message], check=True)


def rollback(state: Optional[RollbackState]) -> bool:
    """Rollback changes if something goes wrong. Returns True on success, False on failure."""
    if not state:
        return True
    logger.info("Rolling back changes...")
    try:
        # Check if last tag is after the script start
        last_tag = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"], text=True).strip()
        last_tag_commit_dt_str = subprocess.check_output(
            ["git", "log", "-1", "--format=%cd", "--date=iso-strict", last_tag], text=True
        ).strip()
        last_tag_commit_dt = datetime.fromisoformat(last_tag_commit_dt_str)
        if last_tag_commit_dt > state.start_dt:
            # Delete the last tag
            print(f"-Deleting tag: {last_tag}")
            subprocess.run(["git", "tag", "-d", last_tag], check=True)

        # Check if last commit is after the script start
        last_commit_dt_str = subprocess.check_output(
            ["git", "log", "-1", "--format=%cd", "--date=iso-strict"], text=True
        ).strip()
        last_commit_dt = datetime.fromisoformat(last_commit_dt_str)
        if last_commit_dt > state.start_dt:
            # Reset to previous commit
            print("-Deleting last commit")
            subprocess.run(["git", "reset", "--hard", "HEAD~1"], check=True)

        # Restore version files from backup
        state.restore_files()

        logger.info("Rollback completed")
        return True

    except subprocess.CalledProcessError as e:
        # Intentionally swallowed: rollback runs inside an exception handler,
        # so re-raising here would mask the original error.
        logger.error(f"Error during rollback: {e}")
        logger.error("Manual intervention may be required")
        return False


def main() -> None:
    try:
        import argparse

        parent_parser = argparse.ArgumentParser(add_help=False)
        parent_parser.add_argument(
            "--log",
            "-l",
            nargs="?",
            const="",
            default=None,
            metavar="FILE",
            help="Enable logging (optionally to FILE)",
        )

        parser = argparse.ArgumentParser(description="Manage releases")
        subparsers = parser.add_subparsers(dest="command", help="Command to execute")

        # Create release command
        release_parser = subparsers.add_parser("create", parents=[parent_parser], help="Create a new release")
        release_parser.add_argument("type", choices=[t.value for t in ReleaseType], help="Type of release")
        release_parser.add_argument("--pre", choices=[t.value for t in PrereleaseType], help="Type of pre-release")
        release_parser.add_argument("--changes", nargs=1, help="Deprecated. Use --release-docs with commit.txt.")
        release_parser.add_argument(
            "--release-docs",
            nargs="?",
            const=DEFAULT_RELEASE_DOCS_DIR,
            default=None,
            help=f"Folder containing release drafts. Defaults to {DEFAULT_RELEASE_DOCS_DIR} when provided.",
        )
        release_parser.add_argument(
            "--no-interactive", action="store_true", help="Disable interactive prompts (for CI)"
        )

        # Rollback command
        subparsers.add_parser("rollback", parents=[parent_parser], help="Rollback last release")

        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            sys.exit(0)

        # Reconfigure logging based on CLI flags
        if args.log is not None:
            root = logging.getLogger()
            root.setLevel(logging.INFO)
            for h in root.handlers:
                root.removeHandler(h)
            handler = logging.FileHandler(args.log) if args.log else logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            root.addHandler(handler)

        if args.command == "create":
            new_version = create_release(
                ReleaseType(args.type),
                PrereleaseType(args.pre) if args.pre else None,
                changes_message=args.changes[0] if args.changes else None,
                release_docs=args.release_docs,
                interactive=not args.no_interactive,
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
            state = RollbackState.load()
            success = rollback(state)
            state.cleanup()
            if success:
                print(f"Successfully rolled back to {state.current_version}")
            else:
                print(
                    f"Warning: Rollback to {state.current_version} was only partial. Manual intervention may be required."
                )
            print("Please review the changes: CHANGLOG.md entry, version files, latest commit and latest tag.")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
