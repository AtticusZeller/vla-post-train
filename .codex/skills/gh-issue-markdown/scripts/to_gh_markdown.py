"""Convert a local Markdown document into a body that GitHub issues render correctly.

GitHub parses Markdown before MathJax sees the math, so plain ``$...$`` and ``$$...$$`` lose
backslash escapes (``\\{`` becomes ``{``), a line ending in ``\\\\`` turns into a hard break, and a
``<`` starts an HTML tag that swallows the rest of the formula. GitHub also rejects some macros,
such as ``\\operatorname``. This script rewrites math into the code-span forms GitHub leaves
untouched, patches the known breakages, and resolves relative links. Local images become absolute
paths listed in an ``.attach`` file, so ``gh ... --attach`` uploads them and rewrites the references to
GitHub attachment URLs. It never edits the source.
"""

import argparse
import re
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
_HTML_IMG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_HTML_ATTR = re.compile(r"\b(src|alt)=[\"']([^\"']*)[\"']", re.IGNORECASE)
_EXTERNAL = re.compile(r"^([a-z][a-z0-9+.-]*:|#|//)", re.IGNORECASE)
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


def inline_tags(line: str) -> str:
    """Write ``\\tag{n}`` as a trailing ``(n)``; GitHub lays tagged equations out in a squeezed column."""
    line = re.sub(r"\\tag\*\{([^{}]*)\}", r"\\qquad \1", line)
    return re.sub(r"\\tag\{([^{}]*)\}", r"\\qquad (\1)", line)


def math_block(body: list[str]) -> list[str]:
    """Render display math as a fenced ``math`` block."""
    body = join_trailing_row_breaks([inline_tags(fix_math(line)) for line in body])
    return ["```math", *body, "```"]


class ImageResolver:
    """Map local image paths to the absolute paths that ``gh --attach`` uploads."""

    def __init__(self, doc_dir: Path):
        self.doc_dir = doc_dir
        self.attachments: dict[Path, None] = {}
        self.problems: list[str] = []

    def url(self, target: str) -> str:
        """Reference for an image; external URLs pass through, local files become encoded paths.

        gh only rewrites a reference it can parse as a Markdown link destination, so a path with a
        space must be percent-encoded.
        """
        if _EXTERNAL.match(target):
            return target
        path = (self.doc_dir / unquote(target)).resolve()
        if not path.is_file():
            self.problems.append(f"{target}: no such file {path}")
            return target
        self.attachments[path] = None
        return quote(path.as_posix())


def html_img_to_markdown(match: re.Match, images: ImageResolver) -> str:
    """Turn a local ``<img>`` into a Markdown image; gh --attach leaves HTML ``src`` untouched."""
    attrs = {k.lower(): v for k, v in _HTML_ATTR.findall(match.group(0))}
    src = attrs.get("src")
    if not src or _EXTERNAL.match(src):
        return match.group(0)
    return f"![{attrs.get('alt', '')}]({images.url(src)})"


def rewrite_images(text: str, images: ImageResolver | None) -> str:
    """Point Markdown and HTML image references at files gh can attach."""
    if images is None:
        return text
    text = _IMAGE.sub(lambda m: m.group(1) + images.url(m.group(2)) + m.group(3), text)
    return _HTML_IMG.sub(lambda m: html_img_to_markdown(m, images), text)


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
    parser.add_argument("--prepend", default="", help="text placed before the body")
    parser.add_argument("--append", default="", help="text placed after the body")
    args = parser.parse_args()

    if args.output.resolve() == args.source.resolve():
        sys.exit("refusing to overwrite the source; pick another --output path")
    images = ImageResolver(args.source.resolve().parent)
    body, title = convert(args.source.read_text(), args.link_base, args.drop_h1, images)
    if images.problems:
        problems = dict.fromkeys(images.problems)
        print("images that cannot be attached; nothing written:", *problems, sep="\n  ", file=sys.stderr)
        sys.exit(1)
    if args.prepend:
        body = args.prepend.rstrip("\n") + "\n\n" + body
    if args.append:
        body = body.rstrip("\n") + "\n\n" + args.append.rstrip("\n") + "\n"
    args.output.write_text(body)
    # One ``--attach=<path>`` per line, for ``xargs -d '\n' -a <file> gh ...``; empty without images.
    attach_file = args.output.with_name(args.output.name + ".attach")
    attach_file.write_text("".join(f"--attach={path}\n" for path in images.attachments))
    if title is not None:
        print(title)


if __name__ == "__main__":
    main()
