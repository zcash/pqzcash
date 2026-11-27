#!/usr/bin/env python3
"""Keep a figure and its unit on one line: put a no-break space, U+00A0, between them.

    python scripts/nbsp-units.py --check [FILE ...]
    python scripts/nbsp-units.py --write [FILE ...]

Without files, every Markdown file under ragu-pcs/ and book/src/ and the frontier page's
template are taken, except book/src/SUMMARY.md and the working notes, which no page renders.

A figure is a number written in the text, a model-filled figure (<!--fig:name-->value<!--/fig-->),
or an inline math span. Where one is followed by white space and then a unit, that white space,
a line break included, becomes one no-break space. The units are the ones in UNITS: units of
time and size, the counted digits and gates that a step's length is given in, and the words
million, billion, and thousand, which are part of the number.

The text is split into the same spans as scripts/wrap-prose.py splits it into, so that nothing
is changed inside a code span, a math span, a tag, a comment, or a link's target, and fenced
code, display math, and the page's style and script are left alone. This is a lexer for those
spans, not a parser of Markdown or of HTML.

--check exits 1 and lists every place where --write would put a no-break space. Run
scripts/wrap-prose.py --write afterwards: joining a figure to a unit on the next line can leave
a line over the width.
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
NBSP = "\u00a0"
EXCLUDED = {ROOT / "book" / "src" / "SUMMARY.md", ROOT / "ragu-pcs" / "WORKING-NOTES.md"}
UNITS = (
    "s|ms|ns|µs|minutes|hours"
    "|bytes?|kbytes|Mbytes|bits?|kbits|Mbits"
    "|digits|gates"
    "|million|billion|thousand|percent"
)
UNIT_AHEAD = re.compile(rf"[ \t]*\n?[ \t]*(?=(?:{UNITS})(?![\w-]))")
# A number in running text and the white space before its unit.
IN_TEXT = re.compile(rf"(?<=\d)(?:[ \t]+|[ \t]*\n[ \t]*)(?=(?:{UNITS})(?![\w-]))")
SPAN = re.compile(
    r"(?P<figure><!--fig:[^>]*-->.*?<!--/fig-->)"  # a figure marker with its value
    r"|(?P<comment><!--.*?-->)"  # any other comment, such as a claim marker
    r"|(?P<display>\$\$.*?\$\$)"  # display math
    r"|(?P<math>\$[^$\n]*?\$)"  # inline math
    r"|(?P<code>`[^`\n]*`)"  # inline code
    r"|(?P<tag><[A-Za-z/][^>]*>)"  # an HTML tag with its attributes
    r"|(?P<target>\]\([^)\s]*(?:\s[^)]*)?\))",  # a link's target
    re.S,
)
OPAQUE = re.compile(r"<(style|script)\b.*?</\1>", re.S)


def default_files():
    files = [ROOT / "ragu-pcs" / "pareto-template.html"]
    for base in (ROOT / "ragu-pcs", ROOT / "book" / "src"):
        files += sorted(
            p for p in base.rglob("*.md") if "work" not in p.parts and "keep" not in p.parts
        )
    return [p for p in files if p not in EXCLUDED]


def prose_regions(text, markdown):
    """The stretches of `text` that are prose, as (start, end): outside fenced code in
    Markdown, and outside the style and script elements in the template."""
    if not markdown:
        start = 0
        for m in OPAQUE.finditer(text):
            yield start, m.start()
            start = m.end()
        yield start, len(text)
        return
    start, fence, offset = 0, False, 0
    for line in text.split("\n"):
        if line.strip().startswith(("```", "~~~")):
            if not fence:
                yield start, offset
            else:
                start = offset + len(line) + 1
            fence = not fence
        offset += len(line) + 1
    if not fence:
        yield start, len(text)


def joined(text, markdown):
    """`text` with a no-break space between each figure and its unit, and the places changed,
    as line numbers."""
    edits = []  # (start, end) of white space to replace
    for lo, hi in prose_regions(text, markdown):
        region, position, after_figure = text[lo:hi], 0, False
        for m in list(SPAN.finditer(region)) + [None]:
            end = m.start() if m else len(region)
            plain = region[position:end]  # running text before the next span
            if after_figure and (lead := UNIT_AHEAD.match(plain)) and lead.end() > 0:
                edits.append((lo + position, lo + position + lead.end()))
            for found in IN_TEXT.finditer(plain):
                edits.append((lo + position + found.start(), lo + position + found.end()))
            if m is None:
                break
            # A unit may follow a filled figure, or a math span, which is a figure when it is
            # a formula for a number; a formula for something else has no unit after it.
            after_figure = m.lastgroup in ("figure", "math")
            position = m.end()
    out, lines = text, []
    for start, end in sorted(set(edits), reverse=True):
        if out[start:end] != NBSP:
            lines.append(text.count("\n", 0, start) + 1)
            out = out[:start] + NBSP + out[end:]
    return out, sorted(lines)


def main():
    args = sys.argv[1:]
    if not args or args[0] not in ("--check", "--write"):
        sys.exit(__doc__)
    files = [pathlib.Path(a).resolve() for a in args[1:]] or default_files()
    missing = 0
    for path in files:
        text = path.read_text()
        new, lines = joined(text, path.suffix == ".md")
        if not lines:
            continue
        name = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        if args[0] == "--write":
            path.write_text(new)
            print(f"{name}: {len(lines)} no-break spaces written")
        else:
            missing += len(lines)
            print(f"{name}: a figure and its unit can part at lines {', '.join(map(str, lines))}")
    if missing:
        sys.exit(f"{missing} places need a no-break space; run scripts/nbsp-units.py --write")
    if args[0] == "--check":
        print("figures are joined to their units")


if __name__ == "__main__":
    main()
