#!/usr/bin/env python3
"""Merge review extracts from several pages (extract_reviews.js) into one reviews_site.json.

Takes the common fields (rating, review count, distribution, summary) from the first non-empty page,
merges reviews without duplicates (by date and start of text), at most 30.

Usage:
  merge_reviews.py page1.json page2.json ... --out reviews_site.json
"""
import argparse
import json
import sys

MAX_REVIEWS = 30


def merge(pages):
    out = None
    seen = set()
    for p in pages:
        if not isinstance(p, dict):
            continue
        if p.get("blocked"):
            if out is None:
                out = dict(p, reviews=[])
            continue
        if out is None or out.get("blocked"):
            out = {k: v for k, v in p.items() if k != "reviews"}
            out["reviews"] = []
            out["blocked"] = False
        for k in ("rating", "count", "distribution", "summary", "pages"):
            if out.get(k) in (None, "", {}) and p.get(k) not in (None, "", {}):
                out[k] = p[k]
        for r in p.get("reviews") or []:
            key = (r.get("date"), (r.get("text") or r.get("pros") or r.get("cons") or "")[:60])
            if key in seen or len(out["reviews"]) >= MAX_REVIEWS:
                continue
            seen.add(key)
            out["reviews"].append(r)
    return out or {"blocked": False, "reviews": []}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Merge review pages into one file")
    ap.add_argument("pages", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    pages = []
    for path in a.pages:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            pages.append(json.loads(data) if isinstance(data, str) else data)
        except (OSError, ValueError) as exc:
            print("Skipping %s: %s" % (path, exc), file=sys.stderr)
    res = merge(pages)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print("Reviews: %d of %s, rating %s" % (len(res.get("reviews", [])), res.get("count"), res.get("rating")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
