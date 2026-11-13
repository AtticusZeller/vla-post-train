"""Convert a local Markdown document into a body that GitHub issues render correctly.

GitHub parses Markdown before MathJax sees the math, so plain ``$...$`` and ``$$...$$`` lose
backslash escapes (``\\{`` becomes ``{``), a line ending in ``\\\\`` turns into a hard break, and a
``<`` starts an HTML tag that swallows the rest of the formula. GitHub also rejects some macros,
such as ``\\operatorname``. This script rewrites math into the code-span forms GitHub leaves
untouched, patches the known breakages, and resolves relative links. Local images become raw URLs
pinned to a pushed commit, because gh has no API for issue attachments. It never edits the source.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, unquote

_FENCE = re.compile(r"^(```|~~~)")
_DISPLAY_START = re.compile(r"^\s*(\$\$|\\\[)\s*(.*)$")
_INLINE_PAREN = re.compile(r"\\\((.+?)\\\)")
# ASCII word boundaries only: Chinese prose often puts a formula right next to a CJK character.
_INLINE_DOLLAR = re.compile(r"(?<![\\$`\w])\$(?![\s$`])([^$\n]+?)(?<![\s\\])\$(?![$`\w])", re.ASCII)
_CODE_SPAN = re.compile(r"(\$`[^`\n]*`\$|`[^`\n]*`)")
_LINK = re.compile(r"(?<!!)\[([^\]\n]+)\]\(([^)\s]+)\)")
_IMAGE = re.compile(r"(!\[[^\]\n]*\]\()([^)\s]+)((?:\s+\"[^\"\n]*\")?\))")
_HTML_IMG = re.compile(r"(<img\b[^>]*?\bsrc=[\"'])([^\"']+)([\"'])", re.IGNORECASE)
_EXTERNAL = re.compile(r"^([a-z][a-z0-9+.-]*:|#|//)", re.IGNORECASE)
_GITHUB_REMOTE = re.compile(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/?$")
_MACRO_REPLACEMENTS = {r"\operatorname{": r"\mathrm{"}


def fix_math(expr: str, in_table: bool = False) -> str:
    """Patch a math expression so GitHub's HTML pipeline and MathJax accept it."""
    for old, new in _MACRO_REPLACEMENTS.items():
        expr = expr.replace(old, new)
    expr = re.sub(r"<(?!=)", r"\\lt ", expr)
    expr = re.sub(r">", r"\\gt ", expr)
    if in_table:
        expr = expr.replace(r"\|", r"\Vert ").replace("|", r"\vert ")
    return expr


def join_trailing_row_breaks(lines: list[str]) -> list[str]:
    """Join lines that end in ``\\\\`` with the next one; GitHub turns that newline into a break."""
    out: list[str] = []
    for line in lines:
        if out and out[-1].rstrip().endswith("\\\\"):
            out[-1] = out[-1].rstrip() + " " + line.lstrip()
        else:
            out.append(line)
    return out


def math_block(body: list[str]) -> list[str]:
    """Render display math as a fenced ``math`` block."""
    body = join_trailing_row_breaks([fix_math(line) for line in body])
    return ["```math", *body, "```"]


