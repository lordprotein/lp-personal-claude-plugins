#!/usr/bin/env python3
"""Short digest of geo.json (output of osm_nearby.py) for agents: up to 2 KB instead of ~50 KB.

Usage: geo_brief.py geo.json [--out geo_brief.json]
"""
import argparse
import json
import sys

TOP_CATS = ["metro", "rail_station", "stop_bus_tram", "school", "kindergarten", "park", "forest",
            "major_road", "railway_line", "industrial", "powerline", "landfill", "construction",
            "nightlife", "mall", "clinic"]
PARTIAL_MARK = "failed to load"
# Markers written by older versions of osm_nearby.py (Russian notes and errors), kept for old geo.json files.
LEGACY_PARTIAL_MARK = "не загрузились"
LEGACY_GEOM_ERROR = "часть 'geom'"
MAX_BYTES = 2048


def _item(x, cat):
    name = (x.get("name") or "").strip() or None
    if name and len(name) > 40:
        name = name[:39] + "…"
    row = [name, x.get("distance_m")]
    if cat == "major_road":
        row.append((x.get("tags") or {}).get("highway"))
    return row


def is_partial(geo):
    notes = " ".join(geo.get("notes") or [])
    errs = " ".join(geo.get("errors") or [])
    if PARTIAL_MARK in notes or LEGACY_PARTIAL_MARK in notes or "part 'geom'" in errs or LEGACY_GEOM_ERROR in errs:
        return True
    # old files without the marker: no linear objects at all, and requests failed
    cats = geo.get("categories") or {}
    linear = ("major_road", "railway_line", "tram_line", "powerline")
    return bool(geo.get("errors")) and not any(cats.get(c) for c in linear)


def build(geo, top_n=3):
    noise = geo.get("noise_estimate") or {}
    srcs = [[s.get("kind"), s.get("name"), s.get("distance_m"), s.get("est_db")]
            for s in (noise.get("sources") or [])[:3]]
    cats = geo.get("categories") or {}
    top = {}
    for c in TOP_CATS:
        items = cats.get(c) or []
        if items:
            top[c] = [_item(x, c) for x in items[:top_n]]
    brief = {
        "center": geo.get("center"),
        "nearest": {k: v for k, v in (geo.get("nearest") or {}).items() if v is not None},
        "top3": top,
        "noise_estimate": {
            "est_db_combined": noise.get("est_db_combined"),
            "est_db_max": noise.get("est_db_max"),
            "sources": srcs,
            "price_discount_pct": noise.get("price_discount_pct"),
        },
        "suggested_scores": geo.get("suggested_scores"),
        "score_notes": geo.get("score_notes"),
        "partial": is_partial(geo),
        "errors_count": len(geo.get("errors") or []),
    }
    # Fit the limit: first cut the top lists to 2, then to 1, then drop the notes
    for n in (2, 1):
        if _size(brief) <= MAX_BYTES:
            break
        brief["top3"] = {c: v[:n] for c, v in brief["top3"].items()}
    if _size(brief) > MAX_BYTES:
        brief["score_notes"] = None
    # last resort: drop the least important categories (TOP_CATS order = priority)
    for c in reversed(TOP_CATS):
        if _size(brief) <= MAX_BYTES:
            break
        brief["top3"].pop(c, None)
    return brief


def _size(brief):
    return len(dumps(brief).encode("utf-8"))


def dumps(brief):
    return json.dumps(brief, ensure_ascii=False, separators=(",", ":"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Digest of geo.json for agents (≤2 KB)")
    ap.add_argument("geo")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    try:
        with open(a.geo, encoding="utf-8") as f:
            brief = build(json.load(f))
    except (OSError, ValueError) as e:
        print("Error: %s" % e, file=sys.stderr)
        return 1
    txt = dumps(brief)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(txt)
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
