"""Version management script."""

import re
import subprocess
from datetime import datetime
from pathlib import Path


def update_version(new_version: str) -> None:
    """Update version in all necessary files."""
    # Update pyproject.toml
    pyproject = Path("pyproject.toml")
    content = pyproject.read_text()
    content = re.sub(r'version = "[^"]+"', f'version = "{new_version}"', content)
    pyproject.write_text(content)

    # Update docs/conf.py
    conf = Path("docs/conf.py")
    content = conf.read_text()
    content = re.sub(r'release = "[^"]+"', f'release = "{new_version}"', content)
    conf.write_text(content)

    # Create/update CHANGELOG.md entry
    changelog = Path("CHANGELOG.md")
    if not changelog.exists():
        changelog.write_text(f"# Changelog\n\n## [{new_version}] - {datetime.now().date()}\n")

    # Git commands
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", f"Bump version to {new_version}"], check=True)
    subprocess.run(["git", "tag", f"v{new_version}"], check=True)


if __name__ == "__main__":
    import sys

    new_version = sys.argv[1]
    update_version(new_version)