def git(cwd: Path, *args: str) -> str:
    """Run git in ``cwd`` and return its stripped stdout, or raise with git's message."""
    proc = subprocess.run(["git", "-C", str(cwd), *args], check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


class RepoSnapshot:
    """One GitHub repository pinned to a commit, used to publish files by raw URL."""

    def __init__(self, root: Path, remote: str, rev: str | None):
        self.root = root
        url = git(root, "remote", "get-url", remote)
        match = _GITHUB_REMOTE.search(url)
        if not match:
            raise RuntimeError(f"remote {remote} of {root} is not on github.com: {url}")
        self.slug = match.group(1)
        ref = rev or f"{remote}/HEAD"
        try:
            self.sha = git(root, "rev-parse", "--verify", f"{ref}^{{commit}}")
        except RuntimeError as e:
            raise RuntimeError(f"cannot resolve {ref} in {root}; fetch the remote or pass --rev ({e})")

    def raw_url(self, path: Path) -> str:
        """Raw URL of ``path`` at the pinned commit."""
        rel = path.relative_to(self.root).as_posix()
        return f"https://raw.githubusercontent.com/{self.slug}/{self.sha}/{quote(rel)}"

    def problem(self, path: Path) -> str | None:
        """Why the pinned commit cannot serve ``path`` as it is on disk, or None if it can."""
        rel = path.relative_to(self.root).as_posix()
        try:
            pinned = git(self.root, "rev-parse", f"{self.sha}:{rel}")
        except RuntimeError:
            return f"not in {self.slug}@{self.sha[:7]}; commit and push it first"
        if pinned != git(self.root, "hash-object", str(path)):
            return f"differs from {self.slug}@{self.sha[:7]}; commit and push the current version"
        return None


class ImageResolver:
    """Map local image paths in a document to raw URLs and collect the ones that cannot be served."""

    def __init__(self, doc_dir: Path, remote: str = "origin", rev: str | None = None):
        self.doc_dir = doc_dir
        self.remote = remote
        self.rev = rev
        self.snapshots: dict[Path, RepoSnapshot] = {}
        self.problems: list[str] = []

    def snapshot(self, path: Path) -> RepoSnapshot:
        """The pinned repository that contains ``path``; submodules count as their own repository."""
        root = Path(git(path.parent, "rev-parse", "--show-toplevel"))
        if root not in self.snapshots:
            self.snapshots[root] = RepoSnapshot(root, self.remote, self.rev)
        return self.snapshots[root]

    def url(self, target: str) -> str:
        """URL for an image reference; external URLs pass through unchanged."""
        if _EXTERNAL.match(target):
            return target
        path = (self.doc_dir / unquote(target)).resolve()
        if not path.is_file():
            self.problems.append(f"{target}: no such file {path}")
            return target
        try:
            snap = self.snapshot(path)
            problem = snap.problem(path)
        except RuntimeError as e:
            self.problems.append(f"{target}: {e}")
            return target
        if problem:
            self.problems.append(f"{target}: {problem}")
        return snap.raw_url(path)


def rewrite_images(text: str, images: ImageResolver | None) -> str:
    """Point Markdown and HTML image references at URLs GitHub can load."""
    if images is None:
        return text
    text = _IMAGE.sub(lambda m: m.group(1) + images.url(m.group(2)) + m.group(3), text)
    return _HTML_IMG.sub(lambda m: m.group(1) + images.url(m.group(2)) + m.group(3), text)


def convert_inline(line: str, link_base: str | None, images: ImageResolver | None = None) -> str:
    """Convert inline math, images, and links in one prose line, leaving code spans alone."""
    in_table = line.lstrip().startswith("|")
    parts = _CODE_SPAN.split(line)
    for i in range(0, len(parts), 2):
        text = parts[i]
        text = _INLINE_PAREN.sub(lambda m: f"$`{fix_math(m.group(1).strip(), in_table)}`$", text)
        text = _INLINE_DOLLAR.sub(lambda m: f"$`{fix_math(m.group(1), in_table)}`$", text)
        text = rewrite_images(text, images)
        text = _LINK.sub(lambda m: rewrite_link(m, link_base), text)
        parts[i] = text
    return "".join(parts)


def rewrite_link(match: re.Match, link_base: str | None) -> str:
    """Make a relative link absolute, or keep only its text when no base is given."""
    text, target = match.group(1), match.group(2)
    if _EXTERNAL.match(target):
        return match.group(0)
    if link_base is None:
        return text
    return f"[{text}]({link_base.rstrip('/')}/{target.lstrip('./')})"


def convert(
    text: str,
    link_base: str | None = None,
    drop_h1: bool = False,
    images: ImageResolver | None = None,
) -> tuple[str, str | None]:
    """Convert a whole document; return the body and the dropped H1 title, if any."""
    lines = text.splitlines()
    title = None
    if drop_h1:
        for i, line in enumerate(lines):
            if line.strip():
                if line.startswith("# "):
                    title = line[2:].strip()
                    lines = lines[i + 1 :]
                    while lines and not lines[0].strip():
                        lines.pop(0)
                break

    out: list[str] = []
    fence: str | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        if fence:
            out.append(line)
            if line.startswith(fence):
                fence = None
            i += 1
            continue
        if m := _FENCE.match(line):
            fence = m.group(1)
            out.append(line)
            i += 1
            continue
        if m := _DISPLAY_START.match(line):
            closer = "$$" if m.group(1) == "$$" else r"\]"
            rest = m.group(2)
            if rest.endswith(closer):
                out.extend(math_block([rest[: -len(closer)].strip()]))
                i += 1
                continue
            body = [rest] if rest else []
            i += 1
            while i < len(lines) and closer not in lines[i]:
                body.append(lines[i])
                i += 1
            if i < len(lines):
                tail = lines[i].split(closer, 1)[0]
                if tail.strip():
                    body.append(tail)
            out.extend(math_block(body))
            i += 1
            continue
        out.append(convert_inline(line, link_base, images))
        i += 1
    return "\n".join(out) + "\n", title


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, help="local Markdown file; it is only read")
    parser.add_argument("-o", "--output", type=Path, required=True, help="converted body file")
    parser.add_argument(
        "--link-base",
        help="URL that relative links resolve against; without it a relative link keeps only its text",
    )
    parser.add_argument(
        "--drop-h1",
        action="store_true",
        help="remove the leading H1 and print it, for use as the issue title",
    )
    parser.add_argument(
        "--remote", default="origin", help="git remote whose GitHub repository serves local images"
    )
    parser.add_argument(
        "--rev",
        help="commit or ref that image URLs are pinned to; default <remote>/HEAD of each repository",
    )
    parser.add_argument("--prepend", default="", help="text placed before the body")
    parser.add_argument("--append", default="", help="text placed after the body")
    args = parser.parse_args()

    if args.output.resolve() == args.source.resolve():
        sys.exit("refusing to overwrite the source; pick another --output path")
    images = ImageResolver(args.source.resolve().parent, args.remote, args.rev)
    body, title = convert(args.source.read_text(), args.link_base, args.drop_h1, images)
    if images.problems:
        problems = dict.fromkeys(images.problems)
        print("images GitHub cannot load; nothing written:", *problems, sep="\n  ", file=sys.stderr)
        sys.exit(1)
    if args.prepend:
        body = args.prepend.rstrip("\n") + "\n\n" + body
    if args.append:
        body = body.rstrip("\n") + "\n\n" + args.append.rstrip("\n") + "\n"
    args.output.write_text(body)
    if title is not None:
        print(title)


if __name__ == "__main__":
    main()
