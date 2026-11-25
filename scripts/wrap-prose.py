#!/usr/bin/env python3
"""Hard-wrap the repository's prose at a width, or check that it is wrapped.

    python scripts/wrap-prose.py --check [--width 100] [FILE ...]
    python scripts/wrap-prose.py --write [--width 100] [FILE ...]

Without files, every Markdown file under ragu-pcs/ and book/src/ and the frontier page's
template are taken, except book/src/SUMMARY.md, whose entries are one line each by mdbook's
rule. In Markdown, paragraphs and list items are refilled; headings, tables, fenced code,
display math, blank lines and lines that open an HTML block are left alone, and only
paragraphs with a line over the width are touched, so a file already wrapped at a narrower
width keeps it. In the template, the text of single-line <p> and <li> elements is refilled
at the element's indentation; the page's script, style and controls are not prose and are
left alone.

Some spans must not be broken, and the filler treats each as one word: a figure marker with
its value (<!--fig:name-->value<!--/fig-->), a claim marker, which is also glued to the word
before it, since CommonMark starts an HTML block at a line that begins with `<!--`; an inline
math span, which mdbook-katex renders only on one source line; an inline code span; an HTML
tag with its attributes; and a Markdown link's target.

--check exits 1 and lists every prose line over the width that the filler could have
shortened, so that a CI step can hold the prose to the width.
"""

import pathlib
import re
import sys
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[1]
GLUE = "\u0001"  # stands for a space inside a span that must not be broken
EXCLUDED = {ROOT / "book" / "src" / "SUMMARY.md"}

ATOMIC = re.compile(
    r"<!--fig:[^>]*-->.*?<!--/fig-->"  # a figure marker with its value
    r"|<span class=\"noteref\"[^>]*>.*?</span>"  # a note reference the model turns into a link
    r"|<!--.*?-->"  # any other comment, such as a claim marker
    r"|\$\$.*?\$\$"  # display math on one line
    r"|\$[^$]*?\$"  # inline math
    r"|`[^`]*`"  # inline code
    r"|<[A-Za-z/][^>]*>"  # an HTML tag with its attributes
    r"|\]\([^)\s]*\s[^)]*\)",  # a link target with a space (a title)
    re.S,
)


def glue(text):
    """Spaces inside unbreakable spans become GLUE, and a comment or a tag is glued to the
    word before it, so that neither starts a line: CommonMark starts an HTML block at a line
    that begins with `<!--`, or with a block-level tag."""
    text = ATOMIC.sub(lambda m: m.group(0).replace(" ", GLUE), text)
    return re.sub(r" (<!--|<[A-Za-z/])", GLUE + r"\1", text)


def fill(text, width, indent, hanging):
    joined = glue(" ".join(part.strip() for part in text))
    lines = textwrap.wrap(
        joined,
        width,
        initial_indent=indent,
        subsequent_indent=hanging,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return [line.replace(GLUE, " ") for line in lines]


LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+\.) ")


def refill_markdown(text, width):
    """Paragraphs and list items are refilled where a line exceeds the width; `raw` keeps a
    paragraph's lines as written for the ones left alone, `buf` their text without the list
    marker and indentation for the filler."""
    out, buf, raw, indent, hanging, in_fence, in_math = [], [], [], "", "", False, False

    def flush():
        if buf:
            if any(len(line) > width for line in raw):
                out.extend(fill(buf, width, indent, hanging))
            else:
                out.extend(raw)
            buf.clear()
            raw.clear()

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            flush()
            in_fence = not in_fence
            out.append(line)
            continue
        if stripped.startswith("$$"):
            flush()
            if not (stripped.endswith("$$") and len(stripped) > 2):
                in_math = not in_math
            out.append(line)
            continue
        if (
            in_fence
            or in_math
            or not stripped
            or stripped.startswith("|")
            or stripped.startswith("#")
            or stripped.startswith("<!--")
            or stripped.startswith("<")
            and not LIST_ITEM.match(line)
            and not buf
        ):
            flush()
            out.append(line)
            continue
        m = LIST_ITEM.match(line)
        if m:
            flush()
            indent = m.group(0)
            hanging = m.group(1) + " " * (len(m.group(0)) - len(m.group(1)))
            buf.append(line[len(indent) :])
            raw.append(line)
            continue
        if not buf:
            indent = hanging = line[: len(line) - len(line.lstrip())]
        buf.append(line)
        raw.append(line)
    flush()
    return "\n".join(out).rstrip("\n") + "\n"


HTML_PROSE = re.compile(r"^(\s*)(<(p|li)(?: [^>]*)?>)(.*)(</\3>)\s*$")


def refill_html(text, width):
    out = []
    for line in text.split("\n"):
        m = HTML_PROSE.match(line)
        if m and len(line) > width:
            indent, open_tag, _, inner, close_tag = m.groups()
            lines = fill([open_tag + inner + close_tag], width, indent, indent)
            out.extend(lines)
        else:
            out.append(line)
    return "\n".join(out).rstrip("\n") + "\n"


def refill(path, text, width):
    return (refill_html if path.suffix == ".html" else refill_markdown)(text, width)


def prose_lines_over(path, text, width):
    """Lines over the width that refilling would shorten."""
    new = refill(path, text, width)
    if new == text:
        return []
    wrapped = set(new.split("\n"))
    return [
        n for n, line in enumerate(text.split("\n"), 1) if len(line) > width and line not in wrapped
    ]


def default_files():
    files = sorted((ROOT / "ragu-pcs").glob("*.md")) + sorted((ROOT / "book" / "src").rglob("*.md"))
    files = [f for f in files if f not in EXCLUDED]
    return files + [ROOT / "ragu-pcs" / "pareto-template.html"]


def main():
    args = sys.argv[1:]
    width = int(args[args.index("--width") + 1]) if "--width" in args else 100
    write = "--write" in args
    check = "--check" in args
    names = [a for i, a in enumerate(args) if not a.startswith("--") and args[i - 1] != "--width"]
    files = [pathlib.Path(n).resolve() for n in names] or default_files()
    bad = 0
    for path in files:
        text = path.read_text()
        if check:
            over = prose_lines_over(path, text, width)
            if over:
                bad += len(over)
                print(f"{path.relative_to(ROOT)}: {len(over)} prose lines over {width}: {over[:8]}")
        else:
            new = refill(path, text, width)
            if new != text:
                print(f"{path.relative_to(ROOT)}: refilled ({len(new.split(chr(10)))} lines)")
                if write:
                    path.write_text(new)
    if check:
        print("prose wrapped" if not bad else f"{bad} prose lines over {width}")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
