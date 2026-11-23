#!/usr/bin/env python3
"""mdBook preprocessor: links out of the book into the repository, and links between the
repository's files that the book includes as chapters.

A chapter may link a file of the repository that lies outside `book/src` by a relative path,
such as `../../../ragu-pcs/pareto-model.py`, which works where the Markdown is read in place:
an editor, or GitHub's view of the source tree. The rendered book has no such files, so this
rewrites those links to the repository on GitHub, `blob/main` for a file and `tree/main` for a
directory (a path ending in `/`). Links that stay inside `book/src` are left alone.

A chapter whose source is an `{{#include}}` of a repository file outside `book/src`, such as the
study's notes under `ragu-pcs/`, has its relative links read from that file's directory, so that
a note links its neighbours as `scripts/x.py` or `other-note.md#section`, which is right where
the file lives. A target that is itself included as a chapter becomes a link to that chapter,
fragment kept, unless the link's text is a code span, which names the file itself and so links
it on GitHub; `ragu-pcs/pareto-template.html` counts as the frontier chapter, which includes the
page generated from it. Any other target inside the repository becomes a GitHub link, and a
target that does not exist fails the build.
"""

import json
import os
import re
import sys
from pathlib import Path

REPOSITORY = "https://github.com/zcash/pqzcash"
SRC = Path(__file__).resolve().parent / "src"
REPO = SRC.parent.parent
INCLUDE = re.compile(r"\{\{#include\s+([^}\s:]+)")
LINK = re.compile(r"\[([^\]]*)\]\(([^)\s#]+)?(#[^)\s]*)?\)")
SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:")
# Repository files that stand for a chapter although no chapter includes them directly.
ALIASES = {
    REPO / "ragu-pcs/pareto-template.html": "proof-systems/pcs-frontier.md",
    REPO / "ragu-pcs/REGENERATING.md": "proof-systems/regenerating.md",
}


def included(chapter_path):
    """The repository file outside `book/src` that the chapter's source includes, or None."""
    source = SRC / chapter_path
    if not source.exists() and source.name == "index.md":
        source = source.with_name("README.md")  # mdBook reports README.md as index.md
    if not source.exists():
        return None
    for m in INCLUDE.finditer(source.read_text()):
        target = (source.parent / m.group(1)).resolve()
        if not target.is_relative_to(SRC):
            return target
    return None


def rewrite(content, chapter_path, chapters):
    """Rewrite the chapter's relative links as the module docstring says."""
    source = SRC / chapter_path
    base = included(chapter_path)
    base_dir = base.parent if base else source.parent

    def sub(m):
        text, path, fragment = m.group(1), m.group(2), m.group(3) or ""
        if not path or SCHEME.match(path) or path.startswith("/"):
            return m.group(0)
        target = (base_dir / path).resolve()
        # A link whose text is a code span names the file itself; a title names the chapter.
        if target in chapters and not text.startswith("`"):
            rel = Path(os.path.relpath(SRC / chapters[target], source.parent)).as_posix()
            return f"[{text}]({rel}{fragment})"
        if target.is_relative_to(SRC) or not target.is_relative_to(REPO):
            return m.group(0)
        if not target.exists():
            sys.exit(f"{chapter_path}: a link to {path}, which is not in the repository")
        kind = "tree" if path.endswith("/") or target.is_dir() else "blob"
        rel = target.relative_to(REPO).as_posix()
        return f"[{text}]({REPOSITORY}/{kind}/main/{rel}{fragment})"

    return LINK.sub(sub, content)


def walk(items):
    """Every chapter with a path, in reading order."""
    for item in items:
        chapter = item.get("Chapter") if isinstance(item, dict) else None
        if not chapter:
            continue
        if chapter.get("path"):
            yield chapter
        yield from walk(chapter.get("sub_items", []))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "supports":
        sys.exit(0)
    book = json.load(sys.stdin)[1]  # after the preprocessor context
    # mdBook 0.5 calls the book's top-level list `items`; earlier versions called it `sections`.
    chapters = list(walk(book.get("items", book.get("sections", []))))
    by_source = dict(ALIASES)
    for chapter in chapters:
        source = included(chapter["path"])
        if source:
            by_source[source] = chapter["path"]
    for chapter in chapters:
        chapter["content"] = rewrite(chapter["content"], chapter["path"], by_source)
    json.dump(book, sys.stdout)


if __name__ == "__main__":
    main()
