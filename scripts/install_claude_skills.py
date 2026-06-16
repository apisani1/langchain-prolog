#!/usr/bin/env python3
"""Install the release-docs Claude skill and /release-docs command into this repo.

This project follows the generate-project release-docs convention: a Claude skill that
drafts release artifacts under .tmp_release_docs/ before you cut a release (consumed by
scripts/release.py via --release-docs). This script installs that skill + command into the
repository's own .claude/ directory so it is available when working in this repo.

The set of files to install is read from a single manifest (asset_manifest.txt), never
hardcoded here. Asset source, in order:
  1. An installed `generate_project` package (reads its bundled manifest + copies) — no network.
  2. Otherwise, download the manifest and the files it lists from GitHub (asks first).

Usage:
  python scripts/install_claude_skills.py             # into ./.claude (asks before any download)
  python scripts/install_claude_skills.py --force     # overwrite existing files
  python scripts/install_claude_skills.py --dry-run   # show what would happen
  python scripts/install_claude_skills.py --dest ~/.claude   # install globally instead
  python scripts/install_claude_skills.py --yes       # don't prompt before downloading
  python scripts/install_claude_skills.py --ref v2.1.0   # download from a specific git ref
"""

import argparse
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
)

REPO = "apisani1/generate-project"
ASSETS_SUBPATH = "src/generate_project/claude_assets"
MANIFEST_NAME = "asset_manifest.txt"

EPILOG = """
What Gets Installed:
  The release-docs Claude skill and the /release-docs command, which draft release
  artifacts (commit message, tag message, CHANGELOG entry, release notes) under
  .tmp_release_docs/ before you cut a release (consumed by scripts/release.py).
    skills/release-docs/      The skill (SKILL.md, agents, helper scripts)
    commands/release-docs.md  The /release-docs slash command
  The exact file list comes from the asset manifest, so it stays correct as assets change.

Asset Source (resolved automatically):
  1. An installed generate_project package -- reads its bundled manifest, copies (no network).
  2. Otherwise -- downloads the manifest and its files from github.com/apisani1/generate-project
     after asking for confirmation (use --yes to skip the prompt, --ref to pick a tag).

Examples:
  %(prog)s                       # Install into <repo>/.claude (asks before downloading)
  %(prog)s --dry-run             # Preview without writing anything
  %(prog)s --force               # Overwrite existing files
  %(prog)s --dest ~/.claude      # Install globally instead of into this repo
  %(prog)s --yes --ref v2.1.0    # Download a specific ref without prompting
"""


def parse_manifest(text: str) -> List[str]:
    """Parse manifest text into relative paths, skipping blank lines and ``#`` comments."""
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def local_assets_dir() -> Optional[Path]:
    """Return the bundled claude_assets dir from an installed generate_project, or None."""
    try:
        import generate_project
    except ImportError:
        return None
    candidate = Path(generate_project.__file__).parent / "claude_assets"
    return candidate if candidate.is_dir() else None


def confirm_download(ref: str, assume_yes: bool) -> bool:
    """Ask before downloading from GitHub (unless --yes). Returns True to proceed."""
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        print(
            "generate_project is not installed and stdin is not interactive; "
            "re-run with --yes to allow downloading the skill files.",
            file=sys.stderr,
        )
        return False
    answer = input(f"Download release-docs skill files from github.com/{REPO}@{ref}? [y/N] ")
    return answer.strip().lower() in ("y", "yes")


def _download(url: str) -> Optional[bytes]:
    """Fetch ``url`` and return its bytes, or None (after printing) on failure."""
    try:
        with urllib.request.urlopen(url) as resp:  # noqa: S310
            return resp.read()
    except urllib.error.URLError as exc:
        print("error: failed to download " + url + ": " + str(exc), file=sys.stderr)
        return None


def install(dest: Path, force: bool, dry_run: bool, ref: str, assume_yes: bool) -> int:
    """Install the manifest-listed assets into ``dest`` and report what happened.

    Resolves the asset source first: the bundled assets of an installed ``generate_project``
    package when available (no network), otherwise a confirmed download from GitHub at ``ref``.
    In both cases the file list comes from the asset manifest. Each asset is copied/written
    under ``dest``, preserving the skills/ and commands/ layout; files that already exist are
    skipped unless ``force`` is set. When ``dry_run`` is True nothing is written, only reported.

    Returns a process exit code: 0 on success, 1 if no asset source is available or a
    download fails.
    """
    dest = dest.expanduser()
    assets_dir = local_assets_dir()

    payloads: Dict[str, bytes] = {}
    items: List[Tuple[str, Optional[Path]]] = []
    if assets_dir is not None:
        rels = parse_manifest((assets_dir / MANIFEST_NAME).read_text())
        items = [(rel, assets_dir / rel) for rel in rels]
        source_desc = "installed generate_project (" + str(assets_dir) + ")"
    else:
        if not confirm_download(ref, assume_yes):
            print("Aborted: no asset source available.", file=sys.stderr)
            return 1
        base_url = "https://raw.githubusercontent.com/" + REPO + "/" + ref + "/" + ASSETS_SUBPATH + "/"
        manifest_bytes = _download(base_url + MANIFEST_NAME)
        if manifest_bytes is None:
            return 1
        rels = parse_manifest(manifest_bytes.decode("utf-8"))
        for rel in rels:
            data = _download(base_url + rel)
            if data is None:
                return 1
            payloads[rel] = data
        items = [(rel, None) for rel in rels]
        source_desc = "github.com/" + REPO + "@" + ref

    installed: List[Path] = []
    skipped: List[Path] = []
    for rel, src in items:
        target = dest / rel
        if target.exists() and not force:
            skipped.append(target)
            continue
        installed.append(target)
        if dry_run:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if rel in payloads:
            target.write_bytes(payloads[rel])
        elif src is not None:
            shutil.copy2(src, target)

    verb = "Would install" if dry_run else "Installed"
    print(verb + " " + str(len(installed)) + " file(s) from " + source_desc + " into " + str(dest))
    for path in installed:
        print("  + " + str(path))
    if skipped:
        print("Skipped " + str(len(skipped)) + " existing file(s); pass --force to overwrite:")
        for path in skipped:
            print("  = " + str(path))
    return 0


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description="Install the release-docs Claude skill/command into this repository.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG,
    )
    parser.add_argument(
        "--dest", type=Path, default=repo_root / ".claude", help="Target .claude directory (default: <repo>/.claude)"
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be installed without writing")
    parser.add_argument("--yes", action="store_true", help="Do not prompt before downloading from GitHub")
    parser.add_argument("--ref", default="main", help="Git ref to download from when generate_project is absent")
    args = parser.parse_args()
    return install(args.dest, args.force, args.dry_run, args.ref, args.yes)


if __name__ == "__main__":
    raise SystemExit(main())
