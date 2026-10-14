"""Check a codebase.md against the method repository it describes.

Reports backtick paths and annotated file-tree entries that match no tracked file or directory at
any of the given revisions, and optionally writes the document's mermaid blocks to a JSON array for
a render check. A relative path passes when some tracked path ends with it, because file trees and
tables name paths relative to the area they describe.
"""

import argparse
import json
import re
import subprocess
from pathlib import Path

_FENCE = re.compile(r"```(\w*)\n(.*?)```", re.S)
_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_PATH_CHARS = re.compile(r"[\w.\-/]+")
_FILE_SUFFIXES = (".py", ".yaml", ".yml", ".md", ".toml", ".json", ".sh", ".txt", ".ipynb", ".html")


def fenced_blocks(text: str, language: str) -> list[str]:
    """Return the bodies of fenced code blocks tagged with ``language``."""
    return [body for tag, body in _FENCE.findall(text) if tag == language]


def looks_like_path(token: str) -> bool:
    """Whether a token names a file or directory rather than a placeholder or identifier."""
    if len(token) < 2 or not _PATH_CHARS.fullmatch(token):
        return False
    return "/" in token or token.endswith(_FILE_SUFFIXES)


def inline_paths(text: str) -> set[str]:
    """Path-like inline code spans outside fenced blocks."""
    prose = _FENCE.sub("", text)
    return {span.rstrip("/") for span in _INLINE_CODE.findall(prose) if looks_like_path(span)}


def tree_paths(text: str) -> set[str]:
    """Path-like tokens on the lines of ``text`` blocks, which hold the annotated file trees."""
    tokens = set()
    for body in fenced_blocks(text, "text"):
        for line in body.splitlines():
            tokens.update(token.rstrip("/") for token in line.split() if looks_like_path(token))
    return tokens


def tracked_paths(repo: Path, revision: str) -> set[str]:
    """Every tracked file at ``revision`` and every directory that contains one."""
    listing = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "-r", "--name-only", revision],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    directories = {
        "/".join(path.split("/")[:depth])
        for path in listing
        for depth in range(1, path.count("/") + 1)
    }
    return set(listing) | directories


def unmatched(paths: set[str], tracked: set[str]) -> list[str]:
    """Paths that are neither tracked nor a trailing part of a tracked path."""
    return sorted(
        path
        for path in paths
        if path not in tracked and not any(candidate.endswith("/" + path) for candidate in tracked)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("doc", type=Path, help="the codebase.md to check")
    parser.add_argument(
        "--repo", type=Path, required=True, help="the method repository it describes"
    )
    parser.add_argument(
        "--rev",
        action="append",
        required=True,
        help="revision the doc describes; repeat for branches it maps",
    )
    parser.add_argument(
        "--mermaid-json", type=Path, help="write the mermaid blocks here as a JSON array"
    )
    args = parser.parse_args()

    text = args.doc.read_text(encoding="utf-8")
    tracked = set().union(*(tracked_paths(args.repo, revision) for revision in args.rev))
    missing = unmatched(inline_paths(text) | tree_paths(text), tracked)
    print(f"{len(missing)} path(s) match nothing at {', '.join(args.rev)}:")
    for path in missing:
        print(f"  {path}")

    if args.mermaid_json is not None:
        blocks = fenced_blocks(text, "mermaid")
        args.mermaid_json.write_text(json.dumps(blocks, ensure_ascii=False), encoding="utf-8")
        print(f"{len(blocks)} mermaid block(s) written to {args.mermaid_json}")


if __name__ == "__main__":
    main()
