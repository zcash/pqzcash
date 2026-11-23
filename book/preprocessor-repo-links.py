#!/usr/bin/env python3
"""mdBook preprocessor: links out of the book into the repository.

A chapter may link a file of the repository that lies outside `book/src` by a relative path,
such as `../../../ragu-pcs/pareto-model.py`, which works where the Markdown is read in place:
an editor, or GitHub's view of the source tree. The rendered book has no such files, so this
rewrites those links to the repository on GitHub, `blob/main` for a file and `tree/main` for a
directory (a path ending in `/`). Links that stay inside `book/src` are left alone.
"""

import json
import re
import sys
from pathlib import Path

REPOSITORY = "https://github.com/zcash/pqzcash"
SRC = Path(__file__).resolve().parent / "src"
LINK = re.compile(r"\]\((\.\./[^)\s#]+)(#[^)\s]*)?\)")


def rewrite(content, chapter_path):
    """Rewrite the chapter's relative links that leave `book/src`."""
    chapter_dir = (SRC / chapter_path).parent

    def sub(m):
        target = (chapter_dir / m.group(1)).resolve()
        try:
            target.relative_to(SRC)
            return m.group(0)  # inside the book
        except ValueError:
            pass
        rel = target.relative_to(SRC.parent.parent).as_posix()
        kind = "tree" if m.group(1).endswith("/") else "blob"
        return f"]({REPOSITORY}/{kind}/main/{rel}{m.group(2) or ''})"

    return LINK.sub(sub, content)


def walk(items):
    for item in items:
        chapter = item.get("Chapter") if isinstance(item, dict) else None
        if not chapter:
            continue
        if chapter.get("path"):
            chapter["content"] = rewrite(chapter["content"], chapter["path"])
        walk(chapter.get("sub_items", []))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "supports":
        sys.exit(0)
    _context, book = json.load(sys.stdin)
    # mdBook 0.5 calls the book's top-level list `items`; earlier versions called it `sections`.
    walk(book.get("items", book.get("sections", [])))
    json.dump(book, sys.stdout)


if __name__ == "__main__":
    main()
