#!/usr/bin/env python3
"""Targeted reading of references: one section instead of the whole file.

  refs.py <file>                   list of headings
  refs.py <file> <part of heading> text of one section (up to the next heading of the same or higher level)

<file> is a name from skills/property-due-diligence/references, with or without .md.
"""
import os
import re
import sys

REF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "skills", "property-due-diligence", "references")
HEAD = re.compile(r"^(#{1,6})\s+(.*)$")


def resolve(name, ref_dir=REF_DIR):
    base = os.path.basename(name)
    if not base.endswith(".md"):
        base += ".md"
    p = os.path.join(ref_dir, base)
    if not os.path.exists(p):
        raise FileNotFoundError("no reference %s (available: %s)" % (base, ", ".join(sorted(
            f for f in os.listdir(ref_dir) if f.endswith(".md")))))
    return p


def headings(lines):
    out = []
    in_code = False
    for i, line in enumerate(lines):
        if line.startswith("```"):
            in_code = not in_code
        m = None if in_code else HEAD.match(line)
        if m:
            out.append((i, len(m.group(1)), m.group(2).strip()))
    return out


def section(text, needle):
    lines = text.splitlines()
    hs = headings(lines)
    low = needle.lower()
    for idx, (i, level, title) in enumerate(hs):
        if low in title.lower():
            end = len(lines)
            for j, lvl, _ in hs[idx + 1:]:
                if lvl <= level:
                    end = j
                    break
            return "\n".join(lines[i:end]).rstrip()
    return None


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0 if argv else 2
    try:
        path = resolve(argv[0])
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if len(argv) == 1:
        for _, level, title in headings(text.splitlines()):
            print("  " * (level - 1) + title)
        return 0
    sec = section(text, " ".join(argv[1:]))
    if sec is None:
        print("Section '%s' not found. Headings: %s" % (" ".join(argv[1:]), "; ".join(
            t for _, _, t in headings(text.splitlines()))), file=sys.stderr)
        return 1
    print(sec)
    return 0


if __name__ == "__main__":
    sys.exit(main())
